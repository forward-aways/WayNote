"""邮箱验证码状态机（**唯一实现**，任何端点都不得自行比对验证码）。

设计见 .deepcode/ADR-20261009-Waynote-email-code-auth.md §6.2 / §6.3 / §6.6。

不变量（改动前请先读 ADR）：
- I1 同一 (email, purpose) 至多一行 PENDING：发新码前把旧的 pending 行 expires_at 置 now（等合作废）
- I2 attempts 单调不减；**错误尝试必须先落库再抛错**（否则并发可绕过尝试上限）
- I3 consumed_at 为终态，不可复用
- I4 purpose ∈ {login, register, reset}；跨用途一律拒绝
- I5 对外话术与"邮箱是否存在 / 码是否真正发出"无关（调用方只用本模块的 GENERIC_* 常量）

并发：校验路径对目标行加 `SELECT … FOR UPDATE` 行锁，把"读 attempts → 判断 → 递增"变成临界区，
消除 TOCTOU（见 ADR §3 表格最后两行）。
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.mailer import send_email_code
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import hash_password, verify_password
from app.models.email_code import EmailCode

log = get_logger("auth.email_code")

PURPOSES = ("login", "register", "reset")

# 统一话术（不变量 I5）：绝不区分"邮箱不存在 / 码未发出 / 码已发"
GENERIC_SENT_MESSAGE = "验证码已发送，请查收（含垃圾邮件箱），{minutes} 分钟内有效"
GENERIC_INVALID_MESSAGE = "验证码无效或已过期，请重新获取"

_LIMITER = SlidingWindowLimiter()


class RateLimited(Exception):
    """命中频控；retry_after_seconds 用于 429 话术。"""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"rate limited, retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class CodeInvalid(Exception):
    """验证码校验失败：对外统一话术，不区分具体原因。"""


@dataclass(frozen=True)
class RequestOutcome:
    cooldown_seconds: int


def reset_rate_limit_state() -> None:
    """测试用：清空限流计数（生产无需调用）。"""
    _LIMITER.reset()


def normalize_email(email: str) -> str:
    """归一化：与注册写入口径一致（去空白 + 小写），避免大小写造成多份账号/多份码。"""
    return email.strip().lower()


def generate_code() -> str:
    """6 位数字码：secrets（CSPRNG）+ 均匀分布。"""
    return f"{secrets.randbelow(1_000_000):06d}"


def request_code(
    db: Session,
    *,
    email: str,
    purpose: str,
    ip: str | None,
    deliver: bool,
) -> RequestOutcome:
    """请求验证码。

    deliver=False（邮箱不适用该用途）时：只做限流与统一话术，不发信、不落码。
    执行顺序不可调换（ADR §6.6）：①限流 → ②发信 → ③落码 —— 保证"用户没收到码"时库里没有可用码。
    """
    if purpose not in PURPOSES:
        raise ValueError(f"unknown purpose: {purpose}")
    email = normalize_email(email)
    cooldown_seconds = settings.email_code_cooldown_seconds

    _enforce_limits(email=email, purpose=purpose, ip=ip)

    if not deliver:
        return RequestOutcome(cooldown_seconds=cooldown_seconds)

    code = generate_code()
    # ② 发信：失败即抛 MailerError（此时库里不会留下可用码）
    send_email_code(to=email, code=code, purpose=purpose, ttl_minutes=settings.email_code_ttl_minutes)

    # ③ 落码：先作废同 (email, purpose) 的旧 pending 行（不变量 I1）
    now = datetime.now(timezone.utc)
    db.execute(
        update(EmailCode)
        .where(
            EmailCode.email == email,
            EmailCode.purpose == purpose,
            EmailCode.consumed_at.is_(None),
            EmailCode.expires_at > now,
        )
        .values(expires_at=now)
        .execution_options(synchronize_session=False)
    )
    db.add(
        EmailCode(
            email=email,
            purpose=purpose,
            code_hash=hash_password(code),
            expires_at=now + timedelta(minutes=settings.email_code_ttl_minutes),
            request_ip=ip,
        )
    )
    db.commit()
    log.info(
        "验证码已发出 purpose=%s to=%s ip=%s",
        purpose,
        email,
        ip or "-",
        extra={"event": "auth.email_code.sent", "purpose": purpose, "ip": ip or "-"},
    )
    return RequestOutcome(cooldown_seconds=cooldown_seconds)


def verify_code(db: Session, *, email: str, purpose: str, code: str) -> None:
    """校验验证码；失败抛 CodeInvalid（统一话术）。

    成功时把 consumed_at 落库（终态）；失败时（错码）先递增 attempts 并落库再抛错。
    """
    if purpose not in PURPOSES:
        raise ValueError(f"unknown purpose: {purpose}")
    email = normalize_email(email)
    now = datetime.now(timezone.utc)

    row = db.execute(
        select(EmailCode)
        .where(EmailCode.email == email, EmailCode.purpose == purpose)
        .order_by(EmailCode.created_at.desc(), EmailCode.id.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()

    if row is None:
        _dummy_compare(code)  # 时序对齐：无行与有行耗时相近
        raise CodeInvalid()
    if row.consumed_at is not None or _as_utc(row.expires_at) <= now:
        raise CodeInvalid()
    if row.attempts >= settings.email_code_max_attempts:
        raise CodeInvalid()

    matched = verify_password(code, row.code_hash)
    row.attempts += 1  # 不变量 I2：无论对错都计入
    if not matched:
        db.commit()  # 先落库再抛错
        raise CodeInvalid()

    row.consumed_at = now  # 不变量 I3：一次性
    db.commit()


def _as_utc(value: datetime) -> datetime:
    """PostgreSQL timestamptz 取回为 aware；防御性兼容 naive（视为 UTC）。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _enforce_limits(*, email: str, purpose: str, ip: str | None) -> None:
    """多层频控：冷却 → 每邮箱小时 → 每邮箱日 → 每 IP 小时 → 全局小时。"""
    checks: tuple[tuple[str, int, int], ...] = (
        (f"cooldown:{email}:{purpose}", settings.email_code_cooldown_seconds, 1),
        (f"email:hour:{email}", 3600, settings.email_code_per_email_hour),
        (f"email:day:{email}", 86400, settings.email_code_per_email_day),
        (f"ip:hour:{ip or '-'}", 3600, settings.email_code_per_ip_hour),
        ("global:hour", 3600, settings.email_code_global_hour),
    )
    for key, window_seconds, limit in checks:
        decision = _LIMITER.hit(key, limit=limit, window_seconds=window_seconds)
        if not decision.allowed:
            raise RateLimited(decision.retry_after_seconds)


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """惰性生成一次假哈希（≈100ms），用于无记录时的时序对齐。"""
    return hash_password(secrets.token_urlsafe(16))


def _dummy_compare(code: str) -> None:
    verify_password(code, _dummy_hash())

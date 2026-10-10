"""认证：密码 + 邮箱验证码双通道。

设计见 .deepcode/ADR-20261009-Waynote-email-code-auth.md。

纪律（改动前请先读 ADR）：
- 验证码逻辑一律走 core/email_code.py，本模块**不得自行比对验证码**（不变量集中在服务层）
- 对外话术统一（不变量 I5）：错误文案与"邮箱是否存在 / 码是否发出"无关
- 顺序性原则：需要验证码的流程，先校验码再判断邮箱是否存在
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import email_code as codes
from app.core.config import settings
from app.core.email_code import CodeInvalid, RateLimited
from app.core.logging import get_logger
from app.core.mailer import MailerError
from app.core.net import parse_trusted_proxies, resolve_client_ip
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    EmailCodeLogin,
    EmailCodeOut,
    EmailCodeRequest,
    PasswordChange,
    PasswordReset,
    TokenOut,
    UserLogin,
    UserOut,
    UserRegister,
)


log = get_logger("api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@lru_cache(maxsize=8)
def _trusted(raw: str) -> frozenset[str]:
    return parse_trusted_proxies(raw)


def _client_ip(request: Request) -> str:
    return resolve_client_ip(request.scope, _trusted(settings.trusted_proxy_ips))


def _find_user(db: Session, email: str) -> User | None:
    """按归一化邮箱查找。

    大小写不敏感：历史注册数据未做归一化（可能有大写），
    这里统一用 lower(email) 匹配，避免老账号登录不上（见 ADR 偏差记录）。
    """
    return db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()


def _default_name(email: str) -> str:
    """免密建号的默认昵称：邮箱 @ 前缀（列宽 50，超长截断）。"""
    return (email.split("@", 1)[0] or "旅人")[:50]


# ===== 注册（需邮箱验证码）=====


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if not settings.allow_registration:
        log.warning("注册已关闭，拒绝注册请求", extra={"event": "auth.register.disabled"})
        raise HTTPException(status_code=403, detail="注册功能已关闭")

    email = codes.normalize_email(data.email)
    # 顺序性原则：先校验注册码 —— 能拿到码即已证明邮箱所有权，之后的"已被注册"不构成枚举面
    try:
        codes.verify_code(db, email=email, purpose="register", code=data.code)
    except CodeInvalid:
        raise HTTPException(status_code=400, detail=codes.GENERIC_INVALID_MESSAGE) from None

    if _find_user(db, email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(email=email, password_hash=hash_password(data.password), name=data.name)
    db.add(user)
    db.commit()
    db.refresh(user)

    log.info("用户注册 id=%s", user.id, extra={"event": "auth.register"})
    return TokenOut(access_token=create_access_token(user.id))


# ===== 密码登录 =====


@router.post("/login", response_model=TokenOut)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = _find_user(db, codes.normalize_email(data.email))
    # 统一话术：不区分"邮箱不存在 / 密码错 / 免密账号"（不变量 I5），但给出可行动的提示
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        log.warning("登录失败 email=%s", data.email, extra={"event": "auth.login.failed"})
        raise HTTPException(
            status_code=400,
            detail="邮箱或密码错误；若你从未设置过密码，请用「验证码登录」",
        )
    log.info("登录成功 id=%s", user.id, extra={"event": "auth.login"})
    return TokenOut(access_token=create_access_token(user.id))


# ===== 邮箱验证码：发放 =====


@router.post("/email-code", response_model=EmailCodeOut)
def request_email_code(data: EmailCodeRequest, request: Request, db: Session = Depends(get_db)):
    if not settings.smtp_configured:
        raise HTTPException(status_code=503, detail="邮件服务未配置，请联系管理员")

    email = codes.normalize_email(data.email)
    user = _find_user(db, email)

    # 投递判定（只决定"是否真的发信"，不影响对外话术）：
    #   login    → 任何邮箱都发（未注册会成为免密账号）
    #   register → 仅未注册邮箱需要（已注册走"邮箱已被注册"）
    #   reset    → 仅已注册邮箱可重置
    if data.purpose == "login":
        deliver = True
    elif data.purpose == "register":
        deliver = user is None
    else:
        deliver = user is not None

    try:
        outcome = codes.request_code(
            db, email=email, purpose=data.purpose, ip=_client_ip(request), deliver=deliver
        )
    except RateLimited as exc:
        raise HTTPException(
            status_code=429, detail=f"请求过于频繁，请 {exc.retry_after_seconds} 秒后再试"
        ) from None
    except MailerError:
        raise HTTPException(status_code=502, detail="邮件发送失败，请稍后重试") from None

    return EmailCodeOut(
        cooldown_seconds=outcome.cooldown_seconds,
        ttl_minutes=settings.email_code_ttl_minutes,
        message=codes.GENERIC_SENT_MESSAGE.format(minutes=settings.email_code_ttl_minutes),
    )


# ===== 邮箱验证码：免密登录（未注册则建号）=====


@router.post("/login/email-code", response_model=TokenOut)
def login_with_email_code(data: EmailCodeLogin, db: Session = Depends(get_db)):
    email = codes.normalize_email(data.email)
    try:
        codes.verify_code(db, email=email, purpose="login", code=data.code)
    except CodeInvalid:
        raise HTTPException(status_code=400, detail=codes.GENERIC_INVALID_MESSAGE) from None

    user = _find_user(db, email)
    if user is None:
        # 邮箱所有权已由验证码证明 → 免密建号（ADR §6.5）
        user = User(email=email, password_hash=None, name=_default_name(email))
        db.add(user)
        db.commit()
        db.refresh(user)
        log.info("免密建号 id=%s", user.id, extra={"event": "auth.register.passwordless"})

    log.info("验证码登录成功 id=%s", user.id, extra={"event": "auth.login.email_code"})
    return TokenOut(access_token=create_access_token(user.id))


# ===== 找回密码 / 重置密码 =====


@router.post("/password/reset", response_model=TokenOut)
def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    email = codes.normalize_email(data.email)
    user = _find_user(db, email)
    if user is None:
        # 与"码无效"完全同话术：不暴露邮箱是否存在（不变量 I5）
        raise HTTPException(status_code=400, detail=codes.GENERIC_INVALID_MESSAGE)

    try:
        codes.verify_code(db, email=email, purpose="reset", code=data.code)
    except CodeInvalid:
        raise HTTPException(status_code=400, detail=codes.GENERIC_INVALID_MESSAGE) from None

    user.password_hash = hash_password(data.new_password)
    db.commit()

    log.info("密码已重置 id=%s", user.id, extra={"event": "auth.password.reset"})
    return TokenOut(access_token=create_access_token(user.id))


# ===== 已登录：设置 / 修改密码 =====


@router.post("/password/change")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.password_hash:
        # 有密码：必须提供当前密码
        if not data.old_password or not verify_password(data.old_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="当前密码不正确")
    else:
        # 免密账号：用邮箱验证码证明所有权（与找回同一 purpose，先请求再提交）
        if not data.code:
            raise HTTPException(status_code=400, detail="该账号还没有密码，请先获取邮箱验证码再设置")
        try:
            codes.verify_code(
                db,
                email=codes.normalize_email(current_user.email),
                purpose="reset",
                code=data.code,
            )
        except CodeInvalid:
            raise HTTPException(status_code=400, detail=codes.GENERIC_INVALID_MESSAGE) from None

    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    log.info("密码已更新 id=%s", current_user.id, extra={"event": "auth.password.change"})
    return {"ok": True}


# ===== 当前用户 =====


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

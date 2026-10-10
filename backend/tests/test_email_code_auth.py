"""邮箱验证码认证：不变量与安全边界回归测试（T1-T21）。

设计见 .deepcode/ADR-20261009-Waynote-email-code-auth.md §8。

测试策略：
- 拦截发信（monkeypatch app.core.email_code.send_email_code）拿到验证码，不碰真实 SMTP
- "已注册邮箱"用 helpers.make_user 造数；断言数据库真实状态用原生 SQL（绕开 ORM identity map）
- 限流是模块级内存态：autouse fixture 前后清零
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.core.email_code as email_code_module
from app.core.config import settings
from app.core.mailer import MailerError
from app.core.security import hash_password

from helpers import make_user

PASSWORD = "s3cret-123"


@pytest.fixture(autouse=True)
def _reset_limits() -> Iterator[None]:
    email_code_module.reset_rate_limit_state()
    yield
    email_code_module.reset_rate_limit_state()


@pytest.fixture()
def mailbox(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
    """拦截发信：记录 (收件人, 验证码, 用途)；同时把 SMTP 置为已配置。"""
    sent: list[tuple[str, str, str]] = []

    def fake_send(*, to: str, code: str, purpose: str, ttl_minutes: int) -> None:
        sent.append((to, code, purpose))

    monkeypatch.setattr(email_code_module, "send_email_code", fake_send)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_user", "noreply@test.invalid")
    monkeypatch.setattr(settings, "smtp_password", "test-auth-code")
    return sent


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _db_scalar(session: Session, sql: str, **params: object):
    """原生 SQL 读单值：绕开 ORM 缓存，断言数据库里的真实状态。"""
    return session.connection().execute(text(sql), params).scalar_one_or_none()


def _request_code(client, email: str, purpose: str = "login"):
    return client.post("/api/v1/auth/email-code", json={"email": email, "purpose": purpose})


def _issue_code(client, mailbox, email: str, purpose: str) -> str:
    resp = _request_code(client, email, purpose)
    assert resp.status_code == 200, resp.text
    assert mailbox and mailbox[-1][0] == email and mailbox[-1][2] == purpose
    return mailbox[-1][1]


def _login_with_code(client, email: str, code: str):
    return client.post("/api/v1/auth/login/email-code", json={"email": email, "code": code})


def _login_password(client, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ===== T1/T2 免密登录 =====


def test_T1_code_login_creates_passwordless_account(client, session, mailbox) -> None:
    email = _email("t1")
    code = _issue_code(client, mailbox, email, "login")

    resp = _login_with_code(client, email, code)
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == email
    assert body["has_password"] is False  # 免密账号
    assert _db_scalar(session, "SELECT count(*) FROM users WHERE email = :e", e=email) == 1


def test_T2_code_login_existing_user_does_not_duplicate(client, session, mailbox) -> None:
    user = make_user(session, _email("t2"))
    code = _issue_code(client, mailbox, user.email, "login")

    resp = _login_with_code(client, user.email, code)
    assert resp.status_code == 200, resp.text
    assert _db_scalar(session, "SELECT count(*) FROM users WHERE email = :e", e=user.email) == 1


# ===== T3/T4 尝试计数与作废 =====


def test_T3_wrong_code_increments_attempts_before_responding(client, session, mailbox) -> None:
    """不变量 I2：错误尝试必须先落库，否则并发可绕过尝试上限。"""
    email = _email("t3")
    _issue_code(client, mailbox, email, "login")

    resp = _login_with_code(client, email, "000000")
    assert resp.status_code == 400
    assert resp.json()["detail"] == email_code_module.GENERIC_INVALID_MESSAGE
    assert _db_scalar(session, "SELECT attempts FROM email_codes WHERE email = :e", e=email) == 1


def test_T4_code_is_burned_after_max_attempts(client, session, mailbox) -> None:
    email = _email("t4")
    code = _issue_code(client, mailbox, email, "login")

    for _ in range(settings.email_code_max_attempts):
        assert _login_with_code(client, email, "000000").status_code == 400

    # 就算拿到正确码也不放行
    assert _login_with_code(client, email, code).status_code == 400
    assert (
        _db_scalar(session, "SELECT attempts FROM email_codes WHERE email = :e", e=email)
        == settings.email_code_max_attempts
    )


# ===== T5 过期 =====


def test_T5_expired_code_rejected(client, session, mailbox) -> None:
    email = _email("t5")
    code = _issue_code(client, mailbox, email, "login")

    session.connection().execute(
        text("UPDATE email_codes SET expires_at = now() - interval '1 minute' WHERE email = :e"),
        {"e": email},
    )
    assert _login_with_code(client, email, code).status_code == 400


# ===== T6/T7/T8 频控 =====


def test_T6_cooldown_blocks_immediate_resend(client, mailbox) -> None:
    email = _email("t6")
    assert _request_code(client, email, "login").status_code == 200

    resp = _request_code(client, email, "login")
    assert resp.status_code == 429
    assert "秒" in resp.json()["detail"]


def test_T7_per_email_hourly_quota(client, mailbox, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "email_code_cooldown_seconds", 0)  # 只测小时配额
    email = _email("t7")

    for _ in range(settings.email_code_per_email_hour):
        assert _request_code(client, email, "login").status_code == 200
    assert _request_code(client, email, "login").status_code == 429


def test_T8_per_ip_hourly_quota_ignores_forged_headers(client, mailbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """IP 配额按真实直连地址计数：伪造 X-Forwarded-For 不能分桶绕过。"""
    monkeypatch.setattr(settings, "email_code_cooldown_seconds", 0)
    for index in range(settings.email_code_per_ip_hour):
        resp = _request_code(client, _email(f"t8{index}"), "login")
        assert resp.status_code == 200, f"第 {index + 1} 次应放行"

    forged = client.post(
        "/api/v1/auth/email-code",
        json={"email": _email("t8-forged"), "purpose": "login"},
        headers={"x-forwarded-for": "10.66.66.66"},
    )
    assert forged.status_code == 429


# ===== T9/T10/T11 不变量 =====


def test_T9_purpose_isolation(client, mailbox) -> None:
    """不变量 I4：login 码不能用于 reset。"""
    email = _email("t9")
    code = _issue_code(client, mailbox, email, "login")

    resp = client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "code": code, "new_password": PASSWORD},
    )
    assert resp.status_code == 400


def test_T10_code_is_single_use(client, mailbox) -> None:
    """不变量 I3：同一码第二次使用必须失败。"""
    email = _email("t10")
    code = _issue_code(client, mailbox, email, "login")

    assert _login_with_code(client, email, code).status_code == 200
    assert _login_with_code(client, email, code).status_code == 400


def test_T11_response_never_echoes_code(client, mailbox) -> None:
    """守卫：发码响应体绝不含验证码本身。"""
    email = _email("t11")
    resp = _request_code(client, email, "login")
    assert resp.status_code == 200
    code = mailbox[-1][1]
    assert code not in resp.text
    assert code not in resp.json()["message"]


# ===== T12/T13/T14 注册验证 =====


def test_T12_register_with_code(client, mailbox) -> None:
    email = _email("t12")
    code = _issue_code(client, mailbox, email, "register")

    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": "小旅", "code": code},
    )
    assert resp.status_code == 201, resp.text
    assert _login_password(client, email, PASSWORD).status_code == 200
    token = _login_password(client, email, PASSWORD).json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["has_password"] is True


def test_T13_register_validation_and_no_existence_leak(client, session, mailbox) -> None:
    """无码 → 422；错码时"已注册/未注册"响应体完全一致（不泄露邮箱是否存在）。"""
    no_code = client.post("/api/v1/auth/register", json={"email": _email("t13a"), "password": PASSWORD})
    assert no_code.status_code == 422

    existing = make_user(session, _email("t13b"))
    fresh = _email("t13c")

    body_existing = client.post(
        "/api/v1/auth/register", json={"email": existing.email, "password": PASSWORD, "code": "000001"}
    )
    body_fresh = client.post(
        "/api/v1/auth/register", json={"email": fresh, "password": PASSWORD, "code": "000001"}
    )
    assert body_existing.status_code == body_fresh.status_code == 400
    assert body_existing.json()["detail"] == body_fresh.json()["detail"]


def test_T14_register_existing_email_with_valid_code(client, session, mailbox) -> None:
    """持有有效 register 码（等价于已证明邮箱所有权）时，才允许暴露"已被注册"。"""
    existing = make_user(session, _email("t14"))
    email_code_module.request_code(
        session, email=existing.email, purpose="register", ip=None, deliver=True
    )
    code = mailbox[-1][1]

    resp = client.post(
        "/api/v1/auth/register",
        json={"email": existing.email, "password": PASSWORD, "code": code},
    )
    assert resp.status_code == 400
    assert "已被注册" in resp.json()["detail"]


# ===== T15/T16 找回密码 =====


def test_T15_reset_password_flow(client, session, mailbox) -> None:
    user = make_user(session, _email("t15"))
    user.password_hash = hash_password("old-password")
    session.flush()

    code = _issue_code(client, mailbox, user.email, "reset")
    resp = client.post(
        "/api/v1/auth/password/reset",
        json={"email": user.email, "code": code, "new_password": PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]  # 重置即登录
    assert _login_password(client, user.email, PASSWORD).status_code == 200
    assert _login_password(client, user.email, "old-password").status_code == 400


def test_T16_reset_unknown_email_is_generic_and_sends_nothing(client, mailbox) -> None:
    email = _email("t16-none")
    resp = _request_code(client, email, "reset")

    assert resp.status_code == 200  # 与已注册邮箱同话术
    assert mailbox == []  # 但绝不发信
    assert email_code_module.GENERIC_SENT_MESSAGE.split("{")[0] in resp.json()["message"]


# ===== T17/T18 已登录设置/修改密码 =====


def test_T17a_change_password_with_old_password(client, session) -> None:
    user = make_user(session, _email("t17a"))
    user.password_hash = hash_password("old-password")
    session.flush()
    token = _login_password(client, user.email, "old-password").json()["access_token"]

    resp = client.post(
        "/api/v1/auth/password/change",
        json={"old_password": "old-password", "new_password": PASSWORD},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert _login_password(client, user.email, PASSWORD).status_code == 200


def test_T17b_passwordless_account_sets_password_via_code(client, session, mailbox) -> None:
    user = make_user(session, _email("t17b"))
    user.password_hash = None
    session.flush()

    # 免密账号不能密码登录（统一话术里给出可行动指引）
    assert _login_password(client, user.email, "whatever").status_code == 400

    login_code = _issue_code(client, mailbox, user.email, "login")
    access = _login_with_code(client, user.email, login_code).json()["access_token"]

    reset_code = _issue_code(client, mailbox, user.email, "reset")
    resp = client.post(
        "/api/v1/auth/password/change",
        json={"code": reset_code, "new_password": PASSWORD},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200, resp.text

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.json()["has_password"] is True
    assert _login_password(client, user.email, PASSWORD).status_code == 200


def test_T18_change_password_rejects_wrong_inputs(client, session, mailbox) -> None:
    # 有密码：旧密码错 → 400
    user = make_user(session, _email("t18a"))
    user.password_hash = hash_password("old-password")
    session.flush()
    token = _login_password(client, user.email, "old-password").json()["access_token"]
    bad = client.post(
        "/api/v1/auth/password/change",
        json={"old_password": "wrong", "new_password": PASSWORD},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 400
    assert "当前密码" in bad.json()["detail"]

    # 免密账号：不给验证码 → 400
    bare = make_user(session, _email("t18b"))
    bare.password_hash = None
    session.flush()
    code = _issue_code(client, mailbox, bare.email, "login")
    access = _login_with_code(client, bare.email, code).json()["access_token"]
    missing = client.post(
        "/api/v1/auth/password/change",
        json={"new_password": PASSWORD},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert missing.status_code == 400
    assert "验证码" in missing.json()["detail"]


# ===== T19/T20 发信边界 =====


def test_T19_smtp_unconfigured_returns_503(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")

    resp = _request_code(client, _email("t19"), "login")
    assert resp.status_code == 503
    assert "邮件服务" in resp.json()["detail"]


def test_T20_send_failure_leaves_no_usable_code(
    client, session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """发信失败必须 502，且库里不留可用码（执行顺序：限流 → 发信 → 落码）。"""
    email = _email("t20")
    captured: list[str] = []

    def failing_send(*, to: str, code: str, purpose: str, ttl_minutes: int) -> None:
        captured.append(code)
        raise MailerError("boom")

    monkeypatch.setattr(email_code_module, "send_email_code", failing_send)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_user", "noreply@test.invalid")
    monkeypatch.setattr(settings, "smtp_password", "test-auth-code")

    resp = _request_code(client, email, "login")
    assert resp.status_code == 502

    assert captured, "发信被调用过"
    assert (
        _db_scalar(
            session,
            "SELECT count(*) FROM email_codes WHERE email = :e AND consumed_at IS NULL",
            e=email,
        )
        == 0
    )
    assert _login_with_code(client, email, captured[0]).status_code == 400


# ===== T21 既有契约回归 =====


def test_T21_password_login_message_covers_passwordless_account(client, session) -> None:
    user = make_user(session, _email("t21"))
    user.password_hash = None
    session.flush()

    resp = _login_password(client, user.email, "whatever")
    assert resp.status_code == 400
    # 统一话术（不泄露账号状态），但要给出可行动指引
    assert "验证码登录" in resp.json()["detail"]


def test_T21b_password_login_still_works(client, session) -> None:
    """既有契约回归：密码登录路径未被本特性破坏。"""
    user = make_user(session, _email("t21b"))
    user.password_hash = hash_password(PASSWORD)
    session.flush()

    resp = _login_password(client, user.email, PASSWORD)
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_users_password_hash_is_nullable_in_schema(session) -> None:
    """迁移前置条件：库结构允许 password_hash 为空（免密账号）。"""
    nullable = session.connection().execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'password_hash'"
        )
    ).scalar_one()
    assert nullable == "YES"


def test_email_codes_lookup_index_exists(session) -> None:
    count = session.connection().execute(
        text(
            "SELECT count(*) FROM pg_indexes "
            "WHERE tablename = 'email_codes' AND indexname = 'ix_email_codes_lookup'"
        )
    ).scalar_one()
    assert count == 1


def test_T22_register_input_validation_is_server_side(client, mailbox) -> None:
    """服务端校验是权威（前端校验只负责体验）：密码长度、昵称长度都在后端拦。

    另外验证顺序性：校验失败发生在业务逻辑之前，因此不会消耗验证码。
    """
    email = _email("t22")
    code = _issue_code(client, mailbox, email, "register")

    too_short = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "12345", "code": code}
    )
    assert too_short.status_code == 422

    too_long_name = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": "长" * 51, "code": code},
    )
    assert too_long_name.status_code == 422

    # 前两次 422 没有消耗验证码，第三次仍可用
    ok = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": "长" * 50, "code": code},
    )
    assert ok.status_code == 201, ok.text

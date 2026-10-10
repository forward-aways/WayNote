"""密码登录频控与应用层加固回归（设计见 .deepcode/ADR-20261010-Waynote-auth-rate-limit.md）。

要点：
- 只对"失败"记账：成功登录不消耗额度（T3）
- 两个维度都要过：IP（单点暴力）与邮箱（分布式针对单账号）
- 判定先 peek 再校验：已超限请求不做 bcrypt（T1 里用正确密码也能证明"没走到校验"）
- IP 取值走信任边界：不可信直连伪造 XFF 不能换桶（T4）
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.api.v1.auth import reset_login_rate_limit_state
from app.core.config import settings
from app.core.security import hash_password
from app.main import _docs_kwargs

from helpers import make_user

PASSWORD = "s3cret-123"


@pytest.fixture(autouse=True)
def _reset_login_limits() -> Iterator[None]:
    reset_login_rate_limit_state()
    yield
    reset_login_rate_limit_state()


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _login(client, email: str, password: str, **kwargs):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}, **kwargs)


def _user_with_password(session: Session, prefix: str):
    user = make_user(session, _email(prefix))
    user.password_hash = hash_password(PASSWORD)
    session.flush()
    return user


def test_T1_email_dimension_blocks_even_with_correct_password(client, session) -> None:
    user = _user_with_password(session, "rl-t1")

    for _ in range(settings.login_max_failures_per_email):
        assert _login(client, user.email, "wrong-password").status_code == 400

    resp = _login(client, user.email, PASSWORD)
    assert resp.status_code == 429
    assert "秒" in resp.json()["detail"]
    assert "验证码登录" in resp.json()["detail"]  # 给出可行动指引（反例 1 的缓解）


def test_T2_ip_dimension_blocks_across_emails(client) -> None:
    for index in range(settings.login_max_failures_per_ip):
        assert _login(client, _email(f"rl-t2-{index}"), "wrong-password").status_code == 400

    assert _login(client, _email("rl-t2-last"), "wrong-password").status_code == 429


def test_T3_success_does_not_consume_quota(client, session) -> None:
    user = _user_with_password(session, "rl-t3")

    for _ in range(settings.login_max_failures_per_email - 1):
        assert _login(client, user.email, "wrong-password").status_code == 400

    assert _login(client, user.email, PASSWORD).status_code == 200  # 成功不记账

    assert _login(client, user.email, "wrong-password").status_code == 400  # 最后一次失败仍放行
    assert _login(client, user.email, PASSWORD).status_code == 429  # 到上限后才拦


def test_T4_forged_forwarded_for_cannot_switch_bucket(client) -> None:
    """不可信直连时 XFF 不采信：换头仍按同一真实 IP 分桶。"""
    for index in range(settings.login_max_failures_per_ip):
        resp = _login(
            client,
            _email(f"rl-t4-{index}"),
            "wrong-password",
            headers={"x-forwarded-for": f"10.0.0.{index}"},
        )
        assert resp.status_code == 400

    forged = _login(
        client,
        _email("rl-t4-forged"),
        "wrong-password",
        headers={"x-forwarded-for": "10.9.9.9"},
    )
    assert forged.status_code == 429


def test_T5_docs_switch_wiring() -> None:
    """生产默认不注册文档路由（不注册 ≠ 加鉴权遮挡）。"""
    assert _docs_kwargs(False) == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    assert _docs_kwargs(True) == {}


def test_T6_normal_login_still_works(client, session) -> None:
    user = _user_with_password(session, "rl-t6")
    resp = _login(client, user.email, PASSWORD)
    assert resp.status_code == 200
    assert resp.json()["access_token"]

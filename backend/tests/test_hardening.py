"""信任边界与上报端点加固回归测试（S1-S6）。

设计见 .deepcode/ADR-20260929-Waynote-trust-boundary-hardening.md
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.v1.client_logs import reset_rate_limit_state
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app

PAYLOAD = {"kind": "vue", "message": "render failed", "url": "http://localhost:5173/trips"}


@pytest.fixture(autouse=True)
def _reset_limits() -> Iterator[None]:
    reset_rate_limit_state()
    yield
    reset_rate_limit_state()


def test_untrusted_peer_ignores_forwarded_for() -> None:
    """S1 回归：不可信直连时伪造 XFF 不能绕过匿名限流（修复前每次换头均可通过）。"""
    client = TestClient(app)  # 默认直连对端为 testclient（不可信）
    statuses = [
        client.post(
            "/api/v1/client-logs",
            json=PAYLOAD,
            headers={"x-forwarded-for": f"10.0.0.{index}"},
        ).status_code
        for index in range(3)
    ]

    assert statuses == [204, 204, 429]  # 按直连 IP 计数，匿名档 2 次/分钟


def test_trusted_proxy_uses_forwarded_for() -> None:
    """S2：可信直连（127.0.0.1）时 XFF 被采信为限流 key（反代场景）。"""
    client = TestClient(app, client=("127.0.0.1", 40001))
    statuses = [
        client.post(
            "/api/v1/client-logs",
            json=PAYLOAD,
            headers={"x-forwarded-for": f"10.1.0.{index}"},
        ).status_code
        for index in range(3)
    ]

    assert statuses == [204, 204, 204]  # 不同 XFF 各自分桶，未触发匿名档上限


def test_authenticated_tier_has_separate_quota_and_anon_stack_truncated(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """S3：带有效 JWT 走登录档（20/min）；匿名档 stack 截断至 500。"""
    caplog.set_level(logging.WARNING, logger="waynote.frontend")
    client = TestClient(app)
    headers = {"authorization": f"Bearer {create_access_token(999_999)}"}

    statuses = [client.post("/api/v1/client-logs", json=PAYLOAD, headers=headers).status_code for _ in range(3)]
    assert statuses == [204, 204, 204]  # 不受匿名档 2/min 限制

    long_stack = "x" * 1000
    resp = client.post(
        "/api/v1/client-logs",
        json={**PAYLOAD, "stack": long_stack},
        headers={"x-forwarded-for": "10.2.0.1"},
    )
    assert resp.status_code == 204

    events = [record for record in caplog.records if getattr(record, "event", "") == "frontend.error"]
    assert events, "前端异常必须落日志"
    assert events[0].name == "waynote.frontend"

    anonymous = next(record for record in events if getattr(record, "tier", "") == "anonymous")
    assert len(getattr(anonymous, "stack", "")) == 500  # 匿名档截断生效


def test_registration_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """S6：ALLOW_REGISTRATION=false 时注册返回 403；为 true 时放行到校验层。"""
    client = TestClient(app)

    monkeypatch.setattr(settings, "allow_registration", False)
    resp = client.post("/api/v1/auth/register", json={"email": "new@example.com", "password": "123456"})
    assert resp.status_code == 403
    assert "关闭" in resp.json()["detail"]

    monkeypatch.setattr(settings, "allow_registration", True)
    resp = client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "123456"})
    assert resp.status_code == 422  # 已放行（未真正写库）

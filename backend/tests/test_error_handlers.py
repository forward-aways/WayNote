"""统一异常处理与请求追踪回归测试。"""

from __future__ import annotations

import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import install_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.main import app


def _boom_app() -> FastAPI:
    """最小复现应用：验证未捕获异常 → 统一 500 信封 + request_id。"""
    test_app = FastAPI()
    test_app.add_middleware(RequestContextMiddleware, slow_request_ms=800)
    install_exception_handlers(test_app)

    @test_app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom-secret-detail")

    return test_app


def test_validation_error_hides_raw_input() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "s3cr3t-DO-NOT-LOG"},
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"] == "请求参数校验失败"
    assert body["request_id"]
    assert all("loc" in item and "msg" in item for item in body["errors"])

    dumped = json.dumps(body, ensure_ascii=False)
    assert "s3cr3t-DO-NOT-LOG" not in dumped  # 绝不回传/记录原始输入
    assert "not-an-email" not in dumped


def test_not_found_envelope_and_request_id_echo() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/never-exists", headers={"x-request-id": "test-rid-1"})

    assert resp.status_code == 404
    body = resp.json()
    assert body["request_id"] == "test-rid-1"
    assert resp.headers.get("x-request-id") == "test-rid-1"
    assert "detail" in body


def test_unhandled_exception_returns_unified_500() -> None:
    client = TestClient(_boom_app(), raise_server_exceptions=False)
    resp = client.get("/boom", headers={"x-request-id": "rid-500"})

    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "服务器内部错误，请稍后重试"
    assert body["request_id"] == "rid-500"
    assert resp.headers.get("x-request-id") == "rid-500"
    assert "kaboom-secret-detail" not in json.dumps(body, ensure_ascii=False)


def test_access_log_level_mapping(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="waynote.access")
    client = TestClient(app)

    client.get("/api/v1/health")
    client.get("/api/v1/never-exists")

    records = [record for record in caplog.records if record.name == "waynote.access"]
    health = next(record for record in records if getattr(record, "path", "") == "/api/v1/health")
    not_found = next(
        record for record in records if getattr(record, "path", "") == "/api/v1/never-exists"
    )

    assert health.levelno == logging.DEBUG  # 探活降噪
    assert not_found.levelno == logging.WARNING  # 4xx 告警
    assert getattr(not_found, "status", None) == 404
    assert getattr(not_found, "duration_ms", None) is not None


def test_client_logs_endpoint_rate_limit_and_audit(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="waynote.frontend")
    client = TestClient(app)
    headers = {"x-forwarded-for": "10.9.9.9"}
    payload = {
        "kind": "vue",
        "message": "render failed",
        "stack": "at Foo.vue:1",
        "url": "http://localhost:5173/trips",
        "app_version": "dev",
    }

    first = client.post("/api/v1/client-logs", json=payload, headers=headers)
    assert first.status_code == 204

    statuses = [client.post("/api/v1/client-logs", json=payload, headers=headers).status_code for _ in range(10)]
    assert statuses.count(429) == 1  # 第 11 次触发限流
    assert statuses[-1] == 429

    events = [record for record in caplog.records if getattr(record, "event", "") == "frontend.error"]
    assert events, "前端异常必须落日志"
    assert events[0].name == "waynote.frontend"

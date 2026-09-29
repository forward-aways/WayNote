"""前端错误上报：接收浏览器侧未捕获异常，写入后端统一日志。

安全模型（见 .deepcode/ADR-20260929-Waynote-trust-boundary-hardening.md）：
- IP 解析走统一信任边界（仅可信代理的 XFF 被采信），限流不可通过伪造头绕过
- 两档限流：登录用户 20 次/分钟（key=user_id）；匿名 2 次/分钟（key=真实 IP）
- 全局兜底：所有来源合计 10 次/分钟，防分布式灌入
- 匿名上报的 stack 截断至 500 字符；登录用户保留 4000
- 内存实现：单进程语义，重启清零（多进程部署需外部限流，见 ADR 边界）
"""

from __future__ import annotations

import time
from functools import lru_cache

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger, user_id_var
from app.core.net import parse_trusted_proxies, resolve_client_ip
from app.core.security import decode_token

router = APIRouter(prefix="/client-logs", tags=["client-logs"])
log = get_logger("frontend")

_WINDOW_SECONDS = 60
_ANON_LIMIT = 2
_USER_LIMIT = 20
_GLOBAL_LIMIT = 10
_MAX_KEYS = 4096
_ANON_STACK_LIMIT = 500
_USER_STACK_LIMIT = 4000

_buckets: dict[str, list[float]] = {}


class ClientLogIn(BaseModel):
    kind: str = Field(default="error", max_length=20)
    message: str = Field(min_length=1, max_length=500)
    stack: str | None = Field(default=None, max_length=4000)
    url: str = Field(default="", max_length=500)
    app_version: str | None = Field(default=None, max_length=50)
    request_id: str | None = Field(default=None, max_length=64)


@lru_cache(maxsize=8)
def _trusted(raw: str) -> frozenset[str]:
    return parse_trusted_proxies(raw)


def reset_rate_limit_state() -> None:
    """测试用：清空限流计数（生产无需调用）。"""
    _buckets.clear()


def _hit(key: str, limit: int, now: float) -> bool:
    """记录一次访问；返回 True 表示该 key 已超限。"""
    stamps = [stamp for stamp in _buckets.get(key, []) if now - stamp < _WINDOW_SECONDS]
    if len(stamps) >= limit:
        _buckets[key] = stamps
        return True
    stamps.append(now)
    _buckets[key] = stamps
    return False


def _rate_limited(ip: str, user_id: int | None) -> bool:
    now = time.monotonic()
    if len(_buckets) > _MAX_KEYS:
        _buckets.clear()
    if _hit("global", _GLOBAL_LIMIT, now):
        return True
    if user_id is not None:
        return _hit(f"user:{user_id}", _USER_LIMIT, now)
    return _hit(f"anon:{ip}", _ANON_LIMIT, now)


@router.post("", status_code=204)
def submit_client_log(payload: ClientLogIn, request: Request) -> Response:
    ip = resolve_client_ip(request.scope, _trusted(settings.trusted_proxy_ips))

    # 尽力关联用户（不查库，仅解码）；失败即匿名档
    user_id: int | None = None
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        user_id = decode_token(auth[7:])
        if user_id is not None:
            user_id_var.set(user_id)

    if _rate_limited(ip, user_id):
        return Response(status_code=429)

    tier = "user" if user_id is not None else "anonymous"
    stack_limit = _USER_STACK_LIMIT if user_id is not None else _ANON_STACK_LIMIT

    log.warning(
        "前端异常 tier=%s kind=%s page=%s app=%s client_request_id=%s message=%s",
        tier,
        payload.kind,
        payload.url,
        payload.app_version or "-",
        payload.request_id or "-",
        payload.message,
        extra={
            "event": "frontend.error",
            "tier": tier,
            "kind": payload.kind,
            "page": payload.url,
            "app_version": payload.app_version,
            "client_request_id": payload.request_id,
            "ip": ip,
            "stack": (payload.stack or "")[:stack_limit],
        },
    )
    return Response(status_code=204)

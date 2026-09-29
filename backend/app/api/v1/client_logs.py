"""前端错误上报：接收浏览器侧未捕获异常，写入后端统一日志。

安全权衡（个人工具规模）：
- 未认证可写 → 内存令牌桶限流（默认 10 次/分钟/IP）+ 体积上限 + 日志留存兜底
- 携带有效 token 时尽力关联 user_id（不查询数据库，仅解码）
- 若未来开放注册/多用户，需升级为签名或强制鉴权
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.core.logging import get_logger, user_id_var
from app.core.security import decode_token

router = APIRouter(prefix="/client-logs", tags=["client-logs"])
log = get_logger("frontend")

_WINDOW_SECONDS = 60
_MAX_PER_WINDOW = 10
_MAX_CLIENTS = 2048
_buckets: dict[str, list[float]] = {}


class ClientLogIn(BaseModel):
    kind: str = Field(default="error", max_length=20)
    message: str = Field(min_length=1, max_length=500)
    stack: str | None = Field(default=None, max_length=4000)
    url: str = Field(default="", max_length=500)
    app_version: str | None = Field(default=None, max_length=50)
    request_id: str | None = Field(default=None, max_length=64)


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    if len(_buckets) > _MAX_CLIENTS:
        _buckets.clear()
    stamps = [t for t in _buckets.get(ip, []) if now - t < _WINDOW_SECONDS]
    if len(stamps) >= _MAX_PER_WINDOW:
        _buckets[ip] = stamps
        return True
    stamps.append(now)
    _buckets[ip] = stamps
    return False


@router.post("", status_code=204)
def submit_client_log(payload: ClientLogIn, request: Request) -> Response:
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()) or (
        request.client.host if request.client else "-"
    )
    if _rate_limited(ip):
        return Response(status_code=429)

    # 尽力关联用户（不查库，仅解码）；失败静默忽略
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        user_id = decode_token(auth[7:])
        if user_id is not None:
            user_id_var.set(user_id)

    log.warning(
        "前端异常 kind=%s page=%s app=%s client_request_id=%s message=%s",
        payload.kind,
        payload.url,
        payload.app_version or "-",
        payload.request_id or "-",
        payload.message,
        extra={
            "event": "frontend.error",
            "kind": payload.kind,
            "page": payload.url,
            "app_version": payload.app_version,
            "client_request_id": payload.request_id,
            "ip": ip,
            "stack": (payload.stack or "")[:2000],
        },
    )
    return Response(status_code=204)

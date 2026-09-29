"""请求上下文与访问日志中间件（纯 ASGI 实现）。

为什么不用 BaseHTTPMiddleware：它把请求放入独立 task，contextvars 不向端点传播
（request_id 会丢失），且流式/后台任务存在已知问题。
纯 ASGI 中间件与端点在同一调用栈，contextvars 天然可见（含线程池中的同步端点）。
"""

from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response
from app.core.logging import get_logger, request_id_var, user_id_var

log = get_logger("access")

_HEALTH_PATH = "/api/v1/health"
_RID_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, slow_request_ms: int = 800) -> None:
        self.app = app
        self.slow_request_ms = slow_request_ms

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "-"))
        path = str(scope.get("path", "-"))
        request_id = self._resolve_request_id(scope)
        rid_token = request_id_var.set(request_id)
        uid_token = user_id_var.set(None)
        start = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_started = True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # 未捕获异常兜底：FastAPI 的 exception_handler 只在路由层生效，
            # 中间件层（含未注册类型）的异常在此统一记录并返回统一信封。
            log.error(
                "未捕获异常 %s %s",
                method,
                path,
                extra={"status": 500, "method": method, "path": path},
                exc_info=True,
            )
            if not response_started:
                response = error_response(500, "服务器内部错误，请稍后重试")
                await response(scope, receive, send_wrapper)
            else:
                raise  # 响应已部分发出，无法补救，交由上层断开连接
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            level = self._level_for(method, path, status_code)
            log.log(
                level,
                "%s %s %s",
                method,
                path,
                status_code,
                extra={
                    "status": status_code,
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "ip": self._client_ip(scope),
                    "slow": duration_ms >= self.slow_request_ms,
                },
            )
            request_id_var.reset(rid_token)
            user_id_var.reset(uid_token)

    def _level_for(self, method: str, path: str, status: int) -> int:
        if path == _HEALTH_PATH:
            return logging.DEBUG
        if status >= 500:
            return logging.ERROR
        if status >= 400:
            return logging.WARNING
        return logging.INFO

    @staticmethod
    def _resolve_request_id(scope: Scope) -> str:
        incoming = Headers(scope=scope).get("x-request-id", "")
        cleaned = _RID_UNSAFE.sub("", incoming)[:32]
        return cleaned or uuid4().hex[:12]

    @staticmethod
    def _client_ip(scope: Scope) -> str:
        forwarded = Headers(scope=scope).get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "-"

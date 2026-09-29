"""统一异常处理：HTTP 异常 / 参数校验 / 数据库约束 → 统一 JSON 信封。

未捕获异常由 RequestContextMiddleware 兜底（见 middleware.py，可携带 X-Request-ID）。
响应信封：{"detail": str, "request_id": str, "errors"?: [...]}，与前端既有解析兼容。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_var

log = get_logger("errors")


def level_for_status(status: int) -> int:
    if status >= 500:
        return logging.ERROR
    if status == 404:
        return logging.INFO
    return logging.WARNING


def error_response(
    status: int,
    detail: str,
    *,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {"detail": detail, "request_id": request_id_var.get()}
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, headers=headers)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status = exc.status_code
        log.log(
            level_for_status(status),
            "%s %s -> %s %s",
            request.method,
            request.url.path,
            status,
            exc.detail,
            extra={"status": status, "method": request.method, "path": request.url.path},
        )
        return error_response(status, str(exc.detail), headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # 只保留字段路径与原因，绝不记录 errors[].input（可能包含密码等原始输入）
        errors = [
            {"loc": ".".join(str(part) for part in error.get("loc", ())), "msg": str(error.get("msg", ""))}
            for error in exc.errors()
        ]
        fields = "、".join(error["loc"] for error in errors) or "(unknown)"
        log.warning(
            "参数校验失败 %s %s -> 422 fields=[%s]",
            request.method,
            request.url.path,
            fields,
            extra={
                "status": 422,
                "method": request.method,
                "path": request.url.path,
                "fields": fields,
                "error_count": len(errors),
            },
        )
        return error_response(422, "请求参数校验失败", errors=errors)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        log.error(
            "数据库约束冲突 %s %s -> 409: %s",
            request.method,
            request.url.path,
            exc.orig,
            extra={"status": 409, "method": request.method, "path": request.url.path},
            exc_info=True,
        )
        return error_response(409, "数据冲突或不满足约束，请检查后重试")

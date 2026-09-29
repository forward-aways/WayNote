from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.net import parse_trusted_proxies
from app.db.session import engine
from app.api.v1 import auth, client_logs, places, trip_days, trips


# 日志必须在应用构建前装配（幂等）
setup_logging(settings)
log = get_logger("app")

app = FastAPI(title=settings.app_name)

# 请求上下文 + 访问日志（纯 ASGI，见 core/middleware.py）
app.add_middleware(
    RequestContextMiddleware,
    slow_request_ms=settings.log_slow_request_ms,
    trusted_proxies=parse_trusted_proxies(settings.trusted_proxy_ips),
)
# 统一异常信封（HTTP 异常 / 参数校验 / 数据库约束）
install_exception_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(trips.router, prefix="/api/v1")
app.include_router(trip_days.router, prefix="/api/v1")
app.include_router(places.router, prefix="/api/v1")
app.include_router(client_logs.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Waynote API is running"}


@app.get("/api/v1/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

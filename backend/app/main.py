from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.net import parse_trusted_proxies
from app.db.session import engine
from app.api.v1 import auth, client_logs, places, trip_days, trips, uploads


# 日志必须在应用构建前装配（幂等）
setup_logging(settings)
log = get_logger("app")


def _docs_kwargs(enabled: bool) -> dict[str, str | None]:
    """生产不注册 API 文档路由（见 .deepcode/ADR-20261010-Waynote-auth-rate-limit.md）。

    文档 = 未鉴权的接口地图，属于侦察面；用"不注册"而不是"加鉴权遮挡"。
    本地开发在 backend/.env 里设 DOCS_ENABLED=true 即可照旧访问 /docs。
    """
    if enabled:
        return {}
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


app = FastAPI(title=settings.app_name, **_docs_kwargs(settings.docs_enabled))

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
app.include_router(uploads.router, prefix="/api/v1")

# 媒体文件：开发环境由后端直供（生产由 nginx 的 /media/ location 接管，见 ADR-20261012 §4.6）
app.mount(
    settings.media_url_prefix,
    StaticFiles(directory=settings.media_root, check_dir=False),
    name="media",
)


@app.get("/")
def root():
    return {"message": "Waynote API is running"}


@app.get("/api/v1/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

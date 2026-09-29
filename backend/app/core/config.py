from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env 固定指向 backend/.env，与启动时的工作目录无关
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

    # 必填项：缺失或未配置时启动即失败（fail-fast），杜绝不安全的默认密钥/连接串。
    # 详见 .deepcode/ADR-20260929-Waynote-cascade-and-secrets.md
    database_url: str
    secret_key: str
    app_name: str = "Waynote API"

    # 日志（见 .deepcode/ADR-20260929-Waynote-logging-and-error-handling.md）
    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: Path = Path(__file__).resolve().parents[2] / "logs"
    log_retention_days: int = 14
    log_color: Literal["auto", "always", "never"] = "auto"
    log_slow_request_ms: int = 800
    log_max_bytes: int = 10 * 1024 * 1024  # 单文件上限（0=不限制），与每日轮转取先到者

    # 信任边界与安全（见 .deepcode/ADR-20260929-Waynote-trust-boundary-hardening.md）
    # 仅当直连对端在此白名单内才采信 X-Forwarded-For；严禁填公网网段
    trusted_proxy_ips: str = "127.0.0.1,::1"
    allow_registration: bool = True


settings = Settings()

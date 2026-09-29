from pathlib import Path

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


settings = Settings()

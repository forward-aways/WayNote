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

    # 邮箱验证码与 SMTP（见 .deepcode/ADR-20261009-Waynote-email-code-auth.md §6.4）
    # 凭据留空时启动不受影响，但发码接口会返回 503（明确失败，不静默降级）
    smtp_host: str = ""
    smtp_port: int = 465  # 465=SSL（163/QQ），587=STARTTLS
    smtp_starttls: bool = False
    smtp_timeout_seconds: int = 10
    smtp_user: str = ""
    smtp_password: str = ""  # 邮箱「客户端授权码」，不是登录密码
    smtp_from: str = ""  # 留空则用 smtp_user
    smtp_from_name: str = "途笺 WayNote"
    email_code_ttl_minutes: int = 10
    email_code_cooldown_seconds: int = 60
    email_code_max_attempts: int = 5
    email_code_per_email_hour: int = 5
    email_code_per_email_day: int = 10
    email_code_per_ip_hour: int = 20
    email_code_global_hour: int = 100

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def mail_from(self) -> str:
        return self.smtp_from or self.smtp_user

    # 应用层加固（见 .deepcode/ADR-20261010-Waynote-auth-rate-limit.md）
    # 生产默认关文档：/docs /redoc /openapi.json 是未鉴权的接口地图（本地开发在 .env 里设 true）
    docs_enabled: bool = False
    # 密码登录失败频控：IP 维度挡单点暴力，邮箱维度挡分布式针对单账号（只对失败记账）
    login_max_failures_per_ip: int = 10
    login_max_failures_per_email: int = 5
    login_failure_window_seconds: int = 300

    # 图片与本地媒体存储（见 .deepcode/ADR-20261012-Waynote-image-upload.md §4.1/§4.6）
    # 生产 .env 指向独立目录（如 /home/ubuntu/waynote-media，不放在代码仓库内）；
    # 默认落在 backend/uploads（已 gitignore），与启动时的工作目录无关。
    media_root: Path = Path(__file__).resolve().parents[2] / "uploads"
    media_url_prefix: str = "/media"
    media_max_bytes: int = 4 * 1024 * 1024  # 单图硬上限（前端压缩后通常 300KB~1MB）
    media_max_edge: int = 2000  # 主图最长边
    media_thumb_edge: int = 640  # 缩略图最长边
    media_upload_per_day: int = 100  # 每用户每日上传次数上限（防滥用）


settings = Settings()

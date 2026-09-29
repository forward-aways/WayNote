"""统一日志机制：控制台高亮 + JSON Lines 文件 + 脱敏 + 每日轮转留存。

设计见 .deepcode/ADR-20260929-Waynote-logging-and-error-handling.md
- 唯一出口：业务代码只允许 get_logger() + %s 占位符，禁止拼接敏感值
- 脱敏是最后防线：即使业务代码写错，密码/令牌/邮箱也不会明文落盘
- 留存清理：TimedRotatingFileHandler(backupCount=保留天数) 每日轮转时自动删除过期文件
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import sys
import time
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path

from app.core.config import Settings

# ===== 请求上下文（由中间件/鉴权依赖写入，日志自动携带） =====
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)

# 标准 LogRecord 属性（用于提取业务 extra 字段）
_STANDARD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName"}

# ===== 脱敏 =====
_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|token|secret|authorization|cookie)\b"
    r"([\"']?\s*[:=]\s*[\"']?)([^\s\"',;}]+)"
)
_EMAIL_RE = re.compile(r"([\w.+-]{1,2})[\w.+-]*(@[\w-]+(?:\.[\w-]+)+)")


def mask_text(text: str) -> str:
    """对输出文本做统一脱敏：密钥类字段置 ***，邮箱保留前两位。"""
    text = _SECRET_RE.sub(r"\1\2***", text)
    text = _EMAIL_RE.sub(r"\1***\2", text)
    return text


# ===== ANSI 高亮 =====
_RESET = "\033[0m"
_DIM = "\033[2m"
_LEVEL_COLOR = {
    "DEBUG": "\033[90m",
    "INFO": "\033[36m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[1;37;41m",
}


def _status_color(status: int) -> str:
    if status >= 500:
        return "\033[31m"
    if status >= 400:
        return "\033[33m"
    if status >= 300:
        return "\033[36m"
    return "\033[32m"


def _enable_windows_ansi() -> bool:
    """Windows 控制台开启 VT 序列（失败则不高亮）。"""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


def should_use_color(mode: str) -> bool:
    if mode == "never":
        return False
    if mode == "always":
        return True
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stderr.isatty():
        return False
    return _enable_windows_ansi()


# ===== Formatter =====
class ConsoleFormatter(logging.Formatter):
    """控制台可读格式，按级别/状态码/耗时高亮。"""

    def __init__(self, colors: bool, slow_ms: int) -> None:
        super().__init__()
        self.colors = colors
        self.slow_ms = slow_ms

    def _c(self, code: str, text: str) -> str:
        return f"{code}{text}{_RESET}" if self.colors else text

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level = record.levelname.ljust(7)
        level_text = self._c(_LEVEL_COLOR.get(record.levelname, ""), level)
        logger_name = record.name

        rid = getattr(record, "request_id", None) or request_id_var.get()
        rid_text = self._c("\033[36m", f"[{rid}]") if rid and rid != "-" else "[-]"

        message = record.getMessage()
        status = getattr(record, "status", None)
        if status is not None:
            message = message.replace(str(status), self._c(_status_color(int(status)), str(status)), 1)
        duration = getattr(record, "duration_ms", None)
        if duration is not None:
            ms = f"{duration}ms"
            if duration >= self.slow_ms * 2:
                ms = self._c("\033[31m", ms)
            elif duration >= self.slow_ms:
                ms = self._c("\033[33m", ms)
            else:
                ms = self._c(_DIM, ms)
            message = f"{message} {ms}"

        extras = []
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key.startswith("_") or key in {
                "request_id",
                "user_id",
                "status",
                "duration_ms",
                "method",
                "path",
            }:
                continue
            extras.append(f"{key}={value}")
        user_id = getattr(record, "user_id", None) or user_id_var.get()
        if user_id is not None:
            extras.append(f"user={user_id}")
        suffix = (" " + " ".join(extras)) if extras else ""

        line = f"{ts} {level_text} {logger_name} {rid_text} {message}{suffix}"
        if record.exc_info:
            line += "\n" + self._c("\033[31m", self.formatException(record.exc_info))
        return mask_text(line)


class JsonFormatter(logging.Formatter):
    """JSON Lines：每行一条，便于 grep / jq / 后续采集。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
            "user_id": getattr(record, "user_id", None) or user_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key.startswith("_") or key in payload:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return mask_text(json.dumps(payload, ensure_ascii=False, default=str))


# ===== Handler 工厂（测试与生产共用同一构造逻辑） =====
def build_file_handler(log_path: Path, retention_days: int) -> logging.handlers.TimedRotatingFileHandler:
    handler = logging.handlers.TimedRotatingFileHandler(
        log_path,
        when="midnight",
        backupCount=retention_days,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(JsonFormatter())
    return handler


def cleanup_old_logs(log_dir: Path, retention_days: int) -> int:
    """启动清扫：删除目录中超过保留期的轮转文件（覆盖手工运行等遗留）。"""
    if not log_dir.is_dir():
        return 0
    cutoff = time.time() - retention_days * 86_400
    removed = 0
    for path in log_dir.glob("waynote.log.*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


# ===== 装配 =====
_configured = False


def setup_logging(settings: Settings) -> None:
    """幂等装配：root 双写（控制台 + 文件），收敛 uvicorn 日志，降噪第三方。"""
    global _configured
    if _configured:
        return
    _configured = True

    if os.name == "nt":
        try:
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(
        ConsoleFormatter(colors=should_use_color(settings.log_color), slow_ms=settings.log_slow_request_ms)
    )
    root.addHandler(console)

    if settings.log_to_file:
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        root.addHandler(build_file_handler(settings.log_dir / "waynote.log", settings.log_retention_days))
        removed = cleanup_old_logs(settings.log_dir, settings.log_retention_days)
        if removed:
            root.info("已清理 %s 个过期日志文件", removed, extra={"event": "logs.cleanup"})

    # uvicorn 收敛到同一套 handler；access 由中间件统一输出，关闭避免重复
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
    access.disabled = True

    # 第三方降噪
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """统一前缀 waynote.；业务模块传 'api.trips' 这类短名。"""
    if name.startswith("waynote"):
        return logging.getLogger(name)
    return logging.getLogger(f"waynote.{name}")

"""日志机制回归测试：脱敏、高亮、JSON 结构、留存清理装配。"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from app.core.logging import (
    ConsoleFormatter,
    JsonFormatter,
    build_file_handler,
    cleanup_old_logs,
    mask_text,
)


def _record(level: int, msg: str, args: tuple = ()) -> logging.LogRecord:
    return logging.LogRecord("waynote.test", level, __file__, 1, msg, args, None)


def test_mask_text_masks_secrets_and_emails() -> None:
    text = "login password=abc123 token:xyz authorization=bearer123 user=a@b.com"
    masked = mask_text(text)

    assert "abc123" not in masked
    assert "xyz" not in masked
    assert "bearer123" not in masked
    assert "a@b.com" not in masked
    assert "password=***" in masked
    assert "token:***" in masked


def test_json_formatter_masks_message_and_keeps_structure() -> None:
    formatter = JsonFormatter()
    record = _record(logging.INFO, "登录成功 email=%s", ("demo@example.com",))
    record.event = "auth.login"

    output = formatter.format(record)

    assert "demo@example.com" not in output
    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["logger"] == "waynote.test"
    assert data["request_id"] == "-"
    assert data["event"] == "auth.login"
    assert "de***@example.com" in data["msg"]


def test_console_formatter_highlights_level_status_and_slow_request() -> None:
    record = _record(logging.INFO, "GET /api/v1/trips 200")
    record.status = 200
    record.duration_ms = 1500.0
    record.request_id = "abc123"

    colored = ConsoleFormatter(colors=True, slow_ms=800).format(record)
    plain = ConsoleFormatter(colors=False, slow_ms=800).format(record)

    assert "\033[" in colored  # 级别/状态/耗时高亮
    assert "[abc123]" in colored
    assert "\033[" not in plain
    assert "[abc123]" in plain
    assert "1500.0ms" in plain


def test_build_file_handler_wires_rotation_and_retention(tmp_path: Path) -> None:
    handler = build_file_handler(tmp_path / "waynote.log", retention_days=3)
    try:
        assert str(handler.when).upper() == "MIDNIGHT"
        assert handler.backupCount == 3
        assert handler.encoding == "utf-8"
        assert isinstance(handler.formatter, JsonFormatter)
    finally:
        handler.close()


def test_cleanup_old_logs_removes_only_expired_files(tmp_path: Path) -> None:
    now = time.time()
    day = 86_400
    files = {
        "waynote.log.2026-08-01": now - 20 * day,  # 过期
        "waynote.log.2026-08-05": now - 15 * day,  # 过期
        "waynote.log.2026-09-28": now - 1 * day,  # 保留
        "other.log": now - 99 * day,  # 非本机制文件，不动
    }
    for name, mtime in files.items():
        path = tmp_path / name
        path.write_text("x", encoding="utf-8")
        os.utime(path, (mtime, mtime))

    removed = cleanup_old_logs(tmp_path, retention_days=14)

    assert removed == 2
    assert not (tmp_path / "waynote.log.2026-08-01").exists()
    assert not (tmp_path / "waynote.log.2026-08-05").exists()
    assert (tmp_path / "waynote.log.2026-09-28").exists()
    assert (tmp_path / "other.log").exists()


def test_uvicorn_access_logger_is_disabled() -> None:
    """装配后 uvicorn.access 必须关闭，避免与中间件访问日志重复。"""
    import app.main  # noqa: F401  触发 setup_logging

    assert logging.getLogger("uvicorn.access").disabled is True

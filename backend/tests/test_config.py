"""配置层回归测试：Settings 是唯一配置入口，必填项缺失必须 fail-fast。"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_fail_fast_when_required_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """T7 回归：修复前 SECRET_KEY 有硬编码默认值、DB URL 有默认值，缺失配置也能启动。"""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reads_env_file_independent_of_cwd() -> None:
    """env_file 使用绝对路径，任意工作目录下都能读到 backend/.env。"""
    settings = Settings()

    assert settings.database_url.startswith("postgresql")
    assert len(settings.secret_key) >= 32

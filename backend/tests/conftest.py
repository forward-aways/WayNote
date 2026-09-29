import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """默认复用开发库连接，通过事务回滚保证测试不落数据；可用 TEST_DATABASE_URL 指向独立库。"""
    url = os.getenv("TEST_DATABASE_URL") or settings.database_url
    engine = create_engine(url, poolclass=NullPool)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def connection(engine: Engine) -> Iterator[Connection]:
    """连接级事务：级联删除在 flush 时真实执行，测试结束整体回滚。"""
    conn = engine.connect()
    conn.begin()
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture()
def session(connection: Connection) -> Iterator[Session]:
    """会话加入外层事务（SAVEPOINT），与 API 共享同一事务可见性。"""
    db = Session(bind=connection)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    """FastAPI get_db 依赖覆盖为测试会话，请求内 commit 只释放 SAVEPOINT。"""

    def override_get_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

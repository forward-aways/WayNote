from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 创建数据库引擎
engine = create_engine(settings.database_url)
# 创建会话
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
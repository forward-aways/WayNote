from app.models.user import Base, User
from app.models.trip import Trip
from app.models.trip_day import TripDay
from app.models.place import Place

# 集中注册全部模型（Alembic autogenerate 依赖此处导入），并显式声明为包级导出
__all__ = ["Base", "User", "Trip", "TripDay", "Place"]

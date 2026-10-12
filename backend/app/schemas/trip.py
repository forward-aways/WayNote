from pydantic import BaseModel
from datetime import datetime


class TripCreate(BaseModel):
    title: str
    destination: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str | None = None


class TripUpdate(BaseModel):
    title: str | None = None
    destination: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str | None = None
    status: str | None = None
    # 封面：本人 media key（服务端校验归属）；null=清除；省略=不改（ADR-20261012 图片篇 §4.3）
    cover: str | None = None


class TripOut(BaseModel):
    id: int
    title: str
    destination: str | None
    start_date: datetime | None
    end_date: datetime | None
    cover: str | None
    description: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TripListItem(TripOut):
    """列表专用：附带只读计数（由列表查询的标量子查询填充，无表结构变更）。"""

    day_count: int = 0
    place_count: int = 0
    # 已完成地点数（口径与整程进度一致，含待定地点；见 ADR-20261012 §5.3/I4）
    done_count: int = 0


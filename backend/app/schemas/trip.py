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


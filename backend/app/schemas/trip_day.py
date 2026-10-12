from pydantic import BaseModel
from datetime import date as date_type


class TripDayCreate(BaseModel):
    date: date_type
    title: str | None = None


class TripDayUpdate(BaseModel):
    date: date_type | None = None
    title: str | None = None


class TripDayOut(BaseModel):
    id: int
    trip_id: int
    date: date_type
    day_index: int
    title: str | None

    class Config:
        from_attributes = True


class DayDoneIn(BaseModel):
    """批量完成/取消完成一天的请求体（ADR-20261012 §5.3）。done 必填、不接受 null。"""

    done: bool


class DayDoneOut(BaseModel):
    """批量动作结果：changed = 实际发生状态迁移的地点行数（幂等时可 0）。"""

    day_id: int
    done: bool
    changed: int
from pydantic import BaseModel
from datetime import datetime


class PlaceCreate(BaseModel):
    name: str
    day_id: int | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    category: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    notes: str | None = None
    sort_order: int = 0


class PlaceUpdate(BaseModel):
    name: str | None = None
    day_id: int | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    category: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    notes: str | None = None
    sort_order: int | None = None
    # 完成状态（ADR-20261012）：省略=不改；显式 null 由端点拒绝（422），
    # 状态迁移与 done_at 维护见 app.models.place.apply_done_state
    done: bool | None = None
    # 照片：本人 media key（服务端校验归属）；null=清除；省略=不改（ADR-20261012 图片篇 §4.3）
    photo: str | None = None


class PlaceOut(BaseModel):
    id: int
    trip_id: int
    day_id: int | None
    name: str
    address: str | None
    lat: float | None
    lng: float | None
    category: str | None
    start_time: datetime | None
    end_time: datetime | None
    notes: str | None
    sort_order: int
    done: bool
    done_at: datetime | None
    photo: str | None

    class Config:
        from_attributes = True
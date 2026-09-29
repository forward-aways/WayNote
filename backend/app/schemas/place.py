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

    class Config:
        from_attributes = True
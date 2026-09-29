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
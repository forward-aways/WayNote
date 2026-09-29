from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.user import User
from app.models.trip import Trip
from app.models.trip_day import TripDay
from app.schemas.trip_day import TripDayCreate, TripDayUpdate, TripDayOut
from app.api.deps import get_current_user
from app.core.logging import get_logger

log = get_logger("api.days")

router = APIRouter(prefix="/trips/{trip_id}/days", tags=["trip-days"])


# 辅助函数：获取自己的行程
def _get_own_trip(trip_id: int, db: Session, user: User) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="行程不存在")
    return trip


# 获取行程列表
@router.get("", response_model=list[TripDayOut])
def list_days(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_own_trip(trip_id, db, current_user)
    result = db.execute(
        select(TripDay).where(TripDay.trip_id == trip_id).order_by(TripDay.day_index)
    )
    return result.scalars().all()


# 创建行程
@router.post("", response_model=TripDayOut, status_code=201)
def create_day(
    trip_id: int,
    data: TripDayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 获取自己的行程
    _get_own_trip(trip_id, db, current_user)

    # 获取最大 day_index
    max_index = db.execute(
        select(func.coalesce(func.max(TripDay.day_index), 0)).where(TripDay.trip_id == trip_id)
    ).scalar_one()

    # 创建行程
    day = TripDay(
        trip_id=trip_id,
        date=data.date,
        day_index=max_index + 1,
        title=data.title,
    )
    db.add(day)
    db.commit()
    db.refresh(day)
    log.info("添加日程 trip=%s day=%s date=%s", trip_id, day.id, day.date, extra={"event": "day.create"})
    return day


# 更新行程
@router.patch("/{day_id}", response_model=TripDayOut)
def update_day(
    trip_id: int,
    day_id: int,
    data: TripDayUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_own_trip(trip_id, db, current_user)
    day = db.get(TripDay, day_id)
    if not day or day.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Day 不存在")

    # 更新行程
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(day, key, value)

    db.commit()
    db.refresh(day)
    log.info("更新日程 trip=%s day=%s", trip_id, day_id, extra={"event": "day.update"})
    return day


# 删除行程
@router.delete("/{day_id}", status_code=204)
def delete_day(
    trip_id: int,
    day_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_own_trip(trip_id, db, current_user)
    day = db.get(TripDay, day_id)
    if not day or day.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Day 不存在")

    db.delete(day)
    db.commit()
    log.info("删除日程 trip=%s day=%s", trip_id, day_id, extra={"event": "day.delete"})
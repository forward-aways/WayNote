from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripUpdate, TripOut
from app.api.deps import get_current_user


# 创建一个 APIRouter 实例
router = APIRouter(prefix="/trips", tags=["trips"])


# 获取当前用户的所有行程
@router.get("", response_model=list[TripOut])
def list_trips(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 查询当前用户的所有行程，并按创建时间降序排列
    result = db.execute(
        select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.created_at.desc())
    )
    return result.scalars().all()


# 创建一个行程
@router.post("", response_model=TripOut, status_code=201)
def create_trip(
        data: TripCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 创建一个行程, user_id=current_user.id表示当前用户创建的行程, **data.model_dump()表示将data的字段和值赋给trip
    trip = Trip(user_id=current_user.id, **data.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="行程不存在")
    return trip


# 更新一个行程
@router.patch("/{trip_id}", response_model=TripOut)
def update_trip(
        trip_id: int,
        data: TripUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="行程不存在")

    # 更新行程信息, model_dump(exclude_unset=True)表示只更新非空字段
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(trip, key, value)

    db.commit()
    db.refresh(trip)
    return trip


# 删除一个行程
@router.delete("/{trip_id}", status_code=204)
def delete_trip(
        trip_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="行程不存在")

    # 删除行程
    db.delete(trip)
    db.commit()
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.db.session import get_db
from app.models.user import User
from app.models.trip import Trip
from app.models.trip_day import TripDay
from app.models.place import Place
from app.schemas.trip import TripCreate, TripUpdate, TripOut, TripListItem
from app.api.deps import get_current_user
from app.core import storage
from app.core.logging import get_logger


log = get_logger("api.trips")

# 创建一个 APIRouter 实例
router = APIRouter(prefix="/trips", tags=["trips"])


# 获取当前用户的所有行程（附带天数/地点数只读计数）
@router.get("", response_model=list[TripListItem])
def list_trips(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 标量子查询计数，避免 N+1 请求，也无需改表结构
    day_count = (
        select(func.count(TripDay.id))
        .where(TripDay.trip_id == Trip.id)
        .scalar_subquery()
    )
    place_count = (
        select(func.count(Place.id))
        .where(Place.trip_id == Trip.id)
        .scalar_subquery()
    )
    # 已完成地点数（口径与整程进度一致，含待定地点；见 ADR-20261012 §5.3/I4）
    done_count = (
        select(func.count(Place.id))
        .where(Place.trip_id == Trip.id, Place.done.is_(True))
        .scalar_subquery()
    )

    # 查询当前用户的行程，并按创建时间降序排列
    rows = db.execute(
        select(
            Trip,
            day_count.label("day_count"),
            place_count.label("place_count"),
            done_count.label("done_count"),
        )
        .where(Trip.user_id == current_user.id)
        .order_by(Trip.created_at.desc())
    ).all()

    items: list[TripListItem] = []
    for trip, day_total, place_total, done_total in rows:
        item = TripListItem.model_validate(trip)
        item.day_count = day_total
        item.place_count = place_total
        item.done_count = done_total
        items.append(item)
    return items


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
    log.info("创建行程 id=%s title=%s", trip.id, trip.title, extra={"event": "trip.create"})
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
    payload = data.model_dump(exclude_unset=True)
    old_cover = trip.cover

    # cover 引用：必须是本人的合法 media key（null=清除；见 ADR-20261012 图片篇 §4.3/§4.5）
    if "cover" in payload and payload["cover"] is not None:
        try:
            storage.validate_key(payload["cover"], current_user.id)
        except storage.MediaKeyInvalid:
            raise HTTPException(status_code=400, detail="封面引用无效") from None

    for key, value in payload.items():
        setattr(trip, key, value)

    db.commit()
    db.refresh(trip)

    # 先提交、后删文件：提交失败绝不能先删；清理失败只留孤儿，不影响正确性
    if old_cover and old_cover != trip.cover:
        storage.delete_image(old_cover)

    log.info(
        "更新行程 id=%s fields=%s",
        trip.id,
        ",".join(payload.keys()) or "-",
        extra={"event": "trip.update"},
    )
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

    # 媒体 keys 在提交前收集（级联删除后对象不可用；见 ADR-20261012 图片篇 §4.5）
    cover = trip.cover
    photos = (
        db.execute(
            select(Place.photo).where(Place.trip_id == trip_id, Place.photo.is_not(None))
        )
        .scalars()
        .all()
    )

    # 删除行程（days/places 由数据库级联清理）
    db.delete(trip)
    db.commit()

    for key in ([cover] if cover else []) + list(photos):
        storage.delete_image(key)
    log.info("删除行程 id=%s", trip_id, extra={"event": "trip.delete"})
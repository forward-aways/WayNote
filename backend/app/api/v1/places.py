from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.trip import Trip
from app.models.trip_day import TripDay
from app.models.place import Place, apply_done_state
from app.schemas.place import PlaceCreate, PlaceUpdate, PlaceOut
from app.api.deps import get_current_user
from app.core import storage
from app.core.logging import get_logger


log = get_logger("api.places")

router = APIRouter(prefix="/trips/{trip_id}/places", tags=["places"])


def _get_own_trip(trip_id: int, db: Session, user: User) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        raise HTTPException(status_code=404, detail="行程不存在")
    return trip


# 列出行程中的所有地点
@router.get("", response_model=list[PlaceOut])
def list_places(
    trip_id: int,
    day_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_own_trip(trip_id, db, current_user)
    stmt = select(Place).where(Place.trip_id == trip_id)
    if day_id is not None:
        stmt = stmt.where(Place.day_id == day_id)

    # 按天数、排序顺序和地点ID排序
    stmt = stmt.order_by(Place.day_id, Place.sort_order, Place.id)
    return db.execute(stmt).scalars().all()


# 创建一个新的地点
@router.post("", response_model=PlaceOut, status_code=201)
def create_place(
    trip_id: int,
    data: PlaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_own_trip(trip_id, db, current_user)

    if data.day_id is not None:
        day = db.get(TripDay, data.day_id)
        if not day or day.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="day_id 不属于该行程")
    # 创建地点
    place = Place(trip_id=trip_id, **data.model_dump())
    db.add(place)
    db.commit()
    db.refresh(place)
    log.info("添加地点 trip=%s place=%s name=%s", trip_id, place.id, place.name, extra={"event": "place.create"})
    return place


# 更新地点
@router.patch("/{place_id}", response_model=PlaceOut)
def update_place(
    trip_id: int,
    place_id: int,
    data: PlaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_own_trip(trip_id, db, current_user)
    place = db.get(Place, place_id)
    if not place or place.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="地点不存在")

    payload = data.model_dump(exclude_unset=True)
    # fields 在状态位弹出前取：日志要覆盖 done 这类"不直接 setattr"的字段
    fields = ",".join(payload.keys()) or "-"
    old_photo = place.photo

    if "day_id" in payload and payload["day_id"] is not None:
        day = db.get(TripDay, payload["day_id"])
        if not day or day.trip_id != trip_id:
            raise HTTPException(status_code=400, detail="day_id 不属于该行程")

    # photo 引用：必须是本人的合法 media key（null=清除；见 ADR-20261012 图片篇 §4.3/§4.5）
    if "photo" in payload and payload["photo"] is not None:
        try:
            storage.validate_key(payload["photo"], current_user.id)
        except storage.MediaKeyInvalid:
            raise HTTPException(status_code=400, detail="照片引用无效") from None

    # done 是布尔状态位：显式 null 无意义（列 NOT NULL），直接 422 拒绝；
    # 状态迁移走 apply_done_state（不变量 I1 的唯一维护点，见 ADR-20261012 §5.3）
    if "done" in payload:
        raw_done = payload.pop("done")
        if raw_done is None:
            raise HTTPException(status_code=422, detail="done 不能为 null")
        apply_done_state(place, raw_done)

    for key, value in payload.items():
        setattr(place, key, value)

    db.commit()
    db.refresh(place)

    # 先提交、后删文件：提交失败绝不能先删；清理失败只留孤儿，不影响正确性
    if old_photo and old_photo != place.photo:
        storage.delete_image(old_photo)

    log.info(
        "更新地点 trip=%s place=%s fields=%s",
        trip_id,
        place.id,
        fields,
        extra={"event": "place.update"},
    )
    return place


# 删除地点
@router.delete("/{place_id}", status_code=204)
def delete_place(
    trip_id: int,
    place_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_own_trip(trip_id, db, current_user)
    place = db.get(Place, place_id)
    if not place or place.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="地点不存在")

    place_photo = place.photo  # 提交前取（删除后对象不可用）
    db.delete(place)
    db.commit()
    # 媒体清理（photo 在提交前取；见 ADR-20261012 图片篇 §4.5）
    if place_photo:
        storage.delete_image(place_photo)
    log.info("删除地点 trip=%s place=%s", trip_id, place_id, extra={"event": "place.delete"})
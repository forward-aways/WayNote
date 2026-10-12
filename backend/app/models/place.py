from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base

if TYPE_CHECKING:
    from app.models.trip import Trip
    from app.models.trip_day import TripDay


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    day_id: Mapped[int | None] = mapped_column(
        ForeignKey("trip_days.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 照片：媒体 key（相对标识，形状/归属校验见 core/storage.py；NULL=无照片）
    # 只存 key 不存 URL —— 内容与位置分离，换存储/域名不影响存量引用（ADR-20261012 图片篇 §4.2）
    photo: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 完成状态（ADR-20261012）：天/整程进度全部由它派生，是唯一事实来源。
    # 不变量 I1：done_at IS NULL ⟺ done = false —— 由 apply_done_state 唯一维护，
    # DB CHECK ck_places_done_at_consistent 兜底拒写非法态（防复发机制 1）。
    done: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="places")
    day: Mapped["TripDay | None"] = relationship(back_populates="places")


def apply_done_state(place: "Place", done: bool) -> None:
    """完成状态的唯一迁移入口（不变量 I1 的唯一维护点，见 ADR-20261012 §5.2）。

    幂等（I6）：目标态与当前态一致时不重写 done_at，完成时间不被无意义刷新。
    """
    if place.done == done:
        return
    place.done = done
    place.done_at = datetime.now() if done else None

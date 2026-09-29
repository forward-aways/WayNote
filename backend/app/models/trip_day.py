from datetime import date as date_type
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base

if TYPE_CHECKING:
    from app.models.place import Place
    from app.models.trip import Trip


class TripDay(Base):
    __tablename__ = "trip_days"
    __table_args__ = (
        UniqueConstraint("trip_id", "day_index", name="uq_trip_day_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    date: Mapped[date_type] = mapped_column(Date)
    day_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="days")

    # 反例（禁止照搬 Trip 的级联策略）：places.day_id 可空且 DB ondelete=SET NULL，
    # 业务语义是"删除天数后地点保留、归属置空"，因此不配 delete 级联，由 ORM 置 NULL。
    # 详见 .deepcode/ADR-20260929-Waynote-cascade-and-secrets.md
    places: Mapped[list["Place"]] = relationship(back_populates="day")

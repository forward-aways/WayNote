from datetime import date

from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import Place, Trip, TripDay, User


def make_user(session: Session, email: str) -> User:
    user = User(email=email, password_hash="x")
    session.add(user)
    session.flush()
    return user


def make_trip(session: Session, user: User, title: str) -> Trip:
    trip = Trip(user_id=user.id, title=title)
    session.add(trip)
    session.flush()
    return trip


def make_day(session: Session, trip: Trip, day_index: int, day_date: date) -> TripDay:
    day = TripDay(trip_id=trip.id, day_index=day_index, date=day_date)
    session.add(day)
    session.flush()
    return day


def make_place(session: Session, trip: Trip, name: str, day: TripDay | None = None) -> Place:
    place = Place(trip_id=trip.id, day_id=day.id if day is not None else None, name=name)
    session.add(place)
    session.flush()
    return place


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def count_rows(connection: Connection, table: str, where: str = "TRUE", **params: object) -> int:
    """原生 SQL 计数：绕过 ORM identity map，断言数据库真实状态。"""
    sql = text(f"SELECT count(*) FROM {table} WHERE {where}")
    return connection.execute(sql, params).scalar_one()

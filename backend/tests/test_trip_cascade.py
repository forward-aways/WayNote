"""行程/天/地点删除级联回归测试。

核心不变量（见 .deepcode/ADR-20260929-Waynote-cascade-and-secrets.md）：
1. 子 FK NOT NULL + DB ondelete=CASCADE  → ORM delete-orphan + passive_deletes，删除父对象由数据库级联。
2. 子 FK 可空 + DB ondelete=SET NULL     → 不得配置 delete 级联，删除天后地点保留且 day_id 置空。
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from helpers import auth_headers, count_rows, make_day, make_place, make_trip, make_user


def test_delete_trip_with_children_cascades(
    client: TestClient, session: Session, connection: Connection
) -> None:
    """T1 回归：修复前 db.delete(trip) 会发 UPDATE trip_days SET trip_id=NULL 并抛 IntegrityError(500)。"""
    user = make_user(session, "t1@example.com")
    trip = make_trip(session, user, "T1 带子数据")
    day = make_day(session, trip, 1, date(2026, 10, 1))
    make_place(session, trip, "T1 地点", day)
    trip_id = trip.id
    headers = auth_headers(user)

    resp = client.delete(f"/api/v1/trips/{trip_id}", headers=headers)

    assert resp.status_code == 204, resp.text
    assert count_rows(connection, "trips", "id = :trip_id", trip_id=trip_id) == 0
    assert count_rows(connection, "trip_days", "trip_id = :trip_id", trip_id=trip_id) == 0
    assert count_rows(connection, "places", "trip_id = :trip_id", trip_id=trip_id) == 0


def test_delete_empty_trip_keeps_other_trips(
    client: TestClient, session: Session, connection: Connection
) -> None:
    """T2 边界：空行程删除正常，且不影响同用户其他行程。"""
    user = make_user(session, "t2@example.com")
    empty = make_trip(session, user, "T2 空行程")
    other = make_trip(session, user, "T2 其他行程")
    empty_id, other_id = empty.id, other.id

    resp = client.delete(f"/api/v1/trips/{empty_id}", headers=auth_headers(user))

    assert resp.status_code == 204, resp.text
    assert count_rows(connection, "trips", "id = :trip_id", trip_id=empty_id) == 0
    assert count_rows(connection, "trips", "id = :trip_id", trip_id=other_id) == 1


def test_delete_day_keeps_place_with_null_day_id(
    client: TestClient, session: Session, connection: Connection
) -> None:
    """T3 反例守卫：places.day_id 是 SET NULL 语义，禁止套用 delete-orphan 误删地点。"""
    user = make_user(session, "t3@example.com")
    trip = make_trip(session, user, "T3")
    day = make_day(session, trip, 1, date(2026, 10, 2))
    place = make_place(session, trip, "T3 保留地点", day)
    trip_id, day_id, place_id = trip.id, day.id, place.id

    resp = client.delete(f"/api/v1/trips/{trip_id}/days/{day_id}", headers=auth_headers(user))

    assert resp.status_code == 204, resp.text
    assert count_rows(connection, "trip_days", "id = :day_id", day_id=day_id) == 0
    assert count_rows(connection, "places", "id = :place_id", place_id=place_id) == 1
    day_id_value = connection.execute(
        text("SELECT day_id FROM places WHERE id = :place_id"), {"place_id": place_id}
    ).scalar_one()
    assert day_id_value is None


def test_delete_trip_does_not_affect_other_users_data(
    client: TestClient, session: Session, connection: Connection
) -> None:
    """T4 泛化：级联范围严格限定在被删除行程，其他用户数据不变。"""
    user_a = make_user(session, "t4-a@example.com")
    user_b = make_user(session, "t4-b@example.com")
    trip_a = make_trip(session, user_a, "T4-A")
    day_a = make_day(session, trip_a, 1, date(2026, 10, 3))
    make_place(session, trip_a, "T4-A 地点", day_a)
    trip_b = make_trip(session, user_b, "T4-B")
    day_b = make_day(session, trip_b, 1, date(2026, 10, 3))
    make_place(session, trip_b, "T4-B 地点", day_b)
    trip_a_id, trip_b_id = trip_a.id, trip_b.id

    resp = client.delete(f"/api/v1/trips/{trip_a_id}", headers=auth_headers(user_a))

    assert resp.status_code == 204, resp.text
    assert count_rows(connection, "trips", "id = :trip_id", trip_id=trip_a_id) == 0
    assert count_rows(connection, "trip_days", "trip_id = :trip_id", trip_id=trip_a_id) == 0
    assert count_rows(connection, "places", "trip_id = :trip_id", trip_id=trip_a_id) == 0
    assert count_rows(connection, "trips", "id = :trip_id", trip_id=trip_b_id) == 1
    assert count_rows(connection, "trip_days", "trip_id = :trip_id", trip_id=trip_b_id) == 1
    assert count_rows(connection, "places", "trip_id = :trip_id", trip_id=trip_b_id) == 1


def test_cannot_delete_other_users_trip(
    client: TestClient, session: Session, connection: Connection
) -> None:
    """T5 安全：越权删除返回 404 且数据完好。"""
    owner = make_user(session, "t5-owner@example.com")
    attacker = make_user(session, "t5-attacker@example.com")
    trip = make_trip(session, owner, "T5")
    day = make_day(session, trip, 1, date(2026, 10, 4))
    make_place(session, trip, "T5 地点", day)
    trip_id = trip.id

    resp = client.delete(f"/api/v1/trips/{trip_id}", headers=auth_headers(attacker))

    assert resp.status_code == 404
    assert count_rows(connection, "trips", "id = :trip_id", trip_id=trip_id) == 1
    assert count_rows(connection, "trip_days", "trip_id = :trip_id", trip_id=trip_id) == 1
    assert count_rows(connection, "places", "trip_id = :trip_id", trip_id=trip_id) == 1


def test_delete_trip_cascades_multiple_days_places_and_no_orphans(
    client: TestClient, session: Session, connection: Connection
) -> None:
    """T6 泛化：3 天 5 地点（含未分配地点）全部级联清理，且不产生孤儿行。"""
    user = make_user(session, "t6@example.com")
    trip = make_trip(session, user, "T6")
    days = [make_day(session, trip, i, date(2026, 10, i)) for i in (5, 6, 7)]
    make_place(session, trip, "T6-1", days[0])
    make_place(session, trip, "T6-2", days[0])
    make_place(session, trip, "T6-3", days[1])
    make_place(session, trip, "T6-4", days[1])
    make_place(session, trip, "T6-5 未分配")  # day_id IS NULL 也要被行程级联清理
    trip_id, user_id = trip.id, user.id

    resp = client.delete(f"/api/v1/trips/{trip_id}", headers=auth_headers(user))

    assert resp.status_code == 204, resp.text
    assert count_rows(connection, "trip_days", "trip_id = :trip_id", trip_id=trip_id) == 0
    assert count_rows(connection, "places", "trip_id = :trip_id", trip_id=trip_id) == 0
    # 孤儿行检查：places/trip_days 的 trip_id 必须都能在 trips 中找到
    assert (
        count_rows(
            connection, "places p LEFT JOIN trips t ON p.trip_id = t.id", "t.id IS NULL"
        )
        == 0
    )
    assert (
        count_rows(
            connection, "trip_days d LEFT JOIN trips t ON d.trip_id = t.id", "t.id IS NULL"
        )
        == 0
    )
    # 级联不得波及 users 表
    assert count_rows(connection, "users", "id = :user_id", user_id=user_id) == 1

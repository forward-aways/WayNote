"""地点完成状态（done/done_at）与进度计数回归测试。

设计见 .deepcode/ADR-20261012-Waynote-place-completion.md：
- 不变量 I1：done_at IS NULL ⟺ done = false（唯一迁移入口 apply_done_state + DB CHECK 兜底）
- I4：列表 done_count 与整程进度同口径（含待定地点）
- I6：幂等——done 未变化时不重写 done_at
- 批量接口：单请求、原子、幂等（changed 语义）
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.place import apply_done_state
from helpers import auth_headers, make_day, make_place, make_trip, make_user


def _places_url(trip_id: int) -> str:
    return f"/api/v1/trips/{trip_id}/places"


def _place_url(trip_id: int, place_id: int) -> str:
    return f"/api/v1/trips/{trip_id}/places/{place_id}"


def _days_done_url(trip_id: int, day_id: int) -> str:
    return f"/api/v1/trips/{trip_id}/days/{day_id}/done"


def test_patch_done_sets_done_at_and_clears_on_undo(
    client: TestClient, session: Session
) -> None:
    """T1/T3：勾选置位 done_at；取消勾选清空；重新 GET 验证持久化。"""
    user = make_user(session, "done-basic@example.com")
    trip = make_trip(session, user, "完成-基本")
    place = make_place(session, trip, "清水寺")

    resp = client.patch(
        _place_url(trip.id, place.id), json={"done": True}, headers=auth_headers(user)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["done"] is True
    assert body["done_at"] is not None

    got = client.get(_places_url(trip.id), headers=auth_headers(user)).json()
    persisted = next(p for p in got if p["id"] == place.id)
    assert persisted["done"] is True and persisted["done_at"] is not None

    undo = client.patch(
        _place_url(trip.id, place.id), json={"done": False}, headers=auth_headers(user)
    )
    assert undo.status_code == 200
    assert undo.json()["done"] is False
    assert undo.json()["done_at"] is None


def test_patch_done_is_idempotent_and_keeps_done_at(
    client: TestClient, session: Session
) -> None:
    """T2/I6：重复勾选不重写完成时间。"""
    user = make_user(session, "done-idem@example.com")
    trip = make_trip(session, user, "完成-幂等")
    place = make_place(session, trip, "金阁寺")

    first = client.patch(
        _place_url(trip.id, place.id), json={"done": True}, headers=auth_headers(user)
    ).json()
    second = client.patch(
        _place_url(trip.id, place.id), json={"done": True}, headers=auth_headers(user)
    ).json()
    assert second["done"] is True
    assert second["done_at"] == first["done_at"]


def test_patch_done_null_rejected(client: TestClient, session: Session) -> None:
    """T3b：显式 null 被拒（422），状态不变。"""
    user = make_user(session, "done-null@example.com")
    trip = make_trip(session, user, "完成-空值")
    place = make_place(session, trip, "银阁寺")

    resp = client.patch(
        _place_url(trip.id, place.id), json={"done": None}, headers=auth_headers(user)
    )
    assert resp.status_code == 422, resp.text

    got = client.get(_places_url(trip.id), headers=auth_headers(user)).json()
    assert next(p for p in got if p["id"] == place.id)["done"] is False


def test_list_done_count_matches_progress_scope(
    client: TestClient, session: Session
) -> None:
    """T4/I4：done_count 只计已勾（含待定地点）；他人行程不受影响。"""
    user = make_user(session, "done-counts@example.com")
    trip = make_trip(session, user, "完成-计数")
    day = make_day(session, trip, 1, date(2026, 10, 1))
    done_assigned = make_place(session, trip, "已勾-有日程", day)
    make_place(session, trip, "未勾-有日程", day)
    done_pending = make_place(session, trip, "已勾-待定")  # day_id 为空也计入
    trip_id = trip.id

    apply_done_state(done_assigned, True)
    apply_done_state(done_pending, True)
    session.flush()

    other = make_user(session, "done-counts-other@example.com")
    make_trip(session, other, "他人行程-无完成")
    other_ids = {t["id"] for t in client.get("/api/v1/trips", headers=auth_headers(other)).json()}

    items = {
        item["id"]: item
        for item in client.get("/api/v1/trips", headers=auth_headers(user)).json()
    }
    item = items[trip_id]
    assert item["place_count"] == 3
    assert item["done_count"] == 2
    assert item["done_count"] <= item["place_count"]

    # 他人列表里的行程 done_count 全为 0，且看不到本用户行程
    other_items = client.get("/api/v1/trips", headers=auth_headers(other)).json()
    assert all(t["done_count"] == 0 for t in other_items)
    assert trip_id not in other_ids

    # 详情契约保持不变：仍不携带任何计数字段
    detail = client.get(f"/api/v1/trips/{trip_id}", headers=auth_headers(user))
    assert detail.status_code == 200
    assert "done_count" not in detail.json()


def test_day_bulk_done_atomic_and_idempotent(
    client: TestClient, session: Session
) -> None:
    """T5/T9：批量完成只迁移未完成行；幂等 changed=0；反向批量清空 done_at。"""
    user = make_user(session, "done-bulk@example.com")
    trip = make_trip(session, user, "完成-批量")
    day_1 = make_day(session, trip, 1, date(2026, 10, 1))
    day_2 = make_day(session, trip, 2, date(2026, 10, 2))
    already = make_place(session, trip, "已勾", day_1)
    make_place(session, trip, "未勾A", day_1)
    make_place(session, trip, "未勾B", day_1)
    day_2_place = make_place(session, trip, "另一天", day_2)
    trip_id, day_1_id, day_2_id = trip.id, day_1.id, day_2.id

    apply_done_state(already, True)
    session.flush()

    resp = client.patch(
        _days_done_url(trip_id, day_1_id),
        json={"done": True},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"day_id": day_1_id, "done": True, "changed": 2}

    rows = client.get(_places_url(trip_id), headers=auth_headers(user)).json()
    day_1_rows = [p for p in rows if p["day_id"] == day_1_id]
    assert all(p["done"] and p["done_at"] is not None for p in day_1_rows)
    other_row = next(p for p in rows if p["id"] == day_2_place.id)
    assert other_row["done"] is False and other_row["done_at"] is None

    again = client.patch(
        _days_done_url(trip_id, day_1_id),
        json={"done": True},
        headers=auth_headers(user),
    )
    assert again.json()["changed"] == 0

    cleared = client.patch(
        _days_done_url(trip_id, day_2_id),
        json={"done": False},
        headers=auth_headers(user),
    )
    assert cleared.json()["changed"] == 0  # day_2 本来就未完成

    reverse = client.patch(
        _days_done_url(trip_id, day_1_id),
        json={"done": False},
        headers=auth_headers(user),
    )
    assert reverse.json()["changed"] == 3
    rows_after = client.get(_places_url(trip_id), headers=auth_headers(user)).json()
    day_1_after = [p for p in rows_after if p["day_id"] == day_1_id]
    assert all(not p["done"] and p["done_at"] is None for p in day_1_after)


def test_day_bulk_ownership_404(client: TestClient, session: Session) -> None:
    """T8：他人行程的批量接口返回 404。"""
    owner = make_user(session, "done-owner@example.com")
    trip = make_trip(session, owner, "完成-归属")
    day = make_day(session, trip, 1, date(2026, 10, 1))
    make_place(session, trip, "地点", day)

    intruder = make_user(session, "done-intruder@example.com")
    resp = client.patch(
        _days_done_url(trip.id, day.id),
        json={"done": True},
        headers=auth_headers(intruder),
    )
    assert resp.status_code == 404


def test_db_check_rejects_inconsistent_done(session: Session) -> None:
    """T6/I1 反例：裸 SQL 写 done=true 且 done_at=NULL（或反向）必须被 DB 拒绝。"""
    user = make_user(session, "done-check@example.com")
    trip = make_trip(session, user, "完成-CHECK")
    trip_id = trip.id

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(
                text(
                    "INSERT INTO places (trip_id, name, done, done_at) "
                    "VALUES (:trip_id, '非法-有勾无时间', true, NULL)"
                ),
                {"trip_id": trip_id},
            )

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(
                text(
                    "INSERT INTO places (trip_id, name, done, done_at) "
                    "VALUES (:trip_id, '非法-无勾有时间', false, now())"
                ),
                {"trip_id": trip_id},
            )

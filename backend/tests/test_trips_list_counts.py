"""行程列表 day_count / place_count 只读计数字段回归测试。"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from helpers import auth_headers, make_day, make_place, make_trip, make_user


def test_list_trips_returns_day_and_place_counts(
    client: TestClient, session: Session
) -> None:
    user = make_user(session, "counts@example.com")
    trip_a = make_trip(session, user, "计数-有子数据")
    trip_b = make_trip(session, user, "计数-空行程")
    trip_a_id, trip_b_id = trip_a.id, trip_b.id

    day_1 = make_day(session, trip_a, 1, date(2026, 10, 1))
    make_day(session, trip_a, 2, date(2026, 10, 2))
    make_place(session, trip_a, "地点1", day_1)
    make_place(session, trip_a, "地点2", day_1)
    make_place(session, trip_a, "待定地点")  # day_id 为空也计入地点数

    resp = client.get("/api/v1/trips", headers=auth_headers(user))
    assert resp.status_code == 200, resp.text

    items = {item["title"]: item for item in resp.json()}
    assert items["计数-有子数据"]["day_count"] == 2
    assert items["计数-有子数据"]["place_count"] == 3
    assert items["计数-空行程"]["day_count"] == 0
    assert items["计数-空行程"]["place_count"] == 0

    # 单条详情接口保持原响应契约：不携带计数字段，避免影响既有调用方
    detail = client.get(f"/api/v1/trips/{trip_a_id}", headers=auth_headers(user))
    assert detail.status_code == 200
    assert "day_count" not in detail.json()

    # 计数与数据归属一致：另一用户的列表看不到本用户行程
    other = make_user(session, "counts-other@example.com")
    other_items = client.get("/api/v1/trips", headers=auth_headers(other)).json()
    assert all(item["id"] not in {trip_a_id, trip_b_id} for item in other_items)

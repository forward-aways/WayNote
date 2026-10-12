"""图片上传 / 媒体存储回归测试（ADR-20261012-Waynote-image-upload）。

覆盖：上传管线（校验/规范化/EXIF 抹除/缩略图）、体积与频控边界、key 归属与目录穿越、
替换与清空的文件清理、删除实体的级联清理、未鉴权。媒体根目录指向 tmp_path，不落真实文件。
"""

import io
import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.api.v1.uploads import reset_upload_rate_limit_state
from app.core import storage
from app.core.config import settings
from app.core.images import ImageInvalid, normalize_image
from helpers import auth_headers, make_place, make_trip, make_user


@pytest.fixture(autouse=True)
def media_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """媒体根目录隔离到 tmp_path + 清空上传频控（保证用例间互不影响）。"""
    monkeypatch.setattr(settings, "media_root", tmp_path / "uploads")
    reset_upload_rate_limit_state()
    return settings.media_root


def make_jpeg(width: int = 1200, height: int = 800, *, exif: Image.Exif | None = None) -> bytes:
    image = Image.new("RGB", (width, height), (30, 140, 90))
    buffer = io.BytesIO()
    if exif is None:
        image.save(buffer, format="JPEG")
    else:
        image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def upload(client: TestClient, user, data: bytes, filename: str = "photo.jpg"):
    return client.post(
        "/api/v1/uploads/images",
        files={"file": (filename, data, "image/jpeg")},
        headers=auth_headers(user),
    )


def key_files(root: Path, key: str) -> tuple[Path, Path]:
    return root / key, root / storage.thumb_key(key)


# ===== T1 正常上传 =====


def test_upload_happy_path(client: TestClient, session: Session, media_env: Path) -> None:
    user = make_user(session, "upload-ok@example.com")
    resp = upload(client, user, make_jpeg())

    assert resp.status_code == 201, resp.text
    body = resp.json()
    key = body["key"]
    assert key.startswith(f"{user.id}/") and key.endswith(".jpg")
    main, thumb = key_files(media_env, key)
    assert main.exists() and thumb.exists()
    assert thumb.stat().st_size < main.stat().st_size
    assert body["width"] == 1200 and body["height"] == 800
    assert body["url"].endswith(key)


def test_upload_requires_auth(client: TestClient, session: Session) -> None:
    resp = client.post(
        "/api/v1/uploads/images",
        files={"file": ("photo.jpg", make_jpeg(), "image/jpeg")},
    )
    assert resp.status_code == 401


# ===== T2/T3 校验与边界 =====


def test_upload_rejects_fake_image(client: TestClient, session: Session, media_env: Path) -> None:
    user = make_user(session, "upload-fake@example.com")
    resp = upload(client, user, b"hello, not an image" * 10)

    assert resp.status_code == 400, resp.text
    if media_env.exists():
        assert not list(media_env.rglob("*.jpg"))


def test_upload_rejects_oversized(client: TestClient, session: Session) -> None:
    user = make_user(session, "upload-big@example.com")
    payload = b"x" * (settings.media_max_bytes + 1)
    resp = upload(client, user, payload)
    assert resp.status_code == 400
    assert "过大" in resp.json()["detail"]


def test_upload_rejects_tiny_and_bomb(client: TestClient, session: Session) -> None:
    user = make_user(session, "upload-edge@example.com")

    tiny = upload(client, user, make_jpeg(1, 1))
    assert tiny.status_code == 400, tiny.text

    # 伪装成 20000×20000 的 PNG 头：触发 Pillow 解压炸弹防线（open 阶段即拒绝）
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 20000, 20000, 8, 2, 0, 0, 0)
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    bomb = upload(client, user, signature + ihdr)
    assert bomb.status_code == 400, bomb.text


def test_upload_daily_quota(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = make_user(session, "upload-quota@example.com")
    monkeypatch.setattr(settings, "media_upload_per_day", 2)

    assert upload(client, user, make_jpeg()).status_code == 201
    assert upload(client, user, make_jpeg()).status_code == 201
    third = upload(client, user, make_jpeg())
    assert third.status_code == 429, third.text


# ===== T4 规范化：方向纠正 + EXIF 全丢 =====


def test_upload_normalizes_orientation_and_strips_exif(
    client: TestClient, session: Session, media_env: Path
) -> None:
    user = make_user(session, "upload-exif@example.com")

    exif = Image.Exif()
    exif[274] = 6  # Orientation: 旋转 90°，规范化后应变成 2000×3000 再缩到 2000 长边
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (39.0, 54.0, 0.0)  # Pillow 写 GPS 需 float/IFDRational（元组会在编码期报错）
    raw = make_jpeg(3000, 2000, exif=exif)
    with Image.open(io.BytesIO(raw)) as probe:
        assert probe.getexif().get_ifd(0x8825).get(1) == "N"  # 前置条件：输入确实带 GPS
    resp = upload(client, user, raw)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["height"] == 2000 and body["width"] < body["height"]

    main, _ = key_files(media_env, body["key"])
    with Image.open(main) as out:
        assert len(out.getexif()) == 0  # EXIF（含 GPS）已随重编码丢弃


# ===== T6 归属与目录穿越 =====


def test_cover_and_photo_reject_foreign_or_malformed_key(
    client: TestClient, session: Session
) -> None:
    owner = make_user(session, "media-owner@example.com")
    intruder = make_user(session, "media-intruder@example.com")
    trip = make_trip(session, owner, "媒体归属")
    place = make_place(session, trip, "地点")
    foreign_key = storage.build_key(intruder.id)

    for bad in (foreign_key, "../../etc/passwd", f"{owner.id}/2026/10/zz.jpg", "not-a-key"):
        resp = client.patch(
            f"/api/v1/trips/{trip.id}",
            json={"cover": bad},
            headers=auth_headers(owner),
        )
        assert resp.status_code == 400, f"cover={bad} -> {resp.text}"
        resp = client.patch(
            f"/api/v1/trips/{trip.id}/places/{place.id}",
            json={"photo": bad},
            headers=auth_headers(owner),
        )
        assert resp.status_code == 400, f"photo={bad} -> {resp.text}"

    detail = client.get(f"/api/v1/trips/{trip.id}", headers=auth_headers(owner)).json()
    assert detail["cover"] is None


# ===== T7 替换 / 清空清理 =====


def test_replacing_and_clearing_media_deletes_old_files(
    client: TestClient, session: Session, media_env: Path
) -> None:
    user = make_user(session, "media-swap@example.com")
    trip = make_trip(session, user, "媒体替换")
    first = upload(client, user, make_jpeg()).json()["key"]
    second = upload(client, user, make_jpeg()).json()["key"]
    url = f"/api/v1/trips/{trip.id}"

    assert client.patch(url, json={"cover": first}, headers=auth_headers(user)).status_code == 200
    main, thumb = key_files(media_env, first)
    assert main.exists() and thumb.exists()

    assert client.patch(url, json={"cover": second}, headers=auth_headers(user)).status_code == 200
    assert not main.exists() and not thumb.exists()
    assert key_files(media_env, second)[0].exists()

    assert client.patch(url, json={"cover": None}, headers=auth_headers(user)).status_code == 200
    assert not key_files(media_env, second)[0].exists()
    assert client.get(url, headers=auth_headers(user)).json()["cover"] is None


# ===== T8 删除实体联动清理 =====


def test_deleting_trip_and_place_cleans_media(
    client: TestClient, session: Session, media_env: Path
) -> None:
    user = make_user(session, "media-delete@example.com")
    trip = make_trip(session, user, "媒体删除")
    place = make_place(session, trip, "地点")
    cover = upload(client, user, make_jpeg()).json()["key"]
    photo = upload(client, user, make_jpeg()).json()["key"]

    client.patch(f"/api/v1/trips/{trip.id}", json={"cover": cover}, headers=auth_headers(user))
    client.patch(
        f"/api/v1/trips/{trip.id}/places/{place.id}",
        json={"photo": photo},
        headers=auth_headers(user),
    )
    assert key_files(media_env, cover)[0].exists()
    assert key_files(media_env, photo)[0].exists()

    resp = client.delete(f"/api/v1/trips/{trip.id}", headers=auth_headers(user))
    assert resp.status_code == 204
    assert not key_files(media_env, cover)[0].exists()
    assert not key_files(media_env, photo)[0].exists()

    # 单独删除地点：photo 一并清理
    trip2 = make_trip(session, user, "媒体删除-地点")
    place2 = make_place(session, trip2, "地点2")
    photo2 = upload(client, user, make_jpeg()).json()["key"]
    client.patch(
        f"/api/v1/trips/{trip2.id}/places/{place2.id}",
        json={"photo": photo2},
        headers=auth_headers(user),
    )
    assert client.delete(
        f"/api/v1/trips/{trip2.id}/places/{place2.id}", headers=auth_headers(user)
    ).status_code == 204
    assert not key_files(media_env, photo2)[0].exists()


# ===== T10 管线单测：透明/CMYK/动图 =====


def _decode(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def test_pipeline_flattens_transparency_and_handles_modes() -> None:
    # 透明 PNG：透明角落应合成为白底
    rgba = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    rgba.paste((220, 40, 40, 255), (50, 50, 150, 150))
    buffer = io.BytesIO()
    rgba.save(buffer, format="PNG")
    processed = normalize_image(buffer.getvalue())
    with _decode(processed.data) as out:
        assert out.mode == "RGB"
        assert out.getpixel((0, 0)) == (255, 255, 255)

    # CMYK JPEG：可解码并转 RGB
    cmyk = Image.new("CMYK", (300, 200), (0, 120, 120, 0))
    buffer = io.BytesIO()
    cmyk.save(buffer, format="JPEG")
    assert _decode(normalize_image(buffer.getvalue()).data).mode == "RGB"

    # 两帧 GIF：静帧化（只取首帧）且不抛错
    frame1 = Image.new("P", (200, 200), 1)
    frame2 = Image.new("P", (200, 200), 2)
    buffer = io.BytesIO()
    frame1.save(buffer, format="GIF", save_all=True, append_images=[frame2], duration=100, loop=0)
    processed_gif = normalize_image(buffer.getvalue())
    with _decode(processed_gif.data) as out:
        assert out.format == "JPEG"

    # 空载荷：明确拒绝
    with pytest.raises(ImageInvalid):
        normalize_image(b"")

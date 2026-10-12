"""媒体文件存储（本地文件夹实现；迁移缝见 .deepcode/ADR-20261012-Waynote-image-upload.md §4.1）。

契约即迁移缝：build_key / validate_key / save_image / delete_image / path_of / public_url。
换腾讯云 COS 时只替换本模块实现（外加搬运存量文件），数据库与业务代码零改动。

不变量：
- I1：media_root 之外不可读、不可写（key 正则 + path.resolve() 双重防护）
- I2：缩略图由主图 key 推导（{stem}.thumb.jpg），数据库只存主图 key
- I3：key 第一段 = 用户 id ⇒ 归属校验天然成立（PATCH 引用他人 key 会被 validate_key 拒绝）
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings

# key 形状：{用户id}/{年}/{月}/{32位小写hex}.jpg
# 两个入口两种严格度：
# - 对外引用（validate_key：cover/photo）只接受"主图"key
# - 内部落盘/清理（path_of）额外接受推导出的 ".thumb.jpg"（不变量 I2）
_ID_PART = r"\d{1,10}/\d{4}/\d{2}/[0-9a-f]{32}"
_MAIN_KEY_RE = re.compile(rf"{_ID_PART}\.jpg")
_ANY_KEY_RE = re.compile(rf"{_ID_PART}(\.thumb)?\.jpg")


class MediaKeyInvalid(ValueError):
    """key 非法或不属于当前用户（调用方转为 400）。"""


def build_key(user_id: int, now: datetime | None = None) -> str:
    stamp = now or datetime.now()
    return f"{user_id}/{stamp:%Y/%m}/{uuid.uuid4().hex}.jpg"


def validate_key(key: str, user_id: int) -> str:
    """校验格式与归属，返回原 key；不合法抛 MediaKeyInvalid。

    只接受主图 key（缩略图由 thumb_key 推导，不允许被直接引用）。
    """
    if not isinstance(key, str) or not _MAIN_KEY_RE.fullmatch(key):
        raise MediaKeyInvalid(key)
    if int(key.split("/", 1)[0]) != user_id:
        raise MediaKeyInvalid(key)
    return key


def thumb_key(key: str) -> str:
    """主图 key → 缩略图 key（约定推导，不入库；见不变量 I2）。"""
    return f"{key[: -len('.jpg')]}.thumb.jpg"


def media_root() -> Path:
    """当前配置的存储根目录（每次读 settings，测试可覆盖）。"""
    return Path(settings.media_root)


def path_of(key: str) -> Path:
    """key → 绝对路径；格式与归属前缀之外，再做 resolve 越界检查（不变量 I1）。

    接受主图与 .thumb.jpg（内部落盘/清理用；对外引用请走 validate_key）。
    """
    if not isinstance(key, str) or not _ANY_KEY_RE.fullmatch(key):
        raise MediaKeyInvalid(key)
    root = media_root().resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise MediaKeyInvalid(key)
    return path


def save_image(key: str, data: bytes, thumb: bytes) -> None:
    """原子写入主图与缩略图（先写 .tmp 再 os.replace，避免半截文件被读到）。"""
    for target, payload in ((path_of(key), data), (path_of(thumb_key(key)), thumb)):
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f"{target.name}.tmp")
        tmp.write_bytes(payload)
        os.replace(tmp, target)


def delete_image(key: str) -> None:
    """尽力删除主图与缩略图（不变量 I4：清理失败只留孤儿，不影响业务）。"""
    for target in (path_of(key), path_of(thumb_key(key))):
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass


def public_url(key: str) -> str:
    """对外 URL（迁移到 CDN/COS 时改这里或前端 utils/media.ts 的前缀）。"""
    return f"{settings.media_url_prefix.rstrip('/')}/{key}"

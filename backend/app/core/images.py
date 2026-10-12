"""图片规范化管线（唯一入口；.deepcode/ADR-20261012-Waynote-image-upload.md §4.4）。

- 校验：Pillow 完整解码 + verify（含解压炸弹上限），只接受"真图片"
- 规范化：纠正 EXIF 方向 → 等比缩至上限 → 透明/调色板合成为白底 RGB → JPEG
- 输出：主图 bytes + 缩略图 bytes + 输出尺寸（EXIF 全丢，含 GPS 隐私；见不变量 I4）
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

MAIN_QUALITY = 85
THUMB_QUALITY = 80
# 最小边长：拒绝占位图/追踪像素类垃圾上传（见 ADR-20261012 图片篇 T3 边界）
MIN_EDGE = 64


class ImageInvalid(ValueError):
    """无法解码或格式不受支持（调用方转为 400）。"""


@dataclass(frozen=True)
class Processed:
    data: bytes
    thumb: bytes
    width: int
    height: int


def _encode(image: Image.Image, max_edge: int, quality: int) -> bytes:
    """等比缩到 max_edge 内并编码 JPEG（progressive + optimize）。"""
    copy = image.copy()
    copy.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    copy.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    """统一成白底 RGB：透明图铺白底；调色板/灰度/CMYK 直接转换。"""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (255, 255, 255))
        canvas.paste(rgba, mask=rgba.split()[-1])
        return canvas
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def normalize_image(raw: bytes) -> Processed:
    """原始字节 → (主图 JPEG, 缩略图 JPEG, 宽, 高)。"""
    if not raw:
        raise ImageInvalid("empty payload")
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()  # 完整性校验；verify 之后对象不可继续使用，需重新打开
        image = Image.open(io.BytesIO(raw))
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ImageInvalid(str(exc)) from None

    if getattr(image, "is_animated", False):
        image.seek(0)  # 动图静帧化：只取首帧
    image = ImageOps.exif_transpose(image)  # 先纠正方向，再丢 EXIF
    if min(image.size) < MIN_EDGE:
        raise ImageInvalid("too small")
    image = _flatten_to_rgb(image)

    data = _encode(image, settings.media_max_edge, MAIN_QUALITY)
    thumb = _encode(image, settings.media_thumb_edge, THUMB_QUALITY)
    with Image.open(io.BytesIO(data)) as out:
        width, height = out.size
    return Processed(data=data, thumb=thumb, width=width, height=height)

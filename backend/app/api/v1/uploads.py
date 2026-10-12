"""图片上传（唯一入口；.deepcode/ADR-20261012-Waynote-image-upload.md §4.4）。

管线：频控 → 体积上限 → Pillow 校验/规范化（core/images.py）→ 原子落盘（core/storage.py）。
响应只回 key（相对标识）；前端用 utils/media.ts 拼 URL（内容与位置分离）。
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_current_user
from app.core import storage
from app.core.config import settings
from app.core.images import ImageInvalid, normalize_image
from app.core.logging import get_logger
from app.core.ratelimit import SlidingWindowLimiter
from app.models.user import User

log = get_logger("api.uploads")

router = APIRouter(prefix="/uploads", tags=["uploads"])

# 单进程内存滑动窗口（与验证码/登录同源实现；语义边界见 core/ratelimit.py 模块注释）
_UPLOAD_LIMITER = SlidingWindowLimiter()


def reset_upload_rate_limit_state() -> None:
    """测试用：清空上传频控计数（与 auth 的同类函数保持一致的测试接口）。"""
    _UPLOAD_LIMITER.reset()


@router.post("/images", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # 1) 频控先行：已超限的请求不做任何图片处理
    decision = _UPLOAD_LIMITER.hit(
        f"upload:user:{current_user.id}",
        limit=settings.media_upload_per_day,
        window_seconds=86400,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"今日上传次数已达上限，请 {decision.retry_after_seconds} 秒后再试",
        )

    # 2) 体积上限：多读 1 字节用于判定超限，避免把超大文件整个读进内存
    raw = await file.read(settings.media_max_bytes + 1)
    if len(raw) > settings.media_max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"图片过大（上限 {settings.media_max_bytes // (1024 * 1024)}MB）",
        )

    # 3) 校验 + 规范化（Pillow：唯一解码入口）
    try:
        processed = normalize_image(raw)
    except ImageInvalid:
        raise HTTPException(
            status_code=400, detail="图片已损坏或格式不受支持（请用 JPG/PNG/WebP）"
        ) from None

    # 4) 原子落盘（主图 + 缩略图）
    key = storage.build_key(current_user.id)
    storage.save_image(key, processed.data, processed.thumb)
    log.info(
        "上传图片 user=%s key=%s bytes=%s",
        current_user.id,
        key,
        len(processed.data),
        extra={"event": "media.upload"},
    )
    return {
        "key": key,
        "url": storage.public_url(key),
        "width": processed.width,
        "height": processed.height,
        "bytes": len(processed.data),
    }

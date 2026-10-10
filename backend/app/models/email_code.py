"""邮箱验证码记录（状态机见 .deepcode/ADR-20261009-Waynote-email-code-auth.md §6.2）。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class EmailCode(Base):
    __tablename__ = "email_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 归一化小写后的邮箱（与 users.email 的写入口径一致）
    email: Mapped[str] = mapped_column(String(255))
    # login | register | reset：用途隔离（不变量 I4）
    purpose: Mapped[str] = mapped_column(String(16))
    # bcrypt 哈希：明文码绝不落库（不变量 I3 的前置条件）
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # 已尝试次数：单调不减，错误尝试先落库（不变量 I2）
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    # 终态标记：一旦写入不可复用（不变量 I3）
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    request_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 校验路径固定按 (email, purpose) 取最新一行，索引与之同构
    __table_args__ = (Index("ix_email_codes_lookup", "email", "purpose", "created_at"),)

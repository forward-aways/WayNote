from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.trip import Trip


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # 可空：验证码登录的免密账号没有密码，直到用户主动设置
    # （见 .deepcode/ADR-20261009-Waynote-email-code-auth.md §6.1）
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 级联不变量：trips.user_id 为 NOT NULL 且 DB ondelete=CASCADE，
    # ORM 侧必须配 delete-orphan + passive_deletes，删除用户时由数据库级联清理行程。
    # 详见 .deepcode/ADR-20260929-Waynote-cascade-and-secrets.md
    trips: Mapped[list["Trip"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def has_password(self) -> bool:
        """免密账号（验证码登录自动建号）为 False；供 /auth/me 与前端决定「设置/修改密码」。"""
        return self.password_hash is not None

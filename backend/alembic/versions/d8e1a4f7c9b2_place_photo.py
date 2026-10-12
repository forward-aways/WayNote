"""places: 增加 photo 字段（图片上传：行程封面复用在 trips.cover）

Revision ID: d8e1a4f7c9b2
Revises: c4a7d92b6e15
Create Date: 2026-10-12 13:00:00.000000

设计见 .deepcode/ADR-20261012-Waynote-image-upload.md §4.3。
- 只存媒体 key（相对标识，如 "1/2026/10/<uuid>.jpg"），不存 URL/绝对路径；
  归属校验与清理见 app/core/storage.py 与 api/v1/places.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e1a4f7c9b2'
down_revision: Union[str, Sequence[str], None] = 'c4a7d92b6e15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('places', sa.Column('photo', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('places', 'photo')

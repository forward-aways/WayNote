"""places: 完成状态字段（done/done_at + 一致性 CHECK）

Revision ID: c4a7d92b6e15
Revises: 9d1f4c7b2a58
Create Date: 2026-10-12 12:00:00.000000

设计见 .deepcode/ADR-20261012-Waynote-place-completion.md §5.1。

- places.done：地点级完成状态（天/整程进度由它派生，单一事实来源）
- places.done_at：完成时间（仅服务端写入；不变量 I1：done_at IS NULL ⟺ done=false）
- CHECK ck_places_done_at_consistent：DB 层兜底拒写非法态（防复发机制 1）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a7d92b6e15'
down_revision: Union[str, Sequence[str], None] = '9d1f4c7b2a58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'places',
        sa.Column('done', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.add_column('places', sa.Column('done_at', sa.DateTime(), nullable=True))
    op.create_check_constraint(
        'ck_places_done_at_consistent',
        'places',
        '(NOT done AND done_at IS NULL) OR (done AND done_at IS NOT NULL)',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_places_done_at_consistent', 'places', type_='check')
    op.drop_column('places', 'done_at')
    op.drop_column('places', 'done')

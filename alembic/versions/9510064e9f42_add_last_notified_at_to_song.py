"""add_last_notified_at_to_song

Revision ID: 9510064e9f42
Revises: 56608622def2
Create Date: 2026-08-07 00:00:00.000000

用于新歌增量监控: 记录某首歌曲最后一次发送「新歌发布」通知的时间，
以便抑制对同一新歌的重复推送。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9510064e9f42'
down_revision: Union[str, Sequence[str], None] = '20b85a3c6d12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'songs' in tables:
        cols = [c['name'] for c in inspector.get_columns('songs')]
        if 'last_notified_at' not in cols:
            op.add_column('songs', sa.Column('last_notified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('songs', 'last_notified_at')

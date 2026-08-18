"""add_ignored_songs_table

Revision ID: c4d2e6f8a0b1
Revises: b7e8f3a9c2d4
Create Date: 2026-08-14 00:00:00.000000

新增 ignored_songs 表: 记录用户手动「忽略」的歌曲 (source, source_id)，
防止新歌监控在用户忽略后重新发现同一首歌 (死循环)。

忽略流程: 删文件 + 删 Song + 写本表墓碑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d2e6f8a0b1'
down_revision: Union[str, Sequence[str], None] = 'b7e8f3a9c2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'ignored_songs' not in tables:
        op.create_table(
            'ignored_songs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('artist_id', sa.Integer(),
                      sa.ForeignKey('artists.id', ondelete='SET NULL'),
                      nullable=True, index=True),
            sa.Column('source', sa.String(), nullable=False),
            sa.Column('source_id', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=True),
            sa.Column('ignored_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('source', 'source_id', name='uq_ignored_song_key'),
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'ignored_songs' in tables:
        op.drop_table('ignored_songs')

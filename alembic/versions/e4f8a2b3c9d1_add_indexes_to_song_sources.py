"""add_indexes_to_song_sources

Revision ID: e4f8a2b3c9d1
Revises: a3f9c2e1d4b5
Create Date: 2026-09-16 00:00:00.000000

为 song_sources 表添加查询性能索引:
- (source, source_id): 被 get_by_unique_key 等高频查询使用
- (source): 按平台过滤
- (source_id): 按来源 ID 查询
"""

from alembic import op
import sqlalchemy as sa

revision = 'e4f8a2b3c9d1'
down_revision = 'a3f9c2e1d4b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_song_sources_source', 'song_sources', ['source'])
    op.create_index('ix_song_sources_source_id', 'song_sources', ['source_id'])
    op.create_index('ix_song_sources_source_source_id', 'song_sources', ['source', 'source_id'])


def downgrade() -> None:
    op.drop_index('ix_song_sources_source_source_id', table_name='song_sources')
    op.drop_index('ix_song_sources_source_id', table_name='song_sources')
    op.drop_index('ix_song_sources_source', table_name='song_sources')

"""dedupe_song_sources_and_add_constraint

Revision ID: a3f9c2e1d4b5
Revises: 9510064e9f42
Create Date: 2026-08-13 00:00:00.000000

背景: 初始迁移建 song_sources 表时漏掉了 uq_song_source 唯一约束
(仅 ORM 模型上有 UniqueConstraint, alembic 建的表没有)，
导致应用层「先查后插」逻辑在无竞态防护时可写入重复记录
(实际发现 4 组重复: song 33/62/106/107)。

本迁移:
1. 删除重复记录, 每组 (song_id, source, source_id) 保留 id 最小的一条;
2. 用 batch 模式重建表并补建 uq_song_source 唯一约束 (SQLite 不支持
   ALTER TABLE ADD CONSTRAINT, 需整表重建)。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f9c2e1d4b5'
down_revision: Union[str, Sequence[str], None] = '9510064e9f42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'song_sources' not in tables:
        return

    # 1. 去重: 保留每组 (song_id, source, source_id) 中 id 最小的记录
    conn.execute(sa.text(
        """
        DELETE FROM song_sources
        WHERE id NOT IN (
            SELECT MIN(id) FROM song_sources
            GROUP BY song_id, source, source_id
        )
        """
    ))

    # 2. 补建唯一约束 (batch 模式, SQLite 重建表)
    #    先去重后重建, 避免约束创建失败
    with op.batch_alter_table('song_sources', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_song_source', ['song_id', 'source', 'source_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # 回退: 删除唯一约束 (batch 模式重建表), 数据保持去重后的状态
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'song_sources' not in tables:
        return
    with op.batch_alter_table('song_sources', schema=None) as batch_op:
        batch_op.drop_constraint('uq_song_source', type_='unique')

"""merge heads: ignored_songs + song_source_indexes

Revision ID: f1a2b3c4d5e6
Revises: c4d2e6f8a0b1, e4f8a2b3c9d1
Create Date: 2026-09-17 00:00:00.000000

合并两个分叉的迁移 head:
- c4d2e6f8a0b1 (add_ignored_songs_table)
- e4f8a2b3c9d1 (add_indexes_to_song_sources)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = ('c4d2e6f8a0b1', 'e4f8a2b3c9d1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge — no schema changes needed."""
    pass


def downgrade() -> None:
    """Cannot downgrade a merge revision."""
    pass

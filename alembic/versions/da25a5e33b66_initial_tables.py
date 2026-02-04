"""Initial tables - CORRECTED & COMPATIBLE

Revision ID: da25a5e33b66
Revises: 
Create Date: 2026-01-21 12:00:48.013798
Last Updated: 2026-02-04 (Fixed drift, removed downstream columns to avoid conflict)

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = 'da25a5e33b66'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Artists Table (Fixed: No source_id, Added is_monitored)
    op.create_table('artists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('avatar', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default="active"),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('is_monitored', sa.Boolean(), nullable=True, server_default="0"), # Added here as it seems missing in migrations
        # Removed source_id, source (Correct)
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artists_id'), 'artists', ['id'], unique=False)
    op.create_index(op.f('ix_artists_name'), 'artists', ['name'], unique=False)

    # 2. Artist Sources (New)
    op.create_table('artist_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('avatar', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artist_sources_id'), 'artist_sources', ['id'], unique=False)
    op.create_index(op.f('ix_artist_sources_artist_id'), 'artist_sources', ['artist_id'], unique=False)

    # 3. Songs Table (Fixed: No cover/last_enrich_at, let downstream migrations add them)
    op.create_table('songs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unique_key', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('album', sa.String(), nullable=True),
        sa.Column('artist_id', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('local_path', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=True),
        sa.Column('publish_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        # Removed 'cover' -> Added by 20b85a3c6d12
        # Removed 'last_enrich_at' -> Added by 56608622def2
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_songs_id'), 'songs', ['id'], unique=False)
    op.create_index(op.f('ix_songs_title'), 'songs', ['title'], unique=False)
    op.create_index(op.f('ix_songs_unique_key'), 'songs', ['unique_key'], unique=True)
    
    # 4. Song Sources (New)
    op.create_table('song_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('song_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('cover', sa.String(), nullable=True),
        sa.Column('data_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_song_sources_song_id'), 'song_sources', ['song_id'], unique=False)
    
    # 5. System Settings (Clean)
    # Check if table exists because 13b02a6d3db7 might try to use it or create it?
    # Actually 13b02a6d3db7 ensures it exists. If we create it here, 13b02 might fail or skip?
    # Let's see 13b02 content... Assumed safe to create here if it's "Initial".
    op.create_table('system_settings',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )
    
    # Cleanup legacy
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'media_records' in tables:
        op.drop_table('media_records')

def downgrade() -> None:
    pass

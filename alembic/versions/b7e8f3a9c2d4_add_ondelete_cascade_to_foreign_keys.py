"""add ondelete cascade to foreign keys

Revision ID: b7e8f3a9c2d4
Revises: a3f9c2e1d4b5
Create Date: 2026-08-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7e8f3a9c2d4'
down_revision: Union[str, Sequence[str], None] = 'a3f9c2e1d4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为外键添加 ON DELETE CASCADE, 配合 PRAGMA foreign_keys=ON 由数据库层级联删除。

    背景: 此前删除走 Core bulk delete 绕过 ORM 级联, 且 SQLite 默认不强制外键,
    导致 delete_song/delete_artist 残留孤儿行。修复后:
    - 删除歌手 -> 数据库级级联删除其 songs / artist_sources
    - 删除歌曲 -> 数据库级级联删除其 song_sources

    SQLite 无法 ALTER 修改外键, 无名 FK 约束也无法用 alembic batch 的
    drop_constraint 引用, 因此采用原生 DDL 重建表 (重命名旧表 -> 建新表 -> 拷贝数据)。
    迁移连接未启用 foreign_keys 强制, 拷贝旧数据时不校验, 可安全处理既有孤儿行。
    """
    # ---------- songs: artist_id -> artists.id (ON DELETE CASCADE) ----------
    op.execute("ALTER TABLE songs RENAME TO _songs_old")
    op.execute(
        """
        CREATE TABLE songs (
            id INTEGER NOT NULL,
            unique_key VARCHAR NOT NULL,
            title VARCHAR,
            album VARCHAR,
            artist_id INTEGER,
            duration INTEGER,
            local_path VARCHAR,
            status VARCHAR,
            is_favorite BOOLEAN,
            publish_time DATETIME,
            created_at DATETIME,
            metadata_json JSON,
            url VARCHAR,
            is_pushed BOOLEAN,
            push_time DATETIME,
            audio_quality INTEGER,
            last_enrich_at DATETIME,
            cover VARCHAR,
            last_notified_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(artist_id) REFERENCES artists (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        INSERT INTO songs (id, unique_key, title, album, artist_id, duration, local_path,
            status, is_favorite, publish_time, created_at, metadata_json, url, is_pushed,
            push_time, audio_quality, last_enrich_at, cover, last_notified_at)
        SELECT id, unique_key, title, album, artist_id, duration, local_path,
            status, is_favorite, publish_time, created_at, metadata_json, url, is_pushed,
            push_time, audio_quality, last_enrich_at, cover, last_notified_at
        FROM _songs_old
        """
    )
    op.execute("DROP TABLE _songs_old")
    op.execute("CREATE INDEX ix_songs_id ON songs (id)")
    op.execute("CREATE INDEX ix_songs_title ON songs (title)")
    op.execute("CREATE UNIQUE INDEX ix_songs_unique_key ON songs (unique_key)")

    # ---------- song_sources: song_id -> songs.id (ON DELETE CASCADE) ----------
    op.execute("ALTER TABLE song_sources RENAME TO _song_sources_old")
    op.execute(
        """
        CREATE TABLE song_sources (
            id INTEGER NOT NULL,
            song_id INTEGER NOT NULL,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            url VARCHAR,
            cover VARCHAR,
            duration INTEGER,
            data_json JSON,
            PRIMARY KEY (id),
            CONSTRAINT uq_song_source UNIQUE (song_id, source, source_id),
            FOREIGN KEY(song_id) REFERENCES songs (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        INSERT INTO song_sources (id, song_id, source, source_id, url, cover, duration, data_json)
        SELECT id, song_id, source, source_id, url, cover, duration, data_json
        FROM _song_sources_old
        """
    )
    op.execute("DROP TABLE _song_sources_old")
    op.execute("CREATE INDEX ix_song_sources_song_id ON song_sources (song_id)")

    # ---------- artist_sources: artist_id -> artists.id (ON DELETE CASCADE) ----------
    op.execute("ALTER TABLE artist_sources RENAME TO _artist_sources_old")
    op.execute(
        """
        CREATE TABLE artist_sources (
            id INTEGER NOT NULL,
            artist_id INTEGER NOT NULL,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            avatar VARCHAR,
            url VARCHAR,
            raw_data JSON,
            PRIMARY KEY (id),
            FOREIGN KEY(artist_id) REFERENCES artists (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        INSERT INTO artist_sources (id, artist_id, source, source_id, avatar, url, raw_data)
        SELECT id, artist_id, source, source_id, avatar, url, raw_data
        FROM _artist_sources_old
        """
    )
    op.execute("DROP TABLE _artist_sources_old")
    op.execute("CREATE INDEX ix_artist_sources_id ON artist_sources (id)")
    op.execute("CREATE INDEX ix_artist_sources_artist_id ON artist_sources (artist_id)")


def downgrade() -> None:
    """恢复为默认 (无 ON DELETE 行为) 的外键约束"""
    # ---------- songs ----------
    op.execute("ALTER TABLE songs RENAME TO _songs_old")
    op.execute(
        """
        CREATE TABLE songs (
            id INTEGER NOT NULL,
            unique_key VARCHAR NOT NULL,
            title VARCHAR,
            album VARCHAR,
            artist_id INTEGER,
            duration INTEGER,
            local_path VARCHAR,
            status VARCHAR,
            is_favorite BOOLEAN,
            publish_time DATETIME,
            created_at DATETIME,
            metadata_json JSON,
            url VARCHAR,
            is_pushed BOOLEAN,
            push_time DATETIME,
            audio_quality INTEGER,
            last_enrich_at DATETIME,
            cover VARCHAR,
            last_notified_at DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(artist_id) REFERENCES artists (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO songs (id, unique_key, title, album, artist_id, duration, local_path,
            status, is_favorite, publish_time, created_at, metadata_json, url, is_pushed,
            push_time, audio_quality, last_enrich_at, cover, last_notified_at)
        SELECT id, unique_key, title, album, artist_id, duration, local_path,
            status, is_favorite, publish_time, created_at, metadata_json, url, is_pushed,
            push_time, audio_quality, last_enrich_at, cover, last_notified_at
        FROM _songs_old
        """
    )
    op.execute("DROP TABLE _songs_old")
    op.execute("CREATE INDEX ix_songs_id ON songs (id)")
    op.execute("CREATE INDEX ix_songs_title ON songs (title)")
    op.execute("CREATE UNIQUE INDEX ix_songs_unique_key ON songs (unique_key)")

    # ---------- song_sources ----------
    op.execute("ALTER TABLE song_sources RENAME TO _song_sources_old")
    op.execute(
        """
        CREATE TABLE song_sources (
            id INTEGER NOT NULL,
            song_id INTEGER NOT NULL,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            url VARCHAR,
            cover VARCHAR,
            duration INTEGER,
            data_json JSON,
            PRIMARY KEY (id),
            CONSTRAINT uq_song_source UNIQUE (song_id, source, source_id),
            FOREIGN KEY(song_id) REFERENCES songs (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO song_sources (id, song_id, source, source_id, url, cover, duration, data_json)
        SELECT id, song_id, source, source_id, url, cover, duration, data_json
        FROM _song_sources_old
        """
    )
    op.execute("DROP TABLE _song_sources_old")
    op.execute("CREATE INDEX ix_song_sources_song_id ON song_sources (song_id)")

    # ---------- artist_sources ----------
    op.execute("ALTER TABLE artist_sources RENAME TO _artist_sources_old")
    op.execute(
        """
        CREATE TABLE artist_sources (
            id INTEGER NOT NULL,
            artist_id INTEGER NOT NULL,
            source VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            avatar VARCHAR,
            url VARCHAR,
            raw_data JSON,
            PRIMARY KEY (id),
            FOREIGN KEY(artist_id) REFERENCES artists (id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO artist_sources (id, artist_id, source, source_id, avatar, url, raw_data)
        SELECT id, artist_id, source, source_id, avatar, url, raw_data
        FROM _artist_sources_old
        """
    )
    op.execute("DROP TABLE _artist_sources_old")
    op.execute("CREATE INDEX ix_artist_sources_id ON artist_sources (id)")
    op.execute("CREATE INDEX ix_artist_sources_artist_id ON artist_sources (artist_id)")

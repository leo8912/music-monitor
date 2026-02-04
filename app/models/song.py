"""
Song模型 - 歌曲数据模型定义

此文件定义了Song数据模型，用于表示音乐监控系统中的歌曲实体。
采用核心-扩展模式:
1. Song: 聚合逻辑实体 (UI显示用, 优先QQ数据)
2. SongSource: 具体平台的音频元数据 (数据用)

Author: music-monitor development team
Updated: 2026-01-27
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class Song(Base):
    """
    核心歌曲实体 (Display Entity)
    逻辑主键 (Artist + Title + Album)
    """
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    unique_key = Column(String, unique=True, index=True, nullable=False) # UUID-based unique key
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    
    # Display Information (Prioritized)
    title = Column(String, index=True, nullable=False)
    album = Column(String)
    
    # 优先展示用的封面和时间 (QQ > Netease)
    cover = Column(String, nullable=True)
    publish_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Status
    is_favorite = Column(Boolean, default=False)
    status = Column(String, default="PENDING") # PENDING / DOWNLOADED / ERROR
    local_path = Column(String, nullable=True) # If downloaded locally
    last_enrich_at = Column(DateTime, nullable=True) # Last time enrichment was attempted
    
    # Relationships
    artist = relationship("Artist", back_populates="songs")
    sources = relationship("SongSource", back_populates="song", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Song(title={self.title})>"

    @property
    def localFiles(self):
        """
        Helper for API response: returns list of local file details
        """
        result = []
        if not self.sources:
            return result
        for s in self.sources:
            if s.source == 'local':
                 data = s.data_json or {}
                 result.append({
                     "id": s.id,
                     "source_id": s.source_id,
                     "path": s.url,
                     "quality": data.get('quality', 'PQ'),
                     "format": data.get('format', 'UNK')
                 })
        return result

    @property
    def availableSources(self):
        """
        Helper for API response: returns list of unique sources
        """
        if not self.sources:
            return [self.local_path] if self.local_path else []
        return list(set([s.source for s in self.sources]))

class SongSource(Base):
    """
    歌曲来源映射 (Implementation Entity)
    """
    __tablename__ = "song_sources"
    __table_args__ = (
        UniqueConstraint('song_id', 'source', 'source_id', name='uq_song_source'),
    )

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    
    source = Column(String, nullable=False)    # 'qqmusic', 'netease', 'local'
    source_id = Column(String, nullable=False) # mid / filename
    
    # Source Specific Meta
    cover = Column(String, nullable=True)
    duration = Column(Integer, default=0)
    url = Column(String, nullable=True)  # Playback URL if available
    
    # Flexible Data (Quality, Lyric, etc.)
    data_json = Column(JSON, nullable=True)
    
    song = relationship("Song", back_populates="sources")

    def __repr__(self):
        return f"<SongSource(source={self.source}, id={self.source_id})>"

"""
Artist模型 - 艺术家数据模型定义

此文件定义了Artist数据模型，用于表示音乐监控系统中的艺术家实体。
采用核心-扩展模式:
1. Artist: 聚合逻辑实体 (UI显示用)
2. ArtistSource: 具体平台的关联信息 (数据用)

Author: music-monitor development team
Updated: 2026-01-27
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class Artist(Base):
    """
    核心艺术家实体 (Display Entity)
    """
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    avatar = Column(String, nullable=True)     # Priority Avatar (e.g. QQ)
    status = Column(String, default="active")  # active/paused
    last_sync = Column(DateTime, default=datetime.now)
    is_monitored = Column(Boolean, default=False) 
    
    # Relationships
    sources = relationship("ArtistSource", back_populates="artist", cascade="all, delete-orphan")
    songs = relationship("Song", back_populates="artist", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Artist(name={self.name})>"

class ArtistSource(Base):
    """
    艺术家来源映射 (Implementation Entity)
    """
    __tablename__ = "artist_sources"

    id = Column(Integer, primary_key=True, index=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False, index=True)
    
    source = Column(String, nullable=False)    # e.g. 'qqmusic', 'netease'
    source_id = Column(String, nullable=False) # e.g. 'mid_123'
    avatar = Column(String, nullable=True)     # Source specific avatar
    url = Column(String, nullable=True)
    
    # 完整原始数据 (可选)
    raw_data = Column(JSON, nullable=True) # Full API Response
    
    artist = relationship("Artist", back_populates="sources")

    def __repr__(self):
        return f"<ArtistSource(source={self.source}, id={self.source_id})>"

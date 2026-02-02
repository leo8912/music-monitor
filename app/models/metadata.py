"""
数据库迁移脚本 - 添加元数据表
目的: 建立albums、lyrics、song_metadata_cache三个表,优化元数据管理
作者: GOOGLE
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Index
from datetime import datetime
from app.models.base import Base


class Album(Base):
    """
    专辑表 - 统一管理专辑信息
    避免在songs表中重复存储相同专辑的信息
    """
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    
    # 元数据
    cover_url = Column(String(500), nullable=True)      # 在线封面URL
    cover_path = Column(String(200), nullable=True)     # 本地封面文件路径 (covers/albums/xxx.jpg)
    release_date = Column(DateTime, nullable=True)      # 发行日期
    description = Column(Text, nullable=True)           # 专辑描述
    
    # 来源信息
    source = Column(String(20), nullable=True)          # "netease", "qqmusic", "local"
    source_album_id = Column(String(100), nullable=True)
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Album(name={self.name}, artist_id={self.artist_id})>"


class Lyric(Base):
    """
    歌词表 - 支持多语言歌词和全文搜索
    每首歌可以有多条歌词记录(原文/翻译)
    """
    __tablename__ = "lyrics"

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    
    # 歌词内容
    content = Column(Text, nullable=False)             # 歌词文本
    translated_content = Column(Text, nullable=True)   # 翻译歌词
    language = Column(String(10), default='zh')        # 语言代码: zh, en, ja, ko
    lyric_type = Column(String(20), default='original') # original, translation
    
    # 来源信息
    source = Column(String(20), nullable=True)         # "netease", "qqmusic", "manual"
    source_url = Column(String(500), nullable=True)
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Lyric(song_id={self.song_id}, language={self.language})>"


class SongMetadataCache(Base):
    """
    元数据缓存表 - 减少API调用
    缓存从网易云/QQ音乐API获取的元数据
    """
    __tablename__ = "song_metadata_cache"

    id = Column(Integer, primary_key=True, index=True)
    
    # 唯一标识
    search_key = Column(String(200), nullable=False, index=True)  # "{title}_{artist}"
    source = Column(String(20), nullable=False)                   # "netease", "qqmusic"
    
    # 缓存数据(JSON格式)
    metadata_json = Column(JSON, nullable=False)
    
    # 缓存管理
    hit_count = Column(Integer, default=0)            # 命中次数
    last_hit_at = Column(DateTime, nullable=True)     # 最后命中时间
    expires_at = Column(DateTime, nullable=False)     # 过期时间(创建时间+30天)
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.now)
    
    # 复合唯一索引
    __table_args__ = (
        Index('idx_search_key_source', 'search_key', 'source', unique=True),
    )
    
    def __repr__(self):
        return f"<SongMetadataCache(search_key={self.search_key}, source={self.source})>"


# 数据库迁移函数
def upgrade(engine):
    """执行升级迁移"""
    # 创建所有新表
    Base.metadata.create_all(bind=engine, tables=[
        Album.__table__,
        Lyric.__table__,
        SongMetadataCache.__table__
    ])
    print("✅ 已创建表: albums, lyrics, song_metadata_cache")


def downgrade(engine):
    """回滚迁移"""
    Album.__table__.drop(bind=engine, checkfirst=True)
    Lyric.__table__.drop(bind=engine, checkfirst=True)
    SongMetadataCache.__table__.drop(bind=engine, checkfirst=True)
    print("✅ 已删除表: albums, lyrics, song_metadata_cache")


if __name__ == "__main__":
    from sqlalchemy import create_engine
    
    # 创建数据库引擎
    engine = create_engine('sqlite:///music_monitor.db')
    
    print("="*80)
    print("🚀 开始数据库迁移")
    print("="*80)
    
    # 执行迁移
    upgrade(engine)
    
    print("\n" + "="*80)
    print("✅ 迁移完成!")
    print("="*80)

"""
IgnoredSong模型 - 用户忽略的歌曲记录

记录用户手动「忽略」的歌曲 (source, source_id) 键，用于防止新歌监控
在用户忽略后重新发现同一首歌（死循环）。

设计要点:
- 忽略 = 物理删除缓存文件 + 删除 Song 记录 + 在此登记 (source, source_id)
- 新歌监控 (NewReleaseMonitorService) 与自动下载队列消费时均排除本表命中的键
- 入库（收藏）后的歌曲不应出现在本表；若未来需要"取消忽略"，可删除本表记录

Author: music-monitor development team
Created: 2026-08-14
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from app.models.base import Base


class IgnoredSong(Base):
    """
    被用户忽略的歌曲 (防监控重发现的墓碑记录)
    """
    __tablename__ = "ignored_songs"
    __table_args__ = (
        UniqueConstraint('source', 'source_id', name='uq_ignored_song_key'),
    )

    id = Column(Integer, primary_key=True, index=True)
    # ondelete='SET NULL': 删除歌手时保留忽略墓碑 (artist_id 置空), 避免
    # 重新关注同一歌手后再次发现并下载已忽略的歌曲 (死循环)。
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="SET NULL"), nullable=True, index=True)

    source = Column(String, nullable=False)    # 'qqmusic', 'netease', 'local'
    source_id = Column(String, nullable=False) # mid / filename

    title = Column(String, nullable=True)      # 忽略时的标题快照 (便于排查)

    ignored_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<IgnoredSong(source={self.source}, id={self.source_id})>"

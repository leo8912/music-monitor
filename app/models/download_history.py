"""
下载历史记录模型 - 专门记录下载操作历史

此文件定义了DownloadHistory数据模型，用于记录每次下载操作的详细信息，
包括歌曲信息、平台信息、下载状态、时间等，实现与歌曲列表的解耦。

Author: music-monitor development team

更新日志:
2026-01-21 - 创建DownloadHistory模型，实现下载历史与歌曲列表的解耦
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from app.models.base import Base


class DownloadHistory(Base):
    """
    下载历史记录模型
    专门记录每次下载操作的详细信息
    """
    __tablename__ = 'download_history'
    
    id = Column(Integer, primary_key=True)
    song_unique_key = Column(String, nullable=False)  # 对应歌曲的唯一标识
    
    # 歌曲信息
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String)
    cover_url = Column(String)  # 封面图片链接
    
    # 平台信息
    source = Column(String, nullable=False)  # 如 'netease', 'qqmusic'
    source_id = Column(String, nullable=False)  # 平台内部ID
    
    # 下载信息
    download_path = Column(String)  # 下载文件路径
    download_status = Column(String, default='PENDING')  # PENDING, SUCCESS, FAILED
    download_time = Column(DateTime, default=datetime.now)
    download_duration = Column(Integer)  # 下载耗时（毫秒）
    file_size = Column(Integer)  # 文件大小（字节）
    quality = Column(String)  # 音质信息
    
    # 额外信息
    error_message = Column(String)  # 下载失败时的错误信息
    user_id = Column(Integer)  # 如果有多用户需求
    
    def __repr__(self):
        return f"<DownloadHistory(title={self.title}, source={self.source}, status={self.download_status})>"
"""
下载历史服务 - 处理下载历史相关业务逻辑

此文件提供了下载历史相关的业务逻辑处理，包括：
- 记录下载尝试
- 查询下载历史
- 获取下载统计信息

Author: music-monitor development team

更新日志:
2026-01-21 - 创建DownloadHistoryService，实现下载历史记录与查询功能
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime
import time

from app.models.download_history import DownloadHistory


class DownloadHistoryService:
    def __init__(self):
        pass
    
    async def log_download_attempt(
        self,
        db: AsyncSession,
        title: str,
        artist: str,
        album: str,
        source: str,
        source_id: str,
        status: str = 'PENDING',
        download_path: Optional[str] = None,
        error_message: Optional[str] = None,
        download_duration: Optional[int] = None,
        file_size: Optional[int] = None,
        quality: Optional[str] = None,
        cover_url: Optional[str] = None
    ):
        """记录下载尝试"""
        history_record = DownloadHistory(
            song_unique_key=f"{source}_{source_id}",
            title=title,
            artist=artist,
            album=album,
            cover_url=cover_url,
            source=source,
            source_id=source_id,
            download_status=status,
            download_path=download_path,
            error_message=error_message,
            download_duration=download_duration,
            file_size=file_size,
            quality=quality
        )
        
        db.add(history_record)
        await db.commit()
        await db.refresh(history_record)
        
        return history_record

    async def check_exists(self, db: AsyncSession, source: str, source_id: str) -> bool:
        """检查特定歌曲的下载历史是否存在"""
        query = select(DownloadHistory).where(
            DownloadHistory.source == source,
            DownloadHistory.source_id == str(source_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_download_history(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        source: Optional[str] = None,
        status: Optional[str] = None,
        artist: Optional[str] = None
    ) -> List[DownloadHistory]:
        """获取下载历史列表"""
        query = select(DownloadHistory).order_by(desc(DownloadHistory.download_time))
        
        if source:
            query = query.where(DownloadHistory.source == source)
        if status:
            query = query.where(DownloadHistory.download_status == status)
        if artist:
            query = query.where(DownloadHistory.artist.ilike(f'%{artist}%'))
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_download_stats(self, db: AsyncSession) -> dict:
        """获取下载统计信息"""
        query = select(DownloadHistory)
        result = await db.execute(query)
        all_records = result.scalars().all()
        
        total_downloads = len(all_records)
        success_count = sum(1 for r in all_records if r.download_status == 'SUCCESS')
        failed_count = sum(1 for r in all_records if r.download_status == 'FAILED')
        
        return {
            "total_downloads": total_downloads,
            "successful_downloads": success_count,
            "failed_downloads": failed_count,
            "success_rate": success_count / total_downloads if total_downloads > 0 else 0
        }
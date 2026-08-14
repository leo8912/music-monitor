# -*- coding: utf-8 -*-
"""
下载历史API路由

Author: google
Updated: 2026-01-26
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.services.download_history_service import DownloadHistoryService
from core.database import get_async_session
from app.models.download_history import DownloadHistory
from app.pagination import PaginatedResponse
from app.dependencies import require_auth

# 下载统计响应
from pydantic import BaseModel

class DownloadStatsResponse(BaseModel):
    """下载统计"""
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    success_rate: float = 0.0

router = APIRouter(prefix="/api/download-history", tags=["download_history"], dependencies=[Depends(require_auth)])


@router.get("/", response_model=PaginatedResponse)
async def get_download_history(
    # 统一分页参数
    page: int = Query(1, ge=1, description="页码,从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # 过滤参数
    source: Optional[str] = Query(None, description="筛选来源平台"),
    status: Optional[str] = Query(None, description="筛选下载状态"),
    artist: Optional[str] = Query(None, description="筛选艺术家"),
    db: AsyncSession = Depends(get_async_session)
):
    """获取下载历史记录（统一分页: page + page_size）"""
    current_page = page
    current_page_size = page_size
    offset = (page - 1) * page_size
    fetch_limit = page_size

    history_service = DownloadHistoryService()

    history_list = await history_service.get_download_history(
        db, offset, fetch_limit, source, status, artist
    )

    # 获取总数
    count_query = select(func.count()).select_from(DownloadHistory)
    if source:
        count_query = count_query.where(DownloadHistory.source == source)
    if status:
        count_query = count_query.where(DownloadHistory.download_status == status)
    if artist:
        count_query = count_query.where(DownloadHistory.artist.ilike(f'%{artist}%'))

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 转换为字典列表
    items = []
    for record in history_list:
        items.append({
            "id": record.id,
            "title": record.title,
            "artist": record.artist,
            "album": record.album,
            "source": record.source,
            "source_id": record.source_id,
            "status": record.download_status,
            "download_path": record.download_path,
            "download_time": record.download_time.isoformat() if record.download_time else None,
            "error_message": record.error_message,
            "cover_url": record.cover_url
        })

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=current_page,
        page_size=current_page_size
    )


@router.get("/stats", response_model=DownloadStatsResponse)
async def get_download_stats(
    db: AsyncSession = Depends(get_async_session)
):
    """获取下载统计信息"""
    history_service = DownloadHistoryService()
    stats = await history_service.get_download_stats(db)
    return stats

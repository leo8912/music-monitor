# -*- coding: utf-8 -*-
"""
浏览历史路由 - 播放/浏览历史记录

从 media.py 拆出（阶段 4.6）：历史域单一职责。
注意与 download_history.py（下载历史）区分：本模块是播放/浏览历史。

Author: google
Updated: 2026-08-13
"""
import logging
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import GenericActionResponse
from app.pagination import PaginatedResponse
from app.services.history_service import HistoryService
from app.repositories.media_record import MediaRecordRepository
from core.database import get_async_session
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.get("/api/history", response_model=PaginatedResponse)
async def get_history(
    page: int = Query(1, ge=1, description="页码,从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    author: Optional[str] = None,
    downloaded_only: bool = False,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """获取歌曲历史列表（统一分页: page + page_size）"""
    try:
        history_service = HistoryService()
        result = await history_service.get_history(
            db=db,
            limit=page_size,
            offset=(page - 1) * page_size,
            author=author,
            downloaded_only=downloaded_only
        )

        # 统一分页响应格式 (service 返回 items/total，补全分页字段)
        return PaginatedResponse.create(
            items=result.get('items', []),
            total=result.get('total', 0),
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"获取历史错误: {e}")
        raise HTTPException(status_code=500, detail="获取历史失败: 服务器内部错误, 请查看日志")


class PlayRecordRequest(BaseModel):
    title: str
    artist: str
    album: Optional[str] = ""
    source: str
    media_id: str
    cover: Optional[str] = None


@router.post("/api/history/record", response_model=GenericActionResponse)
async def record_history(
    req: PlayRecordRequest,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """记录/更新播放历史"""
    try:
        repo = MediaRecordRepository(db)
        unique_key = f"{req.source}_{req.media_id}"

        data = {
            "unique_key": unique_key,
            "source": req.source,
            "media_id": req.media_id,
            "media_type": "song",
            "title": req.title,
            "author": req.artist,
            "album": req.album,
            "cover": req.cover,
            "found_at": datetime.now()  # 关键：更新此时间以确保排序在前
        }

        record = await repo.create_or_update(data)
        return {"success": True, "unique_key": record.unique_key}
    except Exception as e:
        logger.error(f"记录历史错误: {e}")
        return {"success": False, "message": "操作失败, 请查看日志"}

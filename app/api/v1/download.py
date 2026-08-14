# -*- coding: utf-8 -*-
"""
下载路由 - 音频下载API端点

从 media.py 拆出（阶段 4.6）：下载域单一职责。
原 app/routers/download.py 已在阶段 4.2 删除，此文件复用其文件名承担下载端点。

Author: google
Updated: 2026-08-13
"""
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import DownloadRequest, DownloadAudioResponse
from core.database import get_async_session
from app.services.media_service import MediaService
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.post("/api/download_audio", response_model=DownloadAudioResponse)
async def download_audio_endpoint(
    req: DownloadRequest,
    media_service: MediaService = Depends(MediaService),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """下载音频文件"""
    logger.info(f"收到下载请求: {req.title} - {req.artist}")

    try:
        result = await media_service.download_audio(
            title=req.title,
            artist=req.artist,
            album=req.album,
            source=req.source,
            source_id=str(req.song_id),
            cover_url=req.pic_url,
            db=db
        )

        if result.get("already_exists") or result.get("file_path"):
            return {
                "local_path": result.get("file_path"),
                "local_audio_path": result.get("file_path"),
                "quality": 999,
                "has_lyric": True
            }
        else:
            raise HTTPException(status_code=500, detail="下载失败")
    except Exception as e:
        logger.error(f"下载错误: {e}")
        raise HTTPException(status_code=500, detail="下载失败: 服务器内部错误, 请查看日志")

# -*- coding: utf-8 -*-
"""
Media路由 - 媒体资源API端点

此文件定义了媒体资源相关的API路由，包括：
- 音频下载和播放
- 收藏管理
- 艺术家管理
- 移动端元数据接口

Author: google
Updated: 2026-01-26
"""
import os
import logging
import asyncio
from datetime import datetime
from urllib.parse import quote
from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import config
from app.schemas import DownloadRequest, ArtistConfig
from core.database import get_async_session
from app.services.media_service import MediaService
from app.services.subscription import SubscriptionService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/download_audio")
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
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/api/audio/{filename:path}")
async def serve_audio(
    filename: str, 
    media_service: MediaService = Depends(MediaService),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """提供音频文件"""
    try:
        file_path, song = await media_service.get_audio_path(filename, db)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="音频文件未找到")

        media_type = "audio/mpeg"
        if filename.endswith(".flac"):
            media_type = "audio/flac"
        
        filename_encoded = quote(filename)
        return FileResponse(
            file_path, 
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=utf-8''{filename_encoded}"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="音频文件未找到")
    except Exception as e:
        logger.error(f"提供音频错误: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


# /api/artists routes moved to subscription.py for better task management


@router.get("/api/play/{source}/{id}")
async def play_proxy(source: str, id: str):
    """获取直接播放链接"""
    from app.services.download_service import DownloadService
    
    download_service = DownloadService()
    url = await download_service.get_play_url(source, id)
    
    if url:
        return RedirectResponse(url)
    
    return JSONResponse({"error": "链接未找到"}, status_code=404)


@router.get("/api/history")
async def get_history(
    limit: int = 20, 
    offset: int = 0, 
    author: Optional[str] = None, 
    downloaded_only: bool = False,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """获取歌曲历史列表"""
    try:
        from app.services.history_service import HistoryService
        
        history_service = HistoryService()
        result = await history_service.get_history(
            db=db,
            limit=limit,
            offset=offset,
            author=author,
            downloaded_only=downloaded_only
        )
        
        return result
    except Exception as e:
        logger.error(f"获取历史错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


class PlayRecordRequest(BaseModel):
    title: str
    artist: str
    album: Optional[str] = ""
    source: str
    media_id: str
    cover: Optional[str] = None

@router.post("/api/history/record")
async def record_history(
    req: PlayRecordRequest,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """记录/更新播放历史"""
    try:
        from app.repositories.media_record import MediaRecordRepository
        from datetime import datetime
        
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
        return {"success": False, "message": str(e)}


@router.get("/api/mobile/metadata")
async def get_mobile_metadata(
    id: str, 
    sign: str, 
    expires: str, 
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """移动端元数据接口"""
    from core.security import verify_signature
    
    if not verify_signature(id, sign, expires):
        raise HTTPException(status_code=403, detail="链接无效")
        
    try:
        from app.repositories.song import SongRepository
        song_repo = SongRepository(db)
        
        parts = id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=404, detail="无效的唯一键格式")
        
        source, source_id = parts
        song = await song_repo.get_by_unique_key(source, source_id)
        
        if not song:
            raise HTTPException(status_code=404, detail="歌曲未找到")
        
        audio_url = ""
        if song.local_path:
            filename = os.path.basename(song.local_path)
            audio_url = f"/api/audio/{filename}"
            
        return {
            "title": song.title,
            "artist": song.artist.name if song.artist else song.title,
            "album": song.album,
            "cover": getattr(song, 'cover_url', None),
            "lyrics": song.metadata_json.get('lyric') if song.metadata_json else None,
            "audio_url": audio_url,
            "source": song.source,
            "is_favorite": song.is_favorite,
            "local_audio_path": song.local_path,
            "id": song.media_id,
            "unique_key": f"{song.source}_{song.media_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取移动端元数据错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

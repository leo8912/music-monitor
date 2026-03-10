# -*- coding: utf-8 -*-
"""
元数据API路由 - 歌词和封面获取

Author: google
Updated: 2026-01-26
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import io
import logging

logger = logging.getLogger(__name__)

from app.services._singletons import get_metadata_service
from core.database import AsyncSessionLocal
from app.models.song import Song
from sqlalchemy import select

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.get("/lyrics")
async def get_lyrics(
    title: str,
    artist: str,
    song_id: str = None
):
    """获取歌词"""
    try:
        local_path = None
        if song_id:
            try:
                # 尝试从数据库获取本地路径
                async with AsyncSessionLocal() as db:
                    stmt = select(Song).where(Song.id == int(song_id))
                    result = await db.execute(stmt)
                    song = result.scalars().first()
                    if song and song.local_path:
                        local_path = song.local_path
                        logger.debug(f"解析 song_id={song_id} 到 local_path={local_path}")
                    else:
                        logger.debug(f"未找到歌曲或无 local_path: id={song_id}")
            except Exception as db_e:
                logger.warning(f"解析 song_id 时数据库错误: {db_e}")

        metadata_service = get_metadata_service()
        lyrics = await metadata_service.fetch_lyrics(title, artist, source_id=None, local_path=local_path)
        
        if lyrics:
            return {"success": True, "lyrics": lyrics}
        else:
            return {"success": False, "error": "无法获取歌词"}
    except Exception as e:
        logger.error(f"获取歌词失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取歌词失败: {str(e)}")


@router.get("/cover")
async def get_cover(
    title: str,
    artist: str
):
    """获取封面"""
    try:
        metadata_service = get_metadata_service()
        cover_url = await metadata_service.fetch_cover_url(title, artist)
        
        if cover_url:
            # 下载封面数据
            cover_data = await metadata_service.fetch_cover_data(cover_url)
            if cover_data:
                return StreamingResponse(
                    io.BytesIO(cover_data), 
                    media_type="image/jpeg"
                )
        
        return {"success": False, "error": "无法获取封面"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取封面失败: {str(e)}")


@router.post("/fetch-all")
async def fetch_all_metadata(
    title: str,
    artist: str,
    source: str = None,
    source_id: str = None
):
    """获取完整元数据（歌词和封面）"""
    try:
        metadata_service = get_metadata_service()
        result = await metadata_service.fetch_metadata(title, artist, source, source_id)
        
        return {
            "success": result.success,
            "has_lyrics": result.lyrics is not None,
            "has_cover": result.cover_data is not None,
            "lyrics": result.lyrics,
            "cover_url": result.cover_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取元数据失败: {str(e)}")
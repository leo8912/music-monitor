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
import sys

logger = logging.getLogger(__name__)

from app.services.metadata_service import MetadataService
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
    # 强制写入文件进行调试
    with open("d:/code/music-monitor/logs/lyrics_debug.log", "a", encoding="utf-8") as f:
        f.write(f"\n=== {__import__('datetime').datetime.now()} === HIT /api/metadata/lyrics\n")
        f.write(f"song_id={song_id}, title={title}, artist={artist}\n")
    
    sys.stderr.write(f"\n=== DEBUG === HIT /api/metadata/lyrics with song_id={song_id}, title={title}\n")
    sys.stderr.flush()
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
                        sys.stderr.write(f"=== DEBUG === Resolved song_id={song_id} to local_path={local_path}\n")
                        sys.stderr.flush()
                    else:
                        sys.stderr.write(f"=== DEBUG === Song not found or no local_path for id={song_id}\n")
                        sys.stderr.flush()
            except Exception as db_e:
                sys.stderr.write(f"=== DEBUG === DB Error resolving song_id: {db_e}\n")
                sys.stderr.flush()
                pass 

        metadata_service = MetadataService()
        lyrics = await metadata_service.fetch_lyrics(title, artist, source_id=None, local_path=local_path)
        
        if lyrics:
            return {"success": True, "lyrics": lyrics}
        else:
            return {"success": False, "error": "无法获取歌词"}
    except Exception as e:
        import traceback
        error_msg = f"Error in get_lyrics: {str(e)}\n{traceback.format_exc()}"
        with open("d:/code/music-monitor/logs/lyrics_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n=== ERROR ===\n{error_msg}\n")
        
        sys.stderr.write(f"=== ERROR === {error_msg}\n")
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"获取歌词失败: {str(e)}")


@router.get("/cover")
async def get_cover(
    title: str,
    artist: str
):
    """获取封面"""
    try:
        metadata_service = MetadataService()
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
        metadata_service = MetadataService()
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
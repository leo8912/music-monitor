# -*- coding: utf-8 -*-
"""
移动端路由 - 签名链接元数据接口

从 media.py 拆出（阶段 4.6）：移动端域单一职责。
签名链接格式属 D9 可改范围，但当前保持不变以兼容历史卡片。

Author: google
Updated: 2026-08-13
"""
import os
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import MobileMetadataResponse
from core.database import get_async_session
from core.security import verify_signature
from app.repositories.song import SongRepository
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


def _extract_lyrics(song: Any) -> Optional[str]:
    """从 Song.sources 的 data_json 中提取歌词 (兼容 dict / JSON 字符串)。"""
    for src in song.sources or []:
        data = src.data_json
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (ValueError, TypeError):
                continue
        if isinstance(data, dict):
            lyric = data.get('lyrics') or data.get('lyric')
            if lyric:
                return lyric
    return None


def _main_source(song: Any) -> str:
    """主来源: 本地已下载优先, 否则取第一个非 local 平台。"""
    if getattr(song, 'local_path', None):
        return 'local'
    sources = [s.source for s in (song.sources or []) if s.source != 'local']
    if sources:
        return sources[0]
    if song.sources:
        return song.sources[0].source
    return 'unknown'


@router.get("/api/mobile/metadata", response_model=MobileMetadataResponse)
async def get_mobile_metadata(
    id: str,
    sign: str,
    expires: str,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """移动端元数据接口"""
    if not verify_signature(id, sign, expires):
        raise HTTPException(status_code=403, detail="链接无效")

    try:
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
            "cover": getattr(song, 'cover', None),
            "lyrics": _extract_lyrics(song),
            "audio_url": audio_url,
            "source": _main_source(song),
            "is_favorite": song.is_favorite,
            "local_audio_path": song.local_path,
            "id": song.unique_key,
            "unique_key": f"{source}_{source_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取移动端元数据错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

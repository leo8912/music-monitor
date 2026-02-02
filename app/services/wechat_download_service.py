# -*- coding: utf-8 -*-
"""
微信下载服务 - 处理微信交互触发的下载

此模块负责微信场景的下载操作：
- 调用 DownloadService 执行下载
- 记录创建与更新
- Magic Link 生成

Author: google
Updated: 2026-01-26
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from urllib.parse import quote
import logging

from app.repositories.media_record import MediaRecordRepository
from core.config import config

logger = logging.getLogger(__name__)


class WeChatDownloadService:
    """
    微信下载服务
    
    处理微信触发的后台下载，使用 DownloadService 执行实际下载。
    """
    
    @staticmethod
    async def download_and_save(
        db: AsyncSession,
        song: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        执行下载并保存记录
        
        Args:
            db: 数据库会话
            song: 歌曲信息 {title, artist, album, source, id, cover}
        
        Returns:
            下载结果字典
        """
        from app.services.download_service import DownloadService
        
        title = song.get('title', '')
        artist = song.get('artist', '')
        if isinstance(artist, list):
            artist = "/".join(artist)
        album = song.get('album', '')
        
        # 使用 DownloadService 执行下载
        download_service = DownloadService()
        
        try:
            result = await download_service.download_audio(
                title=title,
                artist=artist,
                album=album
            )
            
            if result:
                # 下载成功，创建记录
                return await WeChatDownloadService.create_or_update_record(
                    db=db,
                    song=song,
                    download_result=result,
                    cover_url=song.get('cover', '')
                )
            else:
                logger.error(f"微信下载失败: {title}")
                return None
                
        except Exception as e:
            logger.error(f"微信下载异常: {e}")
            return None
    
    @staticmethod
    async def create_or_update_record(
        db: AsyncSession,
        song: Dict[str, Any],
        download_result: Dict[str, Any],
        cover_url: str = ""
    ) -> Optional[Dict[str, Any]]:
        """下载完成后创建或更新媒体记录"""
        repo = MediaRecordRepository(db)
        
        unique_key = f"{song['source']}_{song['id']}"
        title = song.get('title', '')
        artist = song.get('artist', '')
        if isinstance(artist, list):
            artist = "/".join(artist)
        
        # 记录数据
        record_data = {
            "unique_key": unique_key,
            "source": song['source'],
            "media_type": "audio",
            "media_id": str(song['id']),
            "title": title,
            "author": artist,
            "album": song.get('album', ''),
            "local_audio_path": download_result.get('local_path'),
            "audio_quality": download_result.get('quality'),
            "publish_time": datetime.now()
        }
        
        # 处理封面
        final_cover = (
            download_result.get('cover') or 
            cover_url or 
            song.get('cover') or 
            ""
        )
        record_data["cover"] = final_cover
        
        # 创建或更新记录
        record = await repo.create_or_update(record_data)
        
        # 设置为收藏
        await repo.set_favorite(unique_key, True)
        
        # 生成 Magic Link
        magic_url = WeChatDownloadService._generate_magic_url(unique_key)
        
        return {
            "unique_key": unique_key,
            "magic_url": magic_url,
            "cover_url": final_cover,
            "title": title,
            "artist": artist,
            "local_path": download_result.get('local_path')
        }
    
    @staticmethod
    def _generate_magic_url(unique_key: str) -> str:
        """生成带签名的播放链接"""
        from core.security import generate_signed_url_params
        
        sign_params = generate_signed_url_params(unique_key)
        
        base_url = config.get('global', {}).get('external_url', 'http://localhost:8000')
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        
        magic_url = (
            f"{base_url}/#/mobile/play?"
            f"id={quote(sign_params['id'])}&"
            f"sign={sign_params['sign']}&"
            f"expires={sign_params['expires']}"
        )
        
        return magic_url

# -*- coding: utf-8 -*-
import logging
import asyncio
import os
import json
from typing import List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import quote

from app.services.download_service import DownloadService
from app.services.notification import NotificationService
from app.services.media_service import MediaService
from core.database import get_async_session
from core.config import config
from core.security import generate_signed_url_params

logger = logging.getLogger(__name__)

class AutoDownloadService:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AutoDownloadService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized'): return
        self._initialized = True
        self._download_service = DownloadService()
        self._media_service = MediaService()

    async def add_to_queue(self, songs: List[Any]):
        """
        将新发现的歌曲添加到后台下载队列。
        """
        if not songs:
            return
            
        logger.info(f"🚀 AutoDownloadService: 收到 {len(songs)} 首新歌，准备后台自动下载")
        # 使用 Task 在后台运行，不阻塞当前请求
        asyncio.create_task(self._process_queue(songs))

    async def _process_queue(self, songs: List[Any]):
        """内部队列处理器"""
        # 由于是后台任务，我们需要手动获取数据库会话
        async for db in get_async_session():
            for song in songs:
                try:
                    # 1. 检查是否已经下载
                    if song.local_path and os.path.exists(song.local_path):
                        logger.info(f"⏩ 歌曲已存在，跳过下载: {song.title}")
                        continue
                    
                    logger.info(f"📥 正在自动下载: {song.title} - {song.artist.name if hasattr(song.artist, 'name') else song.artist}")
                    
                    # 2. 调用 MediaService 进行下载 (包含自动补全元数据和存库)
                    result = await self._media_service.download_audio(
                        title=song.title,
                        artist=song.artist.name if hasattr(song.artist, 'name') else song.artist,
                        album=song.album,
                        source=song.source,
                        source_id=str(song.source_id),
                        cover_url=getattr(song, 'cover', None) or getattr(song, 'cover_url', None),
                        db=db
                    )
                    
                    if result and (result.get('file_path') or result.get('already_exists')):
                        logger.info(f"✅ 自动下载成功: {song.title}")
                        
                        # 3. 发送微信推送通知
                        external_url = config.get('global', {}).get('external_url', '')
                        if external_url:
                            # 构造唯一键并生成签名链接
                            u_key = f"{song.source}_{song.source_id}"
                            sign_params = generate_signed_url_params(u_key)
                            
                            magic_link = f"{external_url.rstrip('/')}/#/mobile/play?id={quote(sign_params['id'])}&sign={sign_params['sign']}&expires={sign_params['expires']}"
                            
                            await NotificationService.send_download_card(
                                title=song.title,
                                artist=song.artist.name if hasattr(song.artist, 'name') else song.artist,
                                album=song.album,
                                cover=getattr(song, 'cover', None) or getattr(song, 'cover_url', None),
                                magic_link=magic_link,
                                quality="FLAC" if result.get('quality', 0) >= 740 else "HQ"
                            )
                    else:
                        logger.warning(f"❌ 自动下载失败: {song.title}")

                except Exception as e:
                    logger.error(f"⚠️ 自动下载过程异常 ({song.title}): {e}", exc_info=True)
            
            # 后台任务处理完这一批次即结束
            break

_service = None

def get_auto_download_service():
    global _service
    if _service is None:
        _service = AutoDownloadService()
    return _service

# -*- coding: utf-8 -*-
import logging
import asyncio
import os
from typing import List, Dict

from app.services.download_service import DownloadService
from app.services.notification import NotificationService
from app.services.media_service import MediaService
from core.database import get_async_session
from core.config_manager import get_config_manager
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

    async def add_to_queue(self, snapshots: List[Dict]):
        """
        将新发现的歌曲（纯快照 dict）添加到后台下载队列。

        snapshot 结构: {title, artist, album, source, source_id, cover_url}
        使用快照而非 ORM 对象，避免跨协程/会话访问懒加载关系或幽灵字段。
        """
        if not snapshots:
            return
            
        logger.info(f"🚀 AutoDownloadService: 收到 {len(snapshots)} 首新歌，准备后台自动下载")
        # 使用 Task 在后台运行，不阻塞当前请求
        asyncio.create_task(self._process_queue(snapshots))

    async def _process_queue(self, snapshots: List[Dict]):
        """内部队列处理器"""
        # 由于是后台任务，我们需要手动获取数据库会话
        async for db in get_async_session():
            for snap in snapshots:
                title = snap.get("title", "")
                artist = snap.get("artist", "")
                album = snap.get("album", "")
                source = snap.get("source", "")
                source_id = str(snap.get("source_id", "") or "")
                cover_url = snap.get("cover_url", "")

                try:
                    logger.info(f"📥 正在自动下载: {title} - {artist}")

                    # 调用 MediaService 进行下载 (包含自动补全元数据和存库)
                    result = await self._media_service.download_audio(
                        title=title,
                        artist=artist,
                        album=album,
                        source=source,
                        source_id=source_id,
                        cover_url=cover_url,
                        db=db
                    )

                    if result and (result.get('file_path') or result.get('already_exists')):
                        logger.info(f"✅ 自动下载成功: {title}")

                        # 3. 下载完成通知：发送试听卡片 (点击即播) - 仅当 external_url 已配置
                        external_url = get_config_manager().get('system', {}).get('external_url', '')
                        if external_url and source and source_id:
                            # 构造唯一键并生成签名链接
                            u_key = f"{source}_{source_id}"
                            sign_params = generate_signed_url_params(u_key)

                            from urllib.parse import quote
                            magic_link = f"{external_url.rstrip('/')}/#/mobile/play?id={quote(sign_params['id'])}&sign={sign_params['sign']}&expires={sign_params['expires']}"

                            await NotificationService.send_download_card(
                                title=snap.get('title'),
                                artist=artist,
                                album=album,
                                cover=cover_url,
                                magic_link=magic_link,
                                quality="FLAC" if result.get('quality', 0) >= 740 else "HQ"
                            )
                        else:
                            logger.warning(f"未配置 external_url 或缺少 source，跳过试听卡片: {title}")
                    else:
                        logger.warning(f"❌ 自动下载失败: {title}")
                except Exception as e:
                    logger.error(f"⚠️ 自动下载过程异常 ({title}): {e}", exc_info=True)
            
            # 后台任务处理完这一批次即结束
            break

_service = None

def get_auto_download_service():
    global _service
    if _service is None:
        _service = AutoDownloadService()
    return _service

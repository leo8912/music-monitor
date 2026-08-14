# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import List, Dict, Optional
from urllib.parse import quote

from app.services.download_service import DownloadService
from app.services.notification import NotificationService
from core.database import get_async_session
from core.config_manager import get_config_manager
from core.security import generate_signed_url_params
from core.queue import enqueue

logger = logging.getLogger(__name__)

# 进程级下载并发控制: SQLite 单写者, 批量新歌发现时若多个下载批次并发
# 写库会触发 "database is locked"。原实现用 asyncio.Lock 把整个批次
# (含耗时最长的网络下载) 完全串行化, 使配置项 system.max_concurrent_downloads
# 形同虚设。改为按配置的并发度限流 (Semaphore), 既保留写库保护
# (并发数受限 + core.queue locked 重试 + SQLite busy_timeout 30s 兜底),
# 又让多个批次可并行执行网络下载阶段 (并发专项)。
_download_semaphore: Optional[asyncio.Semaphore] = None
_download_semaphore_init_lock = asyncio.Lock()


async def _get_download_semaphore() -> asyncio.Semaphore:
    """惰性初始化下载并发信号量 (并发度读配置, 容错默认 3)。

    Python 3.10+ 的 asyncio.Semaphore 不绑定事件循环, 模块级惰性创建安全。
    """
    global _download_semaphore  # noqa: PLW0603 - 惰性初始化惯用法
    if _download_semaphore is None:
        async with _download_semaphore_init_lock:
            if _download_semaphore is None:
                try:
                    n = int(get_config_manager().get('system', {}).get('max_concurrent_downloads', 3))
                except (TypeError, ValueError):
                    n = 3
                n = max(1, n)
                _download_semaphore = asyncio.Semaphore(n)
                logger.info(f"下载并发度: {n} (max_concurrent_downloads)")
    return _download_semaphore

class AutoDownloadService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AutoDownloadService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._download_service = DownloadService()
        # 延迟导入以打破循环依赖: media_service -> library -> artist_refresh_service
        # -> auto_download_service -> media_service
        from app.services.media_service import MediaService
        self._media_service = MediaService()

    async def add_to_queue(self, snapshots: List[Dict]):
        """
        将新发现的歌曲（纯快照 dict）添加到后台下载队列。

        snapshot 结构: {title, artist, album, source, source_id, cover_url}
        使用快照而非 ORM 对象，避免跨协程/会话访问懒加载关系或幽灵字段。

        arq 模式: 入 Redis 队列由 worker 消费; inline 模式: 进程内后台执行。
        """
        if not snapshots:
            return

        logger.info(f"🚀 AutoDownloadService: 收到 {len(snapshots)} 首新歌，准备后台自动下载")
        await enqueue("auto_download", snapshots=snapshots)

    async def _process_queue(self, snapshots: List[Dict]):
        """内部队列处理器"""
        # 并发限流: 同一时间最多 max_concurrent_downloads 个批次并行
        # (网络下载并发执行; 写库冲突由 SQLite busy_timeout + queue 重试兜底)
        async with await _get_download_semaphore():
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
    global _service  # noqa: PLW0603 - 单例惰性初始化惯用法
    if _service is None:
        _service = AutoDownloadService()
    return _service

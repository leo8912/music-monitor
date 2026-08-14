# -*- coding: utf-8 -*-
"""
后台任务注册表 (阶段 3 / R3)

arq worker (app/workers/worker.py) 与本进程 inline 执行共用此注册表。
所有任务通过 core.queue.register_task 注册，由 core.queue.enqueue 投递。

约定:
- 任务函数必须是 async, 入参可 JSON 序列化 (arq 经 Redis 传递)。
- ORM 对象不可直接入参, 应传 id/快照 dict, 任务内部自开 AsyncSessionLocal。
- 任务内尽量自开 session, 不依赖调用方 (跨进程隔离)。
"""
import logging
from typing import List, Dict, Optional

from core.queue import register_task

logger = logging.getLogger(__name__)


@register_task("auto_download")
async def auto_download(snapshots: List[Dict]):
    """新歌自动下载: 传入快照列表 (无 ORM 对象, 保证可序列化)。"""
    from app.services.auto_download_service import get_auto_download_service
    await get_auto_download_service()._process_queue(snapshots)


@register_task("heal_all")
async def heal_all(force: bool = False, limit: int = 50):
    """全库元数据治愈。"""
    from app.services.metadata_healer import MetadataHealer
    await MetadataHealer().heal_all(force=force, limit=limit)


@register_task("scan_library")
async def scan_library(incremental: bool = False):
    """全量/增量扫描本地音频库。"""
    from app.services.scan_service import ScanService
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await ScanService().scan_local_files(db, incremental=incremental)


@register_task("wechat_download")
async def wechat_download(song: Dict, user_id: str):
    """微信渠道单曲下载 (自包含: 下载+保存记录+通知)。"""
    from core.database import AsyncSessionLocal
    from app.services.download_service import DownloadService
    from app.services.wechat_download_service import WeChatDownloadService
    from app.services.notification import NotificationService
    from app.notifiers.wecom import WeComNotifier

    title = song.get('title', '')
    artist = song.get('artist', '')
    if isinstance(artist, list):
        artist = "/".join(artist)

    try:
        result = await DownloadService().download_audio(
            title=title,
            artist=artist,
            album=song.get('album', '')
        )
        if not result:
            await WeComNotifier().send_text(f"❌ 下载失败：{title}", [user_id])
            return

        async with AsyncSessionLocal() as db:
            record_result = await WeChatDownloadService.create_or_update_record(
                db=db, song=song, download_result=result,
                cover_url=song.get('cover', '')
            )

        if record_result:
            await NotificationService.send_download_card(
                title=title, artist=artist, album=song.get('album', ''),
                cover=record_result.get('cover_url', ''),
                magic_link=record_result.get('magic_url', ''),
                quality=record_result.get('audio_quality') or 'Standard'
            )
        else:
            await WeComNotifier().send_text("⚠️ 下载成功但保存失败", [user_id])
    except Exception as e:
        logger.error(f"微信下载任务异常: {e}", exc_info=True)
        try:
            await WeComNotifier().send_text(f"❌ 系统错误：{e}", [user_id])
        except Exception:
            pass


@register_task("wechat_import")
async def wechat_import(song_id: int, user_id: str):
    """微信「待定」入库: 收藏歌曲 (自包含 session)。"""
    from sqlalchemy import select
    from core.database import AsyncSessionLocal
    from app.models.song import Song
    from app.services.favorite_service import FavoriteService
    from app.notifiers.wecom import WeComNotifier

    try:
        async with AsyncSessionLocal() as db:
            song = (await db.execute(select(Song).where(Song.id == song_id))).scalars().first()
            title = song.title if song else ""
            result = await FavoriteService().toggle(db, song_id)
        if result and result.get('is_favorite'):
            await WeComNotifier().send_text(
                f"✅ 已入库：{title}\n已移至收藏夹，可在资料库中查看。", [user_id])
        else:
            await WeComNotifier().send_text("⚠️ 入库失败或歌曲不存在", [user_id])
    except Exception as e:
        logger.error(f"微信入库任务异常: {e}", exc_info=True)
        try:
            await WeComNotifier().send_text(f"❌ 系统错误: {e}", [user_id])
        except Exception:
            pass


@register_task("wechat_ignore")
async def wechat_ignore(song_id: int, user_id: str):
    """微信「待定」忽略: 删文件+删Song+写墓碑 (自包含 session)。"""
    from sqlalchemy import select
    from core.database import AsyncSessionLocal
    from app.models.song import Song
    from app.services.ignore_service import IgnoreService
    from app.notifiers.wecom import WeComNotifier

    try:
        async with AsyncSessionLocal() as db:
            song = (await db.execute(select(Song).where(Song.id == song_id))).scalars().first()
            title = song.title if song else ""
            ok = await IgnoreService().ignore_song(db, song_id)
        if ok:
            await WeComNotifier().send_text(
                f"🗑️ 已忽略：{title}\n该歌曲不再监控推送，文件与记录已删除。", [user_id])
        else:
            await WeComNotifier().send_text("⚠️ 忽略失败: 歌曲不存在", [user_id])
    except Exception as e:
        logger.error(f"微信忽略任务异常: {e}", exc_info=True)
        try:
            await WeComNotifier().send_text(f"❌ 系统错误: {e}", [user_id])
        except Exception:
            pass


@register_task("refresh_artist")
async def refresh_artist(artist_name: str, source: Optional[str] = None, artist_id: Optional[str] = None):
    """添加歌手后的后台任务: 智能关联 + 刷新全量歌曲 (自包含 session, 带去重)。"""
    from app.services.subscription import (
        SubscriptionService,
        acquire_active_refresh,
        release_active_refresh,
    )
    from app.services.library import LibraryService
    from core.database import AsyncSessionLocal

    if not await acquire_active_refresh(artist_name):
        logger.info(f"⏭️ [Queue] Artist '{artist_name}' is already being refreshed, skipping.")
        return

    logger.info(f"🚀 [Queue Start] Setting up artist: {artist_name} (Source: {source}:{artist_id})")

    try:
        async with AsyncSessionLocal() as db:
            logger.info(f"🔍 [Queue] Linking sources for {artist_name}...")
            if source and artist_id:
                await SubscriptionService.smart_link_sources(db, artist_name, source, artist_id)
            else:
                await SubscriptionService.smart_link_sources(db, artist_name)

            logger.info(f"📥 [Queue] Refreshing songs for {artist_name}...")
            service = LibraryService()
            count = await service.refresh_artist(db, artist_name)
            logger.info(f"✅ [Queue Complete] {artist_name}: Found {count} songs")
    except Exception as e:
        logger.error(f"❌ [Queue Failed] {artist_name}: {e}", exc_info=True)
    finally:
        await release_active_refresh(artist_name)


@register_task("release_check")
async def release_check():
    """新歌增量监控 (替代 APScheduler 定时, worker 侧 cron 触发)。"""
    from app.services.new_release_monitor import get_new_release_monitor
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await get_new_release_monitor().check_all(db)


@register_task("asset_localize")
async def asset_localize():
    """媒体资源本地化巡检 (头像/封面落盘)。"""
    from app.services.scheduling import run_asset_localization
    await run_asset_localization()


@register_task("file_integrity")
async def file_integrity():
    """文件完整性检查。"""
    from app.services.media_service import check_file_integrity
    await check_file_integrity()

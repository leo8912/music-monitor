# -*- coding: utf-8 -*-
"""
Scheduling - 周期任务注册与重排

统一管理所有循环任务，避免在 main.py 内联零散注册。
- job_new_release_check: 新歌增量监控 (默认 6h，可配置)
- job_file_integrity: 每 24h 文件完整性检查
- job_asset_localize: 每 24h 媒体资源本地化巡检
- job_cache_cleanup: 每 24h 音频缓存自动清理 (孤儿文件 + 容量超限, 待定歌曲不清理)

Author: music-monitor development team
"""
import logging

from core.config_manager import get_config_manager
from core.database import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.artist import Artist
from app.models.song import Song
from app.services.media_asset_service import MediaAssetService
from app.services.new_release_monitor import get_new_release_monitor
from app.services.media_service import check_file_integrity

logger = logging.getLogger(__name__)

# 任务 ID (稳定标识，供重排/移除使用)
JOB_RELEASE_CHECK = "job_new_release_check"
JOB_FILE_INTEGRITY = "job_file_integrity"
JOB_ASSET_LOCALIZE = "job_asset_localize"
JOB_CACHE_CLEANUP = "job_cache_cleanup"

# 默认: 6 小时
DEFAULT_RELEASE_INTERVAL_MINUTES = 360

# 默认: 缓存清理每 24 小时
DEFAULT_CACHE_CLEANUP_INTERVAL_HOURS = 24


def get_cache_cleanup_interval_hours() -> int:
    """获取缓存清理间隔 (小时)。优先级: scheduler.cleanup_interval_hours -> 默认 24。"""
    sched = get_config_manager().get("scheduler", {}) or {}
    iv = sched.get("cleanup_interval_hours")
    if iv:
        return int(iv)
    return DEFAULT_CACHE_CLEANUP_INTERVAL_HOURS


def get_release_interval_minutes() -> int:
    """获取新歌监控间隔 (分钟)。优先级:
    monitor.interval_minutes -> monitor.interval(分钟) -> scheduler.check_interval_minutes -> 默认 360。
    """
    mon = get_config_manager().get("monitor", {}) or {}
    sched = get_config_manager().get("scheduler", {}) or {}

    iv = mon.get("interval_minutes")
    if iv:
        return int(iv)

    iv = mon.get("interval")
    if iv:
        return int(iv)

    iv = sched.get("check_interval_minutes")
    if iv:
        return int(iv)

    return DEFAULT_RELEASE_INTERVAL_MINUTES


async def run_new_release_check():
    """增量新歌监控（轻量，可高频）。"""
    try:
        async with AsyncSessionLocal() as db:
            await get_new_release_monitor().check_all(db)
    except Exception as e:
        logger.error(f"[Scheduler] 新歌增量监控失败: {e}", exc_info=True)


async def run_asset_localization():
    """媒体资源本地化巡检: 全库头像/封面远程 URL 落盘 (低频, 每 24h)。"""
    try:
        svc = MediaAssetService()
        async with AsyncSessionLocal() as db:
            # 1. 歌手头像: 远程 URL 或空 → 补源下载
            stmt = select(Artist).options(selectinload(Artist.sources))
            artists = (await db.execute(stmt)).scalars().all()
            avatar_fixed = 0
            for artist in artists:
                av = artist.avatar or ""
                # 已本地化 → 跳过；空 或 远程/代理 URL → 尝试本地化
                if av.startswith("/uploads/"):
                    continue
                try:
                    if await svc.ensure_avatar(artist, sources=list(artist.sources)):
                        avatar_fixed += 1
                except Exception as e:
                    logger.warning(f"[Asset] 头像本地化失败 {artist.name}: {e}")
            if avatar_fixed:
                await db.commit()
                logger.info(f"[Asset] 头像本地化巡检完成: 修复 {avatar_fixed} 个")

            # 2. 歌曲封面: 远程 URL → 落盘
            stmt2 = select(Song).where(
                (Song.cover.isnot(None)) & (Song.cover != "") &
                (~Song.cover.like("/uploads/%"))
            ).limit(200)
            songs = (await db.execute(stmt2)).scalars().all()
            cover_fixed = 0
            for song in songs:
                try:
                    if await svc.ensure_cover(song):
                        cover_fixed += 1
                except Exception as e:
                    logger.warning(f"[Asset] 封面本地化失败 {song.title}: {e}")
            if cover_fixed:
                await db.commit()
                logger.info(f"[Asset] 封面本地化巡检完成: 修复 {cover_fixed} 个")
    except Exception as e:
        logger.error(f"[Scheduler] 媒体资源本地化巡检失败: {e}", exc_info=True)


async def run_cache_cleanup():
    """音频缓存自动清理: 孤儿文件 + 容量超限 (待定歌曲永不自动删除, 每 24h)。"""
    from app.services.cache_cleanup_service import get_cache_cleanup_service

    try:
        async with AsyncSessionLocal() as db:
            result = await get_cache_cleanup_service().cleanup(db)
            logger.info(f"[Scheduler] 缓存清理执行完成: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] 缓存清理失败: {e}", exc_info=True)


def register_recurring_jobs(scheduler) -> None:
    """注册所有循环任务。scheduler 为 APScheduler(AsyncIOScheduler/SimpleScheduler) 实例。"""
    scheduler.add_job(
        run_new_release_check,
        "interval",
        minutes=get_release_interval_minutes(),
        id=JOB_RELEASE_CHECK,
        replace_existing=True,
    )
    logger.info(f"[Scheduler] 新歌增量监控: 每 {get_release_interval_minutes()} 分钟")

    scheduler.add_job(
        check_file_integrity,
        "interval",
        hours=24,
        id=JOB_FILE_INTEGRITY,
        replace_existing=True,
    )

    scheduler.add_job(
        run_asset_localization,
        "interval",
        hours=24,
        id=JOB_ASSET_LOCALIZE,
        replace_existing=True,
    )
    logger.info("[Scheduler] 媒体资源本地化巡检: 每 24 小时")

    scheduler.add_job(
        run_cache_cleanup,
        "interval",
        hours=get_cache_cleanup_interval_hours(),
        id=JOB_CACHE_CLEANUP,
        replace_existing=True,
    )
    logger.info(f"[Scheduler] 音频缓存自动清理: 每 {get_cache_cleanup_interval_hours()} 小时")


def reschedule_release_job(scheduler) -> None:
    """按最新配置重排新歌监控任务 (设置页保存后调用，无需重启)。"""
    minutes = get_release_interval_minutes()
    try:
        scheduler.remove_job(JOB_RELEASE_CHECK)
    except Exception:
        pass
    try:
        scheduler.add_job(
            run_new_release_check,
            "interval",
            minutes=minutes,
            id=JOB_RELEASE_CHECK,
            replace_existing=True,
        )
        logger.info(f"[Scheduler] 新歌增量监控已重排为每 {minutes} 分钟")
    except Exception as e:
        logger.error(f"[Scheduler] 重排新歌监控失败: {e}")

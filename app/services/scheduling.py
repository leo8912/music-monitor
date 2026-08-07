# -*- coding: utf-8 -*-
"""
Scheduling - 周期任务注册与重排

统一管理所有循环任务，避免在 main.py 内联零散注册。
- job_new_release_check: 新歌增量监控 (默认 6h，可配置)
- job_file_integrity: 每 24h 文件完整性检查
- job_auto_cache: 每 30min 自动缓存近期歌曲

Author: music-monitor development team
"""
import logging

from core.config_manager import get_config_manager

logger = logging.getLogger(__name__)

# 任务 ID (稳定标识，供重排/移除使用)
JOB_RELEASE_CHECK = "job_new_release_check"
JOB_FILE_INTEGRITY = "job_file_integrity"
JOB_AUTO_CACHE = "job_auto_cache"

# 默认: 6 小时
DEFAULT_RELEASE_INTERVAL_MINUTES = 360


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
    handled_by = None
    try:
        from core.database import AsyncSessionLocal
        from app.services.new_release_monitor import get_new_release_monitor

        async with AsyncSessionLocal() as db:
            await get_new_release_monitor().check_all(db)
    except Exception as e:
        logger.error(f"[Scheduler] 新歌增量监控失败: {e}", exc_info=True)


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

    from app.services.media_service import check_file_integrity, auto_cache_recent_songs

    scheduler.add_job(
        check_file_integrity,
        "interval",
        hours=24,
        id=JOB_FILE_INTEGRITY,
        replace_existing=True,
    )

    scheduler.add_job(
        auto_cache_recent_songs,
        "interval",
        minutes=30,
        id=JOB_AUTO_CACHE,
        replace_existing=True,
    )


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
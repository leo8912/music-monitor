# -*- coding: utf-8 -*-
"""
系统扫描路由 - 库扫描与来源检查触发

从 system.py 拆出（阶段 4.6）：扫描域单一职责。

Author: google
Updated: 2026-08-13
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ScanResultResponse, GenericActionResponse
from app.services.library import LibraryService
from core.scheduler import scheduler
from core.database import get_async_session
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.post("/api/system/scan", response_model=ScanResultResponse)
async def trigger_library_scan(db: AsyncSession = Depends(get_async_session)):
    """
    手动触发本地资料库扫描与补全 (Phase 9)
    """
    try:
        service = LibraryService()

        # 1. 扫描文件
        new_count = await service.scan_local_files(db)

        # 2. 补全元数据 (可以异步执行，或者这里只触发少量)
        # 为即时反馈，这里同步执行一次小批量补全
        enrich_count = await service.enrich_metadata(db, limit=5)

        # 3. 如果还有更多，可以后台执行 (TODO: 集成到 Scheduler)

        return {
            "status": "success",
            "new_files_found": new_count,
            "metadata_enriched": enrich_count,
            "message": f"Scanned {new_count} new files, enriched {enrich_count}."
        }
    except Exception as e:
        logger.error(f"Library scan failed: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")


@router.post("/api/system/cache_cleanup", response_model=GenericActionResponse)
async def trigger_cache_cleanup(db: AsyncSession = Depends(get_async_session)):
    """
    手动触发音频缓存自动清理。

    清理 cache_dir 中的孤儿文件 (DB 无记录的下载残留)，并处理容量超限。
    待定歌曲 (DB 有记录且文件在缓存内) 不会被自动删除。
    """
    from app.services.cache_cleanup_service import get_cache_cleanup_service

    try:
        result = await get_cache_cleanup_service().cleanup(db)
        if result.get("skipped"):
            return {"status": "success", "message": "缓存清理未执行 (自动清理未启用或无缓存目录)"}
        removed = result.get("removed_count", 0)
        freed_mb = result.get("freed_bytes", 0) / 1048576
        kept = result.get("kept_pending", 0)
        return {
            "status": "success",
            "message": f"缓存清理完成: 删除 {removed} 个孤儿文件, 释放 {freed_mb:.1f} MB, 保留待定歌曲 {kept} 首",
        }
    except Exception as e:
        logger.error(f"手动缓存清理失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")


@router.post("/api/check/{source}", response_model=GenericActionResponse)
@router.post("/api/run_check/{source}", response_model=GenericActionResponse)
async def trigger_check(source: str):
    """手动触发指定平台的同步检查"""
    if source not in ['netease', 'qqmusic']:
        raise HTTPException(status_code=400, detail="Invalid source")

    # 触发对应平台的立即检查
    # Correct ID from main.py is "job_{source}"
    job_id = f"job_{source}"
    job = scheduler.get_job(job_id)

    if not job:
        logger.warning(f"Job {job_id} not found in scheduler, available: {[j.id for j in scheduler.get_jobs()]}")
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    try:
        # 立即执行任务
        job.modify(next_run_time=datetime.now())  # Use datetime.now() for immediate run in some APScheduler versions or modify next_run_time
        # In APScheduler, next_run_time=None usually means paused.
        # To trigger now, we can use scheduler.trigger_job(job_id) if it exists or just modify to now.
        # scheduler.add_job(..., next_run_time=datetime.now())
        # Let's use the most reliable way for APScheduler
        try:
            scheduler.modify_job(job_id, next_run_time=datetime.now())
        except Exception:
            job.modify(next_run_time=datetime.now())

        logger.info(f"手动触发 {source} 同步检查")
        return {"status": "success", "message": f"{source} 同步已触发"}
    except Exception as e:
        logger.error(f"触发 {source} 检查失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")

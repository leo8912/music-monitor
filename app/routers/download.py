"""
下载API路由 - 提供下载相关API端点

此文件定义了下载相关的API路由，包括：
- 音频下载
- 下载状态查询
- 下载重试
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any

from app.services.download_service import DownloadService
from app.services.download_history_service import DownloadHistoryService
from core.database import get_async_session
from app.schemas import DownloadRequest

router = APIRouter(prefix="/api/download", tags=["download"])

# 全局下载服务实例
download_service = DownloadService()


@router.post("/audio")
async def download_audio(
    req: DownloadRequest,
    download_service: DownloadService = Depends(lambda: download_service),
    history_service: DownloadHistoryService = Depends(DownloadHistoryService),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """下载音频文件"""
    try:
        # 记录下载历史
        await history_service.log_download_attempt(
            db, req.title, req.artist, req.album, req.source, str(req.song_id), 'PENDING'
        )
        
        # 执行下载
        result = await download_service.download_audio(
            title=req.title,
            artist=req.artist,
            album=req.album,
            source=req.source,
            source_id=str(req.song_id)
        )
        
        if result:
            # 更新下载历史
            await history_service.log_download_attempt(
                db, req.title, req.artist, req.album, req.source, str(req.song_id), 
                'SUCCESS', result.get('local_path')
            )
            return result
        else:
            # 记录失败
            await history_service.log_download_attempt(
                db, req.title, req.artist, req.album, req.source, str(req.song_id), 
                'FAILED', error_message="Download failed"
            )
            raise HTTPException(status_code=500, detail="Download failed")
            
    except Exception as e:
        # 记录异常
        await history_service.log_download_attempt(
            db, req.title, req.artist, req.album, req.source, str(req.song_id), 
            'FAILED', error_message=str(e)
        )
        raise


@router.get("/status/{task_id}")
async def get_download_status(
    task_id: str, 
    download_service: DownloadService = Depends(lambda: download_service)
):
    """获取下载状态"""
    status = await download_service.get_download_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.post("/retry/{task_id}")
async def retry_download(
    task_id: str, 
    download_service: DownloadService = Depends(lambda: download_service)
):
    """重试下载"""
    success = await download_service.retry_failed_download(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot retry this task")
    return {"message": "Retry initiated"}


@router.get("/options/retry")
async def get_retry_options(
    download_service: DownloadService = Depends(lambda: download_service)
):
    """获取重试选项"""
    return download_service.retry_manager.get_retry_options()
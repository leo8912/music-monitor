# -*- coding: utf-8 -*-
"""
Library API路由 - 本地资料库管理

Author: google
Updated: 2026-01-26
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import os
from sqlalchemy import select

from core.database import get_async_session
from app.services.library import LibraryService
from app.services.scan_service import ScanService
from app.services.metadata_healer import MetadataHealer
from app.repositories.song import SongRepository
from app.models.song import SongSource
from app.pagination import PaginatedResponse
from app.dependencies import require_auth
from app.schemas import GenericActionResponse, EnrichResponse, FavoriteResponse, DeleteResponse, RedownloadResponse, RefreshArtistResponse, FixQualityResponse, ScanLibraryResponse, DownloadFromSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/library", tags=["library"], dependencies=[Depends(require_auth)])


@router.get("/songs", response_model=PaginatedResponse)
async def get_library_songs(
    # 统一分页参数 (page, page_size)
    page: int = Query(1, ge=1, description="页码,从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # 其他过滤参数
    artist_name: Optional[str] = Query(None, description="歌手名过滤"),
    is_favorite: Optional[bool] = Query(None, description="收藏过滤"),
    monitored_only: bool = Query(True, description="仅显示关注歌手(默认True)"),
    sort_by: str = Query("created_at", description="排序字段: created_at, publish_time, title"),
    order: str = Query("desc", description="排序方向: desc, asc"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取本地资料库歌曲（统一分页: page + page_size）
    """
    try:
        # 统一分页参数
        current_page = page
        current_page_size = page_size
        offset = (page - 1) * page_size
        fetch_limit = page_size

        song_repo = SongRepository(db)
        songs, total = await song_repo.get_paginated(
            skip=offset,
            limit=fetch_limit,
            artist_name=artist_name,
            is_favorite=is_favorite,
            only_monitored=monitored_only,
            sort_by=sort_by,
            order=order
        )

        # 去重
        from app.services.deduplication_service import DeduplicationService
        deduplicated_items = DeduplicationService.deduplicate_songs(songs)

        # 返回统一分页格式
        return PaginatedResponse.create(
            items=deduplicated_items,
            total=total,
            page=current_page,
            page_size=current_page_size
        )
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取资料库失败: 服务器内部错误, 请查看日志")


@router.post("/match-metadata", response_model=GenericActionResponse)
async def match_metadata(
    match_data: dict, # {song_id, target_source, target_song_id}
    db: AsyncSession = Depends(get_async_session)
):
    """
    手动匹配元数据 (Manual Match)
    强制使用指定源的元数据覆盖本地文件
    """
    from app.services.library import LibraryService
    service = LibraryService()

    song_id = match_data.get("song_id")
    target_source = match_data.get("target_source")
    target_song_id = match_data.get("target_song_id")

    if not all([song_id, target_source, target_song_id]):
         return {"success": False, "message": "Missing required parameters"}

    success = await service.apply_metadata_match(db, song_id, target_source, target_song_id)
    return {"success": success}

@router.get("/local-songs", response_model=PaginatedResponse)
async def get_local_songs(
    # 统一分页参数
    page: int = Query(1, ge=1, description="页码,从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段: created_at, publish_time, artist, title, album"),
    order: str = Query("desc", description="排序方向: desc, asc"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    专门获取所有本地歌曲 (有 local_path 的歌曲)
    无视是否关注歌手,按入库时间倒序排列
    """
    try:
        from app.services.library import LibraryService

        # 统一分页参数
        current_page = page
        current_page_size = page_size
        offset = (page - 1) * page_size
        fetch_limit = page_size

        service = LibraryService()
        items, total = await service.get_local_songs_paginated(
            db, offset, fetch_limit, sort_by, order
        )

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=current_page,
            page_size=current_page_size
        )
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取本地音乐失败: 服务器内部错误, 请查看日志")


@router.post("/scan", response_model=ScanLibraryResponse)
async def scan_library(db: AsyncSession = Depends(get_async_session)):
    """扫描本地文件"""
    try:
        scan_service = ScanService()
        result = await scan_service.scan_local_files(db)
        return {"success": True, **result}
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="扫描失败: 服务器内部错误, 请查看日志")


@router.post("/local/enrich", response_model=EnrichResponse)
async def enrich_local_files_endpoint(
    db: AsyncSession = Depends(get_async_session)
):
    """
    补全本地文件元数据 (自动下载封面/专辑/年份/歌词)
    触发后台任务 (使用 MetadataHealer)
    """
    try:
        from core.queue import enqueue
        # 以后台任务运行，避免阻塞接口 (用户手动触发，使用 force=True 确保真正补全)
        # arq 模式入 Redis 队列; inline 模式进程内后台执行
        await enqueue("heal_all", force=True, limit=50)
        return {"success": True, "message": "Metadata healing task started (background)"}
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="补全任务启动失败: 服务器内部错误, 请查看日志")


@router.post("/metadata/refresh", response_model=EnrichResponse)
async def refresh_library_metadata(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session)
):
    """
    刷新资料库元数据 (强制)
    手动触发，无视冷却期
    """
    try:
        metadata_healer = MetadataHealer()
        # 手动刷新，强制治愈 force=True
        count = await metadata_healer.heal_all(force=True, limit=limit)
        return {"success": True, "enriched_count": count}
    except Exception:
        raise HTTPException(status_code=500, detail="资料库刷新失败: 服务器内部错误, 请查看日志")


@router.post("/songs/{song_id}/favorite", response_model=FavoriteResponse)
async def toggle_favorite(
    song_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """切换收藏状态"""
    try:
        service = LibraryService()
        result = await service.toggle_favorite(song_id, db)
        if result:
            return result
        raise HTTPException(status_code=404, detail="歌曲未找到")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="操作失败: 服务器内部错误, 请查看日志")


@router.delete("/songs/{song_id}", response_model=DeleteResponse)
async def delete_song(
    song_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    删除歌曲 (忽略语义)

    删除本地文件 + 删除 Song 记录 + 写忽略墓碑 (ignored_songs)。
    墓碑用于防止新歌监控在删除后重新发现同一首歌 (死循环)。
    """
    try:
        service = LibraryService()
        success = await service.ignore_song(song_id, db)
        if success:
            return {"success": True}
        raise HTTPException(status_code=404, detail="歌曲未找到")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="删除失败: 服务器内部错误, 请查看日志")


from pydantic import BaseModel


class RedownloadRequest(BaseModel):
    song_id: int
    source: str
    track_id: str
    quality: int = 999
    title: Optional[str] = None
    artist: Optional[str] = None

@router.post("/redownload", response_model=RedownloadResponse)
async def redownload_song_endpoint(
    req: RedownloadRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    重新下载歌曲 (Re-download)
    """
    try:
        service = LibraryService()
        success = await service.redownload_song(
            db,
            req.song_id,
            req.source,
            req.track_id,
            req.quality,
            title=req.title,
            artist=req.artist
        )

        if success:
            from app.repositories.song import SongRepository
            repo = SongRepository(db)
            updated_song = await repo.get(req.song_id)

            # Use deduplication service to convert to dict format frontend expects
            from app.services.deduplication_service import DeduplicationService
            items = DeduplicationService.deduplicate_songs([updated_song])

            return {
                "success": True,
                "song": items[0] if items else None
            }

        return {"success": False}
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="重新下载失败: 服务器内部错误, 请查看日志")


class DownloadFromSearchRequest(BaseModel):
    title: str
    artist: str
    album: Optional[str] = ""
    source: str
    source_id: str
    quality: int = 999
    cover_url: Optional[str] = ""

@router.post("/download", response_model=DownloadFromSearchResponse)
async def download_from_search_endpoint(
    req: DownloadFromSearchRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    从搜索结果直接下载 (Direct Download)
    """
    try:
        service = LibraryService()
        result = await service.download_song_from_search(
            db,
            title=req.title,
            artist=req.artist,
            album=req.album,
            source=req.source,
            source_id=req.source_id,
            quality=req.quality,
            cover_url=req.cover_url
        )
        return result
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="下载失败: 服务器内部错误, 请查看日志")

class RefreshRequest(BaseModel):
    artist_name: str

@router.post("/refresh_artist", response_model=RefreshArtistResponse)
async def refresh_artist(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """刷新指定歌手的歌曲"""
    try:
        service = LibraryService()
        count = await service.refresh_artist(db, request.artist_name)
        return {"success": True, "new_songs_count": count}
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="刷新失败: 服务器内部错误, 请查看日志")


@router.delete("/artists/{artist_id}", response_model=DeleteResponse)
async def delete_artist_by_id(
    artist_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """删除歌手及其所有歌曲"""
    try:
        service = LibraryService()
        success = await service.delete_artist(db, artist_id=artist_id)
        if success:
            return {"success": True, "message": f"Artist {artist_id} deleted"}
        raise HTTPException(status_code=404, detail="Artist not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="删除失败: 服务器内部错误, 请查看日志")

@router.delete("/artists/name/{artist_name}", response_model=DeleteResponse)
async def delete_artist_by_name(
    artist_name: str,
    db: AsyncSession = Depends(get_async_session)
):
    """通过名称删除歌手及其所有歌曲"""
    try:
        service = LibraryService()
        success = await service.delete_artist(db, artist_name=artist_name)
        if success:
            return {"success": True, "message": f"Artist {artist_name} deleted"}
        # If not found, maybe just success? No, 404 is better.
        raise HTTPException(status_code=404, detail="Artist not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="删除失败: 服务器内部错误, 请查看日志")

@router.delete("/source/{source_db_id}", response_model=DeleteResponse)
async def delete_source(
    source_db_id: int,
    delete_file: bool = Query(True, description="Whether to delete the physical file"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete a specific source (e.g., a specific local file).
    If it's a local source, optionally delete the physical file.
    """
    try:
        # 1. Fetch the source
        stmt = select(SongSource).where(SongSource.id == source_db_id)
        result = await db.execute(stmt)
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        file_path_to_delete = None
        if source.source == 'local' and delete_file and source.url:
             file_path_to_delete = source.url

        # 2. Delete from DB
        await db.delete(source)
        await db.commit()

        # 3. Delete physical file if requested
        deleted_file = False
        if file_path_to_delete and os.path.exists(file_path_to_delete):
            try:
                import anyio
                await anyio.to_thread.run_sync(os.remove, file_path_to_delete)
                deleted_file = True
                logger.info(f"🗑️ Deleted physical file: {file_path_to_delete}")
            except Exception as e:
                logger.error(f"❌ Failed to delete file {file_path_to_delete}: {e}")
                # We don't rollback DB transaction because the user purpose is to remove it from library primarily

        return {
            "success": True,
            "message": "Source deleted",
            "file_deleted": deleted_file
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete source failed: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")


@router.post("/fix-quality", response_model=FixQualityResponse)
async def fix_quality_internal(db: AsyncSession = Depends(get_async_session)):
    """
    Internal Endpoint: Force fix all local FLAC/WAV quality to SQ
    """
    try:
        from app.services.library import LibraryService
        service = LibraryService()
        updated, logs = await service.force_fix_quality(db)

        if updated > 0:
            return {"success": True, "updated": updated, "details": logs}

        return {"success": True, "updated": 0, "message": "All good"}

    except Exception as e:
        logger.error(f"Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": "操作失败, 请查看日志"}

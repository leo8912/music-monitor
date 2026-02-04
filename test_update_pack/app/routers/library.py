# -*- coding: utf-8 -*-
"""
Library API路由 - 本地资料库管理

Author: google
Updated: 2026-01-26
"""
import logging
import traceback
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import os
from sqlalchemy import select, delete, desc, asc

from core.database import get_async_session
from app.services.library import LibraryService
from app.services.scan_service import ScanService
from app.services.enrichment_service import EnrichmentService
from app.repositories.song import SongRepository
from app.models.song import SongSource
from app.pagination import PaginatedResponse, convert_skip_limit_to_page

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/songs")
async def get_library_songs(
    # 新分页参数 (page, page_size)
    page: Optional[int] = Query(None, ge=1, description="页码,从1开始"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="每页数量"),
    # 旧分页参数 (skip, limit) - 向后兼容
    skip: Optional[int] = Query(None, ge=0, description="[已废弃] 使用 page 代替"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="[已废弃] 使用 page_size 代替"),
    # 其他过滤参数
    artist_name: Optional[str] = Query(None, description="歌手名过滤"),
    is_favorite: Optional[bool] = Query(None, description="收藏过滤"),
    monitored_only: bool = Query(True, description="仅显示关注歌手(默认True)"),
    sort_by: str = Query("publish_time", description="排序字段: publish_time, created_at, title"),
    order: str = Query("desc", description="排序方向: desc, asc"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取本地资料库歌曲
    
    支持两种分页方式:
    1. 新式: page + page_size (推荐)
    2. 旧式: skip + limit (向后兼容,将来会移除)
    """
    try:
        # 处理分页参数 (优先使用新参数)
        if page is not None and page_size is not None:
            # 使用新分页参数
            current_page = page
            current_page_size = page_size
            offset = (page - 1) * page_size
            fetch_limit = page_size
        elif skip is not None and limit is not None:
            # 兼容旧分页参数
            current_page, current_page_size = convert_skip_limit_to_page(skip, limit)
            offset = skip
            fetch_limit = limit
        else:
            # 默认值
            current_page = 1
            current_page_size = 20
            offset = 0
            fetch_limit = 20
        
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取资料库失败: {str(e)}")


@router.post("/match-metadata")
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

@router.get("/local-songs")
async def get_local_songs(
    # 新分页参数
    page: Optional[int] = Query(None, ge=1, description="页码,从1开始"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="每页数量"),
    # 旧分页参数 - 向后兼容
    skip: Optional[int] = Query(None, ge=0, description="[已废弃] 使用 page 代替"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="[已废弃] 使用 page_size 代替"),
    sort_by: str = Query("created_at", description="排序字段: created_at, publish_time, artist, title, album"),
    order: str = Query("desc", description="排序方向: desc, asc"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    专门获取所有本地歌曲 (有 local_path 的歌曲)
    无视是否关注歌手,按入库时间倒序排列
    """
    try:
        from app.models.song import Song, SongSource
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload
        # 处理分页参数
        if page is not None and page_size is not None:
            current_page = page
            current_page_size = page_size
            offset = (page - 1) * page_size
            fetch_limit = page_size
        elif skip is not None and limit is not None:
            current_page, current_page_size = convert_skip_limit_to_page(skip, limit)
            offset = skip
            fetch_limit = limit
        else:
            current_page = 1
            current_page_size = 20
            offset = 0
            fetch_limit = 20
        
        stmt = select(Song).options(
            selectinload(Song.artist),
            selectinload(Song.sources)
        )
        stmt = stmt.where(Song.local_path.isnot(None))
        
        # 排序处理
        order_func = desc if order.lower() == "desc" else asc
        if sort_by == "created_at":
            stmt = stmt.order_by(order_func(Song.created_at))
        elif sort_by == "publish_time":
            stmt = stmt.order_by(order_func(Song.publish_time).nullslast())
        elif sort_by == "artist":
            from app.models.artist import Artist
            stmt = stmt.join(Artist).order_by(order_func(Artist.name))
        elif sort_by == "title":
            stmt = stmt.order_by(order_func(Song.title))
        elif sort_by == "album":
            stmt = stmt.order_by(order_func(Song.album))
        else:
             stmt = stmt.order_by(Song.created_at.desc())
        
        # 分页
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        
        stmt = stmt.offset(offset).limit(fetch_limit)
        
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        # 序列化
        items = []
        for s in songs:
            artist_name = s.artist.name if s.artist else "Unknown"
            status = s.status if s.status else "DOWNLOADED"
            
            # Extract quality and cover from local sources
            quality = None
            local_cover = None
            
            # Define quality priority
            # q_priority = {"HR": 5, "SQ": 4, "HQ": 3, "PQ": 2, "ERR": 1, None: 0}
            q_priority = {"HR": 5, "SQ": 4, "HQ": 3, "PQ": 2, "ERR": 1, None: 0}
            local_files_list = []
            
            for src in s.sources:
                if src.source == 'local':
                    data = src.data_json or {}
                    start_q = quality or 'PQ'
                    new_q = data.get('quality')
                    
                    # Upgrade quality if better
                    if q_priority.get(new_q, 0) > q_priority.get(quality, 0):
                        quality = new_q
                        
                    # Check for local cover
                    # 优先使用 uploads 开头的本地封面
                    src_cover = getattr(src, 'cover', None) or data.get('cover')
                    if src_cover and str(src_cover).startswith('/uploads/'):
                        local_cover = src_cover
                        
                    # Collect file details
                    local_files_list.append({
                        "id": src.id,
                        "source_id": src.source_id,
                        "path": src.url,
                        "quality": new_q or 'PQ',
                        "format": data.get('format', 'UNK')
                    })
            
            # View object construction
            final_cover = local_cover if local_cover else s.cover
            
            items.append({
                "id": s.id,
                "title": s.title,
                "artist": artist_name,
                "album": s.album,
                "cover": final_cover,
                "publish_time": s.publish_time,
                "created_at": s.created_at,
                "source": "local",
                "source_id": s.local_path,
                "local_path": s.local_path,
                "is_favorite": s.is_favorite,
                "status": status,
                "quality": quality,
                "status": status,
                "quality": quality,
                "availableSources": [],
                "localFiles": local_files_list
            })

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=current_page,
            page_size=current_page_size
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取本地音乐失败: {str(e)}")


@router.post("/scan")
async def scan_library(db: AsyncSession = Depends(get_async_session)):
    """扫描本地文件"""
    try:
        scan_service = ScanService()
        result = await scan_service.scan_local_files(db)
        return {"success": True, **result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")


@router.post("/local/enrich")
async def enrich_local_files_endpoint(
    db: AsyncSession = Depends(get_async_session)
):
    """
    补全本地文件元数据 (自动下载封面/专辑/年份)
    触发后台任务
    """
    try:
        from app.services.enrichment_service import EnrichmentService
        # 实例化服务
        service = EnrichmentService()
        # 以后台任务运行，避免阻塞接口
        asyncio.create_task(service.auto_enrich_library())
        return {"success": True, "message": "Enrichment task started"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"补全任务启动失败: {str(e)}")


@router.post("/metadata/refresh")
async def refresh_library_metadata(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session)
):
    """刷新资料库元数据 (仅数据库)"""
    try:
        enrichment_service = EnrichmentService()
        count = await enrichment_service.refresh_library_metadata(db, limit=limit)
        return {"success": True, "enriched_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"资料库刷新失败: {str(e)}")


@router.post("/songs/{song_id}/favorite")
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.delete("/songs/{song_id}")
async def delete_song(
    song_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """删除歌曲"""
    try:
        service = LibraryService()
        success = await service.delete_song(song_id, db)
        if success:
            return {"success": True}
        raise HTTPException(status_code=404, detail="歌曲未找到")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


from pydantic import BaseModel


class RedownloadRequest(BaseModel):
    song_id: int
    source: str
    track_id: str
    quality: int = 999
    title: Optional[str] = None
    artist: Optional[str] = None

@router.post("/redownload")
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"重新下载失败: {str(e)}")


class DownloadFromSearchRequest(BaseModel):
    title: str
    artist: str
    album: Optional[str] = ""
    source: str
    source_id: str
    quality: int = 999
    cover_url: Optional[str] = ""

@router.post("/download")
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

class RefreshRequest(BaseModel):
    artist_name: str

@router.post("/refresh_artist")
async def refresh_artist(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """刷新指定歌手的歌曲"""
    try:
        service = LibraryService()
        count = await service.refresh_artist(db, request.artist_name)
        return {"success": True, "new_songs_count": count}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@router.delete("/artists/{artist_id}")
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.delete("/artists/name/{artist_name}")
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.delete("/source/{source_db_id}")
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
                os.remove(file_path_to_delete)
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
        raise HTTPException(status_code=500, detail=str(e))

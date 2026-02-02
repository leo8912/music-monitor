# -*- coding: utf-8 -*-
"""
FavoriteService - 收藏管理服务

功能：
- 切换歌曲收藏状态
- 移动文件到收藏夹/缓存目录

Author: google
Created: 2026-02-02 (从 LibraryService 拆分)
"""
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import shutil
import logging
import anyio

from app.repositories.song import SongRepository
from app.models.song import Song
from app.utils.error_handler import handle_service_errors

logger = logging.getLogger(__name__)


class FavoriteService:
    """收藏管理服务"""
    
    @handle_service_errors(fallback_value=None, raise_on_critical=False)
    async def toggle(
        self, 
        db: AsyncSession, 
        song_id: int
    ) -> Optional[Dict]:
        """
        切换歌曲的收藏状态。
        
        该方法不仅更新数据库中的 is_favorite 标志，还会根据收藏状态自动移动
        本地音频文件（如果在本地的话）：
        - 收藏: 移动到 'favorites/' 目录
        - 取消收藏: 移动到 'audio_cache/' 目录
        
        Args:
            db (AsyncSession): 异步数据库会话。
            song_id (int): 歌曲在数据库中的唯一标识。
            
        Returns:
            Optional[Dict]: 成功时返回包含新状态信息的字典:
                {
                    "song_id": int,
                    "is_favorite": bool,
                    "new_path": str,  # 新的文件物理路径（如果涉及移动）
                }
                失败或歌曲不存在时返回 None。
                
        Raises:
            ServiceException: 当数据库操作或文件移动发生严重错误时抛出。
        """
        song_repo = SongRepository(db)
        song = await song_repo.toggle_favorite(song_id)
        
        if not song:
            return None
        
        # 如果没有本地文件，只更新状态
        if not song.local_path:
            return {
                "song_id": song.id,
                "is_favorite": song.is_favorite,
                "new_path": None,
                "message": "状态已更新 (无本地文件)"
            }
        
        try:
            old_path = Path(song.local_path).resolve()
            
            # Load config directories
            from core.config_manager import get_config_manager
            storage_cfg = get_config_manager().get("storage", {})
            favorites_dir = Path(storage_cfg.get("favorites_dir", "favorites")).resolve()
            cache_dir = Path(storage_cfg.get("cache_dir", "audio_cache")).resolve()
            library_dir = Path(storage_cfg.get("library_dir", "library")).resolve()
            
            logger.debug(f"Path Check: Old={old_path}, Cache={cache_dir}, Fav={favorites_dir}, Lib={library_dir}")
            
            # 只有当文件存在时才尝试移动
            if await anyio.to_thread.run_sync(old_path.exists):
                
                # Logic: Only move if it is in Cache or Favorites. 
                # Do NOT move if it is in Library.
                
                # Check if file is in library (Static)
                is_in_library = str(old_path).startswith(str(library_dir))
                
                if is_in_library:
                    logger.info(f"Song is in static library ({library_dir}), skipping move.")
                    # Do not move, just return success
                    return {
                        "song_id": song.id,
                        "is_favorite": song.is_favorite,
                        "new_path": song.local_path
                    }

                new_dir = None
                
                if song.is_favorite:
                    # 收藏操作:
                    # 仅当文件在 Cache 目录时，移动到 Favorites
                    if str(old_path).startswith(str(cache_dir)):
                        new_dir = favorites_dir
                    else:
                        logger.info(f"Song not in cache dir ({cache_dir}), skipping move to favorites.")
                else:
                    # 取消收藏操作:
                    # 仅当文件在 Favorites 目录时，移回 Cache
                    if str(old_path).startswith(str(favorites_dir)):
                        new_dir = cache_dir
                    else:
                        logger.info(f"Song not in favorites dir ({favorites_dir}), skipping move back to cache.")

                if new_dir:
                    new_dir.mkdir(parents=True, exist_ok=True)
                    new_path = new_dir / old_path.name
                    
                    # 移动文件
                    if new_path != old_path:
                        logger.info(f"Moving file: {old_path} -> {new_path}")
                        await anyio.to_thread.run_sync(
                            shutil.move, 
                            str(old_path), 
                            str(new_path)
                        )
                        
                        # 更新数据库路径
                        song.local_path = str(new_path)
                        await db.commit()
                        await db.refresh(song)
            else:
                logger.warning(f"File not found: {old_path}")
        
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            # 即使移动失败，收藏状态已变更
        
        return {
            "song_id": song.id,
            "is_favorite": song.is_favorite,
            "new_path": song.local_path
        }
    
    @handle_service_errors(fallback_value=[])
    async def get_favorites(
        self, 
        db: AsyncSession, 
        limit: int = 100
    ) -> list[Song]:
        """
        获取收藏列表
        
        Args:
            db: 数据库会话
            limit: 返回数量限制
            
        Returns:
            收藏歌曲列表
        """
        song_repo = SongRepository(db)
        # 假设 SongRepository 有 get_favorites 方法
        # 如果没有，需要添加
        from sqlalchemy import select
        from app.models.song import Song
        
        stmt = select(Song).where(Song.is_favorite == True).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

# -*- coding: utf-8 -*-
"""
FavoritesService - 收藏管理服务

此模块处理歌曲收藏的添加和移除功能。

Author: google
Updated: 2026-01-26
"""
import os
import shutil
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import config
from app.repositories.media_record import MediaRecordRepository

logger = logging.getLogger(__name__)

# 常量
AUDIO_CACHE_DIR = "audio_cache"
FAVORITES_DIR = "favorites"


class FavoritesService:
    """收藏管理服务"""
    
    @staticmethod
    def get_favorites_dir():
        """获取收藏目录"""
        return config.get('storage', {}).get('favorites_dir', FAVORITES_DIR)

    @staticmethod
    async def toggle_favorite(db: AsyncSession, unique_key: str, force_state: bool = None) -> dict:
        """
        切换收藏状态
        
        Args:
            db: 数据库会话
            unique_key: 歌曲唯一键
            force_state: 强制设置的状态
        
        Returns:
            操作结果字典
        """
        repo = MediaRecordRepository(db)
        record = await repo.get_by_unique_key(unique_key)
        
        if not record:
            return {"success": False, "message": "记录未找到"}

        # 确定新状态
        new_state = not record.is_favorite if force_state is None else force_state
        
        if new_state == record.is_favorite:
            return {"success": True, "state": new_state, "message": "状态未变化"}

        favorites_dir = FavoritesService.get_favorites_dir()
        if not os.path.exists(favorites_dir):
            os.makedirs(favorites_dir)

        if new_state:
            # === 添加到收藏 ===
            if not record.local_audio_path:
                return {"success": False, "message": "歌曲未下载，请先下载"}
            
            # 确定源文件路径
            src_path = record.local_audio_path
            if not os.path.isabs(src_path):
                src_path = os.path.join(AUDIO_CACHE_DIR, record.local_audio_path)
            
            if not os.path.exists(src_path):
                return {"success": False, "message": "源文件不存在"}

            # 复制到收藏目录
            filename = os.path.basename(record.local_audio_path)
            dst_path = os.path.join(favorites_dir, filename)
            
            try:
                shutil.copy2(src_path, dst_path)
                logger.info(f"已复制到收藏: {dst_path}")
            except Exception as e:
                logger.error(f"复制文件失败: {e}")
                return {"success": False, "message": f"文件复制失败: {e}"}
                
            await repo.set_favorite(unique_key, True)
            
        else:
            # === 取消收藏 ===
            if record.local_audio_path:
                filename = os.path.basename(record.local_audio_path)
                fav_path = os.path.join(favorites_dir, filename)
                if os.path.exists(fav_path):
                    try:
                        os.remove(fav_path)
                        logger.info(f"已从收藏移除: {fav_path}")
                    except Exception as e:
                        logger.warning(f"删除收藏文件失败: {e}")
            
            await repo.set_favorite(unique_key, False)

        return {"success": True, "state": new_state}

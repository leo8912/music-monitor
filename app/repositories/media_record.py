# -*- coding: utf-8 -*-
"""
MediaRecordRepository - 媒体记录数据访问层

此文件负责封装 MediaRecord 模型的所有数据库操作，包括：
- 歌曲列表查询（支持分页、过滤、排序）
- 歌曲去重逻辑
- 收藏状态管理
- 统计信息查询

Author: GOOGLE music-monitor development team

更新日志:
- 2026-01-22: 初始创建，从 media.py Router 中提取数据访问逻辑
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from sqlalchemy.orm import selectinload
from datetime import datetime
import json
import logging

from core.database import MediaRecord
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MediaRecordRepository(BaseRepository[MediaRecord]):
    """
    MediaRecord 数据访问仓储
    
    提供对 MediaRecord 表的所有数据库操作封装
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, MediaRecord)
    
    async def get_by_unique_key(self, unique_key: str) -> Optional[MediaRecord]:
        """根据唯一键获取记录"""
        stmt = select(MediaRecord).where(MediaRecord.unique_key == unique_key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_source_and_id(self, source: str, media_id: str) -> Optional[MediaRecord]:
        """根据来源和媒体ID获取记录"""
        unique_key = f"{source}_{media_id}"
        return await self.get_by_unique_key(unique_key)
    
    async def get_songs_paginated(
        self,
        offset: int = 0,
        limit: int = 20,
        author: Optional[str] = None,
        downloaded_only: bool = False,
        order_by_publish_time: bool = True
    ) -> Tuple[List[MediaRecord], int]:
        """
        获取歌曲列表（分页）
        
        Args:
            offset: 偏移量
            limit: 每页数量
            author: 作者过滤（模糊匹配）
            downloaded_only: 仅显示已下载
            order_by_publish_time: 是否按发布时间排序
            
        Returns:
            Tuple[List[MediaRecord], int]: (记录列表, 总数)
        """
        # 构建基础查询
        base_query = select(MediaRecord)
        count_query = select(func.count(MediaRecord.id))
        
        # 应用过滤条件
        if author:
            base_query = base_query.where(MediaRecord.author.ilike(f'%{author}%'))
            count_query = count_query.where(MediaRecord.author.ilike(f'%{author}%'))
        
        if downloaded_only:
            base_query = base_query.where(MediaRecord.local_audio_path.isnot(None))
            count_query = count_query.where(MediaRecord.local_audio_path.isnot(None))
        
        # 排序
        if order_by_publish_time:
            base_query = base_query.order_by(
                desc(MediaRecord.publish_time), 
                desc(MediaRecord.found_at)
            )
        else:
            base_query = base_query.order_by(desc(MediaRecord.found_at))
        
        # 分页
        base_query = base_query.offset(offset).limit(limit)
        
        # 执行查询
        result = await self._session.execute(base_query)
        records = result.scalars().all()
        
        # 计算总数
        count_result = await self._session.execute(count_query)
        total = count_result.scalar()
        
        return records, total
    
    async def get_all_for_dedup(
        self,
        author: Optional[str] = None,
        downloaded_only: bool = False
    ) -> List[MediaRecord]:
        """
        获取所有记录用于去重计算
        
        Args:
            author: 作者过滤
            downloaded_only: 仅已下载
            
        Returns:
            List[MediaRecord]: 记录列表
        """
        query = select(MediaRecord).order_by(
            desc(MediaRecord.publish_time), 
            desc(MediaRecord.found_at)
        )
        
        if author:
            query = query.where(MediaRecord.author.ilike(f'%{author}%'))
        
        if downloaded_only:
            query = query.where(MediaRecord.local_audio_path.isnot(None))
        
        result = await self._session.execute(query)
        return result.scalars().all()
    
    async def update_audio_path(
        self, 
        unique_key: str, 
        local_path: str,
        quality: Optional[int] = None
    ) -> Optional[MediaRecord]:
        """更新音频本地路径"""
        record = await self.get_by_unique_key(unique_key)
        if record:
            record.local_audio_path = local_path
            if quality:
                record.audio_quality = quality
            await self._session.commit()
            await self._session.refresh(record)
        return record
    
    async def toggle_favorite(self, unique_key: str) -> Optional[Dict[str, Any]]:
        """切换收藏状态"""
        record = await self.get_by_unique_key(unique_key)
        if not record:
            return None
        
        record.is_favorite = not record.is_favorite
        await self._session.commit()
        await self._session.refresh(record)
        
        return {
            "is_favorite": record.is_favorite,
            "unique_key": unique_key
        }
    
    async def set_favorite(self, unique_key: str, state: bool) -> Optional[MediaRecord]:
        """设置收藏状态"""
        record = await self.get_by_unique_key(unique_key)
        if record:
            record.is_favorite = state
            await self._session.commit()
            await self._session.refresh(record)
        return record
    
    async def create_or_update(self, data: Dict[str, Any]) -> MediaRecord:
        """
        创建或更新媒体记录
        
        Args:
            data: 包含 unique_key 和其他字段的字典
            
        Returns:
            MediaRecord: 创建或更新后的记录
        """
        unique_key = data.get('unique_key')
        if not unique_key:
            raise ValueError("unique_key is required")
        
        record = await self.get_by_unique_key(unique_key)
        
        if record:
            # 更新现有记录
            for key, value in data.items():
                if key != 'unique_key' and hasattr(record, key):
                    setattr(record, key, value)
            await self._session.commit()
            await self._session.refresh(record)
        else:
            # 创建新记录
            record = MediaRecord(**data)
            self._session.add(record)
            await self._session.commit()
            await self._session.refresh(record)
        
        return record
    
    async def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        # 总歌曲数
        total_query = select(func.count(MediaRecord.id))
        total_result = await self._session.execute(total_query)
        total_songs = total_result.scalar() or 0
        
        # 已下载数
        downloaded_query = select(func.count(MediaRecord.id)).where(
            MediaRecord.local_audio_path.isnot(None)
        )
        downloaded_result = await self._session.execute(downloaded_query)
        downloaded_songs = downloaded_result.scalar() or 0
        
        # 收藏数
        favorites_query = select(func.count(MediaRecord.id)).where(
            MediaRecord.is_favorite == True
        )
        favorites_result = await self._session.execute(favorites_query)
        favorites_count = favorites_result.scalar() or 0
        
        # 按来源统计
        source_query = select(
            MediaRecord.source, 
            func.count(MediaRecord.id)
        ).group_by(MediaRecord.source)
        source_result = await self._session.execute(source_query)
        sources = dict(source_result.all())
        
        return {
            "total_songs": total_songs,
            "downloaded_songs": downloaded_songs,
            "favorites_count": favorites_count,
            "sources": sources
        }

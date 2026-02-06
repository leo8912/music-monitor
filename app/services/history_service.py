# -*- coding: utf-8 -*-
"""
HistoryService - 歌曲历史/列表业务逻辑

此文件负责处理歌曲列表相关的业务逻辑，包括：
- 获取歌曲历史列表（支持分页、过滤）
- 实现歌曲去重逻辑（跨平台合并）
- 格式化输出为前端期望的数据结构

Author: GOOGLE music-monitor development team

更新日志:
- 2026-01-22: 初始创建，从 media.py Router 中提取业务逻辑
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload
import json
import logging
import os

from app.repositories.media_record import MediaRecordRepository
from app.utils.error_handler import handle_service_errors

logger = logging.getLogger(__name__)


class HistoryService:
    """
    歌曲历史/列表服务
    
    提供歌曲列表相关的业务逻辑处理
    """
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
    
    @handle_service_errors(fallback_value={'items': [], 'total': 0}, raise_on_critical=False)
    async def get_history(
        self,
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        author: Optional[str] = None,
        downloaded_only: bool = False
    ) -> Dict[str, Any]:
        """
        获取歌曲历史列表（带去重）
        """
        repo = MediaRecordRepository(db)
        
        # 获取分页数据
        records, _ = await repo.get_songs_paginated(
            offset=offset,
            limit=limit,
            author=author,
            downloaded_only=downloaded_only
        )
        
        # [Revised] 精准批量查询对应的本地 SongSource 记录
        source_map = {}
        if records:
            from app.models.song import Song, SongSource
            
            # 建立精确的 (source, source_id) 组合过滤条件
            filters = []
            for r in records:
                mid = str(r.media_id)
                # [Fix] 如果是本地源，ID 可能包含路径，需提取文件名进行匹配
                if r.source == 'local' and ('/' in mid or '\\' in mid):
                    mid = os.path.basename(mid)
                
                filters.append(and_(
                    SongSource.source == r.source,
                    SongSource.source_id == mid
                ))
            
            if filters:
                sources_stmt = select(SongSource).options(joinedload(SongSource.song)).where(
                    or_(*filters)
                )
                sources_result = await db.execute(sources_stmt)
                for ss in sources_result.scalars().all():
                    # 使用组合键作为映射标识
                    source_key = f"{ss.source}_{ss.source_id}"
                    source_map[source_key] = ss
                    if ss.song:
                        logger.debug(f"[History] Matched {source_key} to Song ID {ss.song.id}")
                    else:
                        logger.warning(f"[History] Matched {source_key} but no song attached")

        # 实现去重逻辑
        unique_items_map = {}
        for record in records:
            unique_key_combo = self._get_dedup_key(record)
            
            # 获取对应的本地来源对象
            mid = str(record.media_id)
            if record.source == 'local' and ('/' in mid or '\\' in mid):
                mid = os.path.basename(mid)
                
            matched_source = source_map.get(f"{record.source}_{mid}")
            
            if unique_key_combo in unique_items_map:
                # 合并平台信息
                self._merge_record(unique_items_map[unique_key_combo], record)
            else:
                # 新增项目
                unique_items_map[unique_key_combo] = self._format_record(record, matched_source)
        
        # 转换为列表并排序
        items = list(unique_items_map.values())        # 排序
        items.sort(
            key=lambda x: x['found_at'] or x['publish_time'] or x['created_at'] or '', 
            reverse=True
        )
        
        # 计算去重后的总数
        all_records = await repo.get_all_for_dedup(
            author=author,
            downloaded_only=downloaded_only
        )
        total_unique = len(set(
            self._get_dedup_key(r) for r in all_records
        ))
        
        return {
            'items': items,
            'total': total_unique
        }
    
    def _get_dedup_key(self, record) -> str:
        """生成去重键"""
        return f"{record.title}_{record.author}_{record.album}".lower()
    
    def _format_record(self, record, matched_source: Any = None) -> Dict[str, Any]:
        """格式化单条记录为前端期望的格式"""
        
        # 优先从本地已入库的 Song 记录中获取路径和音质
        local_path = getattr(record, 'local_audio_path', None)
        quality_val = getattr(record, 'audio_quality', None)
        
        if matched_source:
            # 1. 补全本地路径
            local_song = matched_source.song
            if local_song:
                if not local_path and local_song.local_path:
                    local_path = local_song.local_path
                # 如果本地记录有状态且为 DOWNLOADED，则强制使用该路径
                if local_song.status == 'DOWNLOADED' and local_song.local_path:
                    local_path = local_song.local_path
            
            # 2. 从 SongSource 数据中提取音质
            if not quality_val and matched_source.data_json:
                try:
                    data = matched_source.data_json
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except:
                            data = {}
                    
                    if isinstance(data, dict):
                        quality_val = data.get('quality')
                except Exception as e:
                    logger.debug(f"Failed to extract quality from data_json: {e}")

        # Determine logical quality label
        quality_label = None
        if quality_val:
            try:
                # 支持码率或等级
                if isinstance(quality_val, int):
                    if quality_val >= 999: quality_label = 'SQ' # Hi-Res/SQ
                    elif quality_val >= 320: quality_label = 'HQ'
                    elif quality_val > 0: quality_label = 'HQ' # Assume HQ for other positive values as fallback
                else:
                    kbps = int(quality_val)
                    if kbps >= 900: quality_label = 'SQ'
                    elif kbps >= 320: quality_label = 'HQ'
            except: 
                # 如果是字符串等级
                if str(quality_val).upper() in ['SQ', 'HQ', '11', '10']:
                    quality_label = 'SQ' if str(quality_val).upper() in ['SQ', '11'] else 'HQ'
        
        # Fallback: Infer from file extension if quality is still None
        if not quality_label:
            path_to_check = local_path or getattr(record, 'local_audio_path', '')
            if path_to_check:
                lower_path = path_to_check.lower()
                if any(lower_path.endswith(ext) for ext in ['.flac', '.wav', '.ape']):
                    quality_label = 'SQ'
                elif lower_path.endswith('.mp3'):
                    quality_label = 'HQ' 

        return {
            'id': record.id,
            'unique_key': record.unique_key,
            'source': record.source,
            'media_type': record.media_type,
            'media_id': record.media_id,
            'title': record.title,
            'author': record.author,
            'artist': record.author,  # 兼容前端字段
            'cover': getattr(record, 'cover', None),
            'cover_url': getattr(record, 'cover', None),  # 兼容前端字段
            'url': getattr(record, 'url', None),
            'trial_url': getattr(record, 'trial_url', None),
            'album': getattr(record, 'album', ''),
            'publish_time': record.publish_time.isoformat() if record.publish_time else None,
            'found_at': record.found_at.isoformat() if record.found_at else None,
            'local_path': local_path,
            'is_favorite': getattr(record, 'is_favorite', False),
            'extra_sources': [],  # 初始为空
            'created_at': record.found_at.isoformat() if record.found_at else None,
            'quality': quality_label,
            'status': 'DOWNLOADED' if local_path else 'PENDING'
        }
    
    def _merge_record(self, existing_item: Dict, new_record) -> None:
        """合并重复记录的平台信息"""
        # 合并额外来源
        if existing_item['source'] != new_record.source:
            extra_sources = set()
            if existing_item.get('extra_sources'):
                if isinstance(existing_item['extra_sources'], list):
                    extra_sources.update(existing_item['extra_sources'])
                else:
                    try:
                        parsed = json.loads(existing_item['extra_sources'])
                        if isinstance(parsed, list):
                            extra_sources.update(parsed)
                    except:
                        pass
            
            # 添加新来源（避免重复）
            if new_record.source != existing_item['source']:
                extra_sources.add(new_record.source)
            existing_item['extra_sources'] = list(extra_sources)
        
        # 保持最新的时间戳
        record_time = new_record.found_at.isoformat() if new_record.found_at else None
        if record_time and (not existing_item['found_at'] or record_time > existing_item['found_at']):
            existing_item['found_at'] = record_time
            existing_item['created_at'] = record_time
        
        # 更新最新的发布时间
        record_pub_time = new_record.publish_time.isoformat() if new_record.publish_time else None
        existing_pub_time = existing_item['publish_time']
        if record_pub_time and existing_pub_time and record_pub_time > existing_pub_time:
            existing_item['publish_time'] = record_pub_time
        elif record_pub_time and not existing_pub_time:
            existing_item['publish_time'] = record_pub_time

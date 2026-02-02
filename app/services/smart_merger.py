# -*- coding: utf-8 -*-
"""
SmartMerger - 智能元数据合并决策类

核心功能：
根据"判定逻辑表"智能决策是否应更新字段：
1. 空值或垃圾数据 -> 覆盖
2. 封面画质升级 (< 50KB -> > 200KB) -> 覆盖
3. 歌词升级 (纯文本 -> 时间轴) -> 覆盖
4. 日期修复 (1970/默认值 -> 真实日期) -> 覆盖

Author: google
Created: 2026-02-02
"""
import re
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SongMetadata:
    """标准化的歌曲元数据结构"""
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    cover_url: Optional[str] = None
    cover_size_bytes: int = 0  # 封面大小（字节）
    lyrics: Optional[str] = None
    publish_time: Optional[datetime] = None
    source: str = ""  # 来源: netease/qqmusic/local
    confidence: float = 0.0  # 置信度 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "cover_url": self.cover_url,
            "cover_size_bytes": self.cover_size_bytes,
            "lyrics": self.lyrics,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "source": self.source,
            "confidence": self.confidence
        }


class SmartMerger:
    """
    智能元数据合并决策类
    
    判定规则：
    - 空值/垃圾数据 -> 覆盖
    - 封面升级 (低画质 -> 高画质) -> 覆盖
    - 歌词升级 (无时间轴 -> 有时间轴) -> 覆盖
    - 日期修复 (默认值 -> 真实值) -> 覆盖
    """
    
    # 垃圾数据关键词
    GARBAGE_KEYWORDS = [
        "unknown", "test", "未知", "测试", "none", "null",
        "placeholder", "占位", "default", "默认"
    ]
    
    # 默认/无效日期年份
    INVALID_DATE_YEARS = [1970, 1900, 1]  # Unix epoch, 明显无效
    
    # 封面阈值 (字节)
    MIN_COVER_SIZE_BYTES = 50 * 1024      # 50 KB: 低于此视为低质量
    GOOD_COVER_SIZE_BYTES = 200 * 1024    # 200 KB: 高于此视为高质量
    
    @classmethod
    def is_garbage_value(cls, value: Optional[str]) -> bool:
        """判断是否为垃圾数据"""
        if not value:
            return True
        
        value_lower = value.lower().strip()
        
        # 空字符串
        if not value_lower:
            return True
        
        # 垃圾关键词
        for keyword in cls.GARBAGE_KEYWORDS:
            if keyword in value_lower:
                return True
        
        return False
    
    @classmethod
    def is_invalid_date(cls, dt: Optional[datetime]) -> bool:
        """判断是否为无效日期"""
        if not dt:
            return True
        
        # 无效年份
        if dt.year in cls.INVALID_DATE_YEARS:
            return True
        
        # 默认日期检测 (如 2026-01-01 00:00:00)
        if dt.month == 1 and dt.day == 1 and dt.hour == 0 and dt.minute == 0:
            # 可能是默认值，需要结合年份判断
            # 如果年份 > 当前年份，也视为无效
            current_year = datetime.now().year
            if dt.year > current_year + 1:
                return True
        
        return False
    
    @classmethod
    def has_timed_lyrics(cls, lyrics: Optional[str]) -> bool:
        """判断歌词是否有时间轴 (LRC格式)"""
        if not lyrics:
            return False
        
        # LRC 时间轴格式: [00:00.00] 或 [00:00:00]
        lrc_pattern = r'\[\d{2}:\d{2}[.:]\d{2,3}\]'
        return bool(re.search(lrc_pattern, lyrics))
    
    @classmethod
    def should_update_title(cls, current: Optional[str], new: Optional[str]) -> bool:
        """判断是否应更新标题"""
        if cls.is_garbage_value(current) and not cls.is_garbage_value(new):
            return True
        return False
    
    @classmethod
    def should_update_album(cls, current: Optional[str], new: Optional[str]) -> bool:
        """判断是否应更新专辑"""
        if cls.is_garbage_value(current) and not cls.is_garbage_value(new):
            return True
        return False
    
    @classmethod
    def should_update_cover(
        cls, 
        current_url: Optional[str], 
        current_size: int,
        new_url: Optional[str], 
        new_size: int
    ) -> bool:
        """
        判断是否应更新封面
        
        规则：
        1. 无封面 -> 有封面: 更新
        2. 低画质封面 (< 50KB) + 新封面高画质 (> 200KB): 更新
        3. 当前封面是 placeholder (URL 模式匹配): 更新
        """
        # 无封面 -> 有封面
        if not current_url and new_url:
            return True
        
        # 画质升级
        if current_size < cls.MIN_COVER_SIZE_BYTES and new_size > cls.GOOD_COVER_SIZE_BYTES:
            logger.info(f"封面画质升级: {current_size/1024:.1f}KB -> {new_size/1024:.1f}KB")
            return True
        
        # Placeholder 检测 (URL 包含 "default", "placeholder" 等)
        if current_url:
            current_lower = current_url.lower()
            if any(kw in current_lower for kw in ["default", "placeholder", "nocover"]):
                if new_url and new_url.lower() != current_lower:
                    return True
        
        return False
    
    @classmethod
    def should_update_lyrics(cls, current: Optional[str], new: Optional[str]) -> bool:
        """
        判断是否应更新歌词
        
        规则：
        1. 无歌词 -> 有歌词: 更新
        2. 纯文本 -> 时间轴歌词: 更新
        """
        # 无 -> 有
        if not current and new:
            return True
        
        # 纯文本 -> 时间轴
        if current and new:
            current_has_time = cls.has_timed_lyrics(current)
            new_has_time = cls.has_timed_lyrics(new)
            
            if not current_has_time and new_has_time:
                logger.info("歌词升级: 纯文本 -> 时间轴")
                return True
        
        return False
    
    @classmethod
    def should_update_publish_time(
        cls, 
        current: Optional[datetime], 
        new: Optional[datetime]
    ) -> bool:
        """
        判断是否应更新发布时间
        
        规则：
        1. 无日期 -> 有日期: 更新
        2. 无效日期 -> 有效日期: 更新
        """
        # 无 -> 有
        if not current and new:
            return True
        
        # 无效 -> 有效
        if cls.is_invalid_date(current) and not cls.is_invalid_date(new):
            logger.info(f"日期修复: {current} -> {new}")
            return True
        
        return False
    
    @classmethod
    def merge(
        cls,
        current: SongMetadata,
        new: SongMetadata
    ) -> Dict[str, Any]:
        """
        智能合并元数据，返回需要更新的字段
        
        Args:
            current: 当前本地元数据
            new: 在线获取的新元数据
            
        Returns:
            Dict: 需要更新的字段及其新值
        """
        updates = {}
        
        # 标题
        if cls.should_update_title(current.title, new.title):
            updates["title"] = new.title
        
        # 专辑
        if cls.should_update_album(current.album, new.album):
            updates["album"] = new.album
        
        # 封面
        if cls.should_update_cover(
            current.cover_url, current.cover_size_bytes,
            new.cover_url, new.cover_size_bytes
        ):
            updates["cover"] = new.cover_url
        
        # 歌词
        if cls.should_update_lyrics(current.lyrics, new.lyrics):
            updates["lyrics"] = new.lyrics
        
        # 发布时间
        if cls.should_update_publish_time(current.publish_time, new.publish_time):
            updates["publish_time"] = new.publish_time
        
        return updates

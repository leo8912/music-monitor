from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SongMetadata:
    """标准化的歌曲元数据"""
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    cover_url: Optional[str] = None
    publish_time: Optional[str] = None
    lyrics: Optional[str] = None
    source: str = "unknown"
    confidence: float = 0.0

class SmartMerger:
    """
    智能元数据合并器
    
    策略: Smart Hybrid (智能混合)
    只在数据缺失或显式判定为劣质数据时覆盖。
    """
    
    # 垃圾数据关键词 (黑名单)
    GARBAGE_VALUES = {
        "unknown", "unknown album", "unknown artist", "未知", "无", "none", 
        "test", "default", "1970", "1970-01-01"
    }

    def merge(self, local: SongMetadata, online: SongMetadata) -> SongMetadata:
        """
        合并本地和在线元数据，返回最终结果。
        
        Args:
            local: 本地现有元数据
            online: 在线搜索到的最佳匹配元数据
            
        Returns:
            合并后的新 SongMetadata 对象
        """
        # 创建一个新的对象作为结果，初始值为本地值
        result = SongMetadata(
            title=local.title,
            artist=local.artist,
            album=local.album,
            cover_url=local.cover_url,
            publish_time=local.publish_time,
            lyrics=local.lyrics,
            source="mixed"
        )
        
        # 1. 专辑 (Album)
        if self._should_overwrite(local.album, online.album):
            result.album = online.album
            
        # 2. 封面 (Cover)
        # 简单逻辑: 如果本地没封面，就用在线的
        # TODO: 后续加入图片大小对比逻辑
        if not local.cover_url and online.cover_url:
            result.cover_url = online.cover_url
            
        # 3. 发行时间 (Publish Time)
        if self._should_overwrite(local.publish_time, online.publish_time):
             result.publish_time = online.publish_time

        # 4. 歌词 (Lyrics)
        # 如果本地没歌词，用在线的
        if not local.lyrics and online.lyrics:
            result.lyrics = online.lyrics
            
        return result

    def _should_overwrite(self, local_val: Optional[str], online_val: Optional[str]) -> bool:
        """判断是否应该覆盖字段"""
        if not online_val:
            return False
            
        # 1. 如果本地为空，且在线有值 -> 覆盖
        if not local_val:
            return True
            
        # 2. 如果本地是垃圾数据 -> 覆盖
        if self._is_garbage(local_val):
            return True
            
        # 3. 否则保留本地 (保守策略)
        return False

    def _is_garbage(self, value: str) -> bool:
        """检查值是否为垃圾数据"""
        if not value: return True
        return str(value).strip().lower() in self.GARBAGE_VALUES

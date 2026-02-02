"""
音乐源提供者基类

定义统一的抽象接口,所有音乐源提供者必须实现这些接口。

Author: google
Created: 2026-01-23
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TypeVar, Callable, Any
from dataclasses import dataclass, field
import asyncio
import logging
import functools

logger = logging.getLogger(__name__)

def async_retry(max_retries: int = 3, delay: float = 1.0):
    """
    异步函数重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔(秒)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait = delay * (2 ** attempt)  # 指数退避
                        logger.warning(f"Call {func.__name__} failed: {e}. Retrying in {wait:.1f}s ({attempt+1}/{max_retries})")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"Call {func.__name__} failed after {max_retries} retries: {e}")
            
            # 如果重试耗尽, 抛出最后的异常或返回空结果(取决于具体函数的容错设计)
            # 这里我们选择抛出异常, 由上层处理
            raise last_exception
            
        return wrapper
    return decorator


@dataclass
class ArtistInfo:
    """歌手信息"""
    name: str
    source: str  # 'netease' | 'qqmusic'
    id: str
    avatar: str
    song_count: int = 0
    extra_ids: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'source': self.source,
            'id': self.id,
            'avatar': self.avatar,
            'songCount': self.song_count,
            'extra_ids': self.extra_ids
        }


@dataclass
class SongInfo:
    """歌曲信息"""
    title: str
    artist: str
    album: str
    source: str
    id: str
    cover_url: str = ""
    duration: int = 0  # 秒
    publish_time: str = ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'source': self.source,
            'id': self.id,
            'cover_url': self.cover_url,
            'duration': self.duration,
            'publish_time': self.publish_time
        }


class MusicProvider(ABC):
    """
    音乐源提供者基类
    
    所有方法都是异步的,以支持聚合器的并发调用。
    对于底层同步API,实现类需要使用 asyncio.run_in_executor 包装。
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """源名称"""
        pass
    
    @abstractmethod
    async def search_artist(self, keyword: str, limit: int = 10) -> List[ArtistInfo]:
        """
        搜索歌手
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            歌手信息列表
        """
        pass
        
    @abstractmethod
    async def search_song(self, keyword: str, limit: int = 10) -> List[SongInfo]:
        """
        搜索歌曲
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            歌曲信息列表
        """
        pass
    
    @abstractmethod
    async def get_artist_songs(
        self, 
        artist_id: str, 
        offset: int = 0, 
        limit: int = 50
    ) -> List[SongInfo]:
        """
        获取歌手歌曲列表
        
        Args:
            artist_id: 歌手ID
            offset: 偏移量
            limit: 返回结果数量限制
            
        Returns:
            歌曲信息列表
        """
        pass
    
    @abstractmethod
    async def get_song_metadata(self, song_id: str) -> Optional[Dict]:
        """
        获取歌曲元数据(封面、歌词、专辑等)
        
        Args:
            song_id: 歌曲ID
            
        Returns:
            元数据字典,包含 lyrics, cover_url, album 等字段
        """
        pass

    async def get_lyrics(self, song_id: str) -> Optional[str]:
        """
        获取歌词 (MetadataService 插件接口要求)
        
        默认实现: 调用 get_song_metadata 并提取 lyrics 字段
        
        Args:
            song_id: 歌曲ID
            
        Returns:
            Optional[str]: 歌词内容
        """
        try:
            metadata = await self.get_song_metadata(song_id)
            if metadata and 'lyrics' in metadata:
                return metadata['lyrics']
            return None
        except Exception as e:
            logger.error(f"Error getting lyrics from {self.source_name}: {e}")
            return None

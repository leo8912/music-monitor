"""
网易云音乐提供者

使用 pyncm 库(同步API)
通过 asyncio.run_in_executor 包装成异步接口

Author: google
Created: 2026-01-23
"""

from .base import MusicProvider, ArtistInfo, SongInfo, async_retry
from typing import List, Optional, Dict
import asyncio
from functools import partial
import logging

logger = logging.getLogger(__name__)


class NeteaseProvider(MusicProvider):
    """
    网易云音乐提供者
    
    使用 pyncm 库(同步API)
    通过 asyncio.run_in_executor 包装成异步接口
    """
    
    @property
    def source_name(self) -> str:
        return "netease"
    
    @async_retry(max_retries=3)
    async def search_artist(self, keyword: str, limit: int = 10) -> List[ArtistInfo]:
        """
        搜索歌手
        
        pyncm是同步API,在线程池中运行以避免阻塞事件循环
        """
        try:
            from pyncm import apis
            
            # 在线程池中运行同步API
            loop = asyncio.get_event_loop()
            search_result = await loop.run_in_executor(
                None, 
                partial(apis.cloudsearch.GetSearchResult, keyword, stype=100, limit=limit)
            )
            
            results = []
            if search_result and 'result' in search_result and 'artists' in search_result['result']:
                for artist in search_result['result']['artists']:
                    # Relaxed check: Accept if candidate contains keyword (ignoring case/spaces)
                    # or if keyword is reasonably similar.
                    name = artist.get('name', '')
                    cleaned_name = name.lower().replace(' ', '')
                    cleaned_keyword = keyword.lower().replace(' ', '')
                    
                    if cleaned_keyword in cleaned_name or cleaned_name in cleaned_keyword:
                        results.append(ArtistInfo(
                            name=name,
                            source=self.source_name,
                            id=str(artist.get('id', '')),
                            avatar=artist.get('picUrl') or artist.get('img1v1Url', ''),
                            song_count=artist.get('musicSize', 0)
                        ))
            
            logger.info(f"☁️ 网易云搜索歌手: 找到 {len(results)} 条结果 - '{keyword}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ 网易云搜索歌手失败: {e}")
            return []
            
    @async_retry(max_retries=3)
    async def search_song(self, keyword: str, limit: int = 10) -> List[SongInfo]:
        """搜索歌曲"""
        try:
            from pyncm import apis
            
            loop = asyncio.get_event_loop()
            search_result = await loop.run_in_executor(
                None, 
                partial(apis.cloudsearch.GetSearchResult, keyword, stype=1, limit=limit)
            )
            
            results = []
            if search_result and 'result' in search_result and 'songs' in search_result['result']:
                for song in search_result['result']['songs']:
                    results.append(SongInfo(
                        title=song.get('name', ''),
                        artist=song['ar'][0]['name'] if song.get('ar') else '',
                        album=song['al']['name'] if song.get('al') else '',
                        source=self.source_name,
                        id=str(song.get('id', '')),
                        cover_url=song['al'].get('picUrl', '') if song.get('al') else '',
                        duration=song.get('dt', 0) // 1000,
                        publish_time=str(song.get('publishTime', ''))
                    ))
                    
            logger.info(f"☁️ 网易云搜索歌曲: 找到 {len(results)} 条结果 - '{keyword}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ 网易云搜索歌曲失败: {e}")
            return []
    
    @async_retry(max_retries=3)
    async def get_artist_songs(
        self, 
        artist_id: str, 
        offset: int = 0, 
        limit: int = 1000
    ) -> List[SongInfo]:
        """获取歌手歌曲列表"""
        try:
            from pyncm import apis
            
            loop = asyncio.get_event_loop()
            tracks = await loop.run_in_executor(
                None,
                partial(apis.artist.GetArtistTracks, artist_id)
            )
            
            results = []
            if tracks and 'songs' in tracks:
                for song in tracks['songs'][offset:offset+limit]:
                    # 兼容不同的歌手字段名 (ar 或 artists)
                    artist_name = ''
                    if song.get('ar'):
                        artist_name = song['ar'][0]['name']
                    elif song.get('artists'):
                        artist_name = song['artists'][0]['name']
                    else:
                        logger.warning(f"Netease song missing artist info. Keys: {list(song.keys())}")

                    results.append(SongInfo(
                        title=song.get('name', ''),
                        artist=artist_name,
                        album=song['al']['name'] if song.get('al') else '',
                        source=self.source_name,
                        id=str(song.get('id', '')),
                        cover_url=song['al'].get('picUrl', '') if song.get('al') else '',
                        duration=song.get('dt', 0) // 1000,
                        publish_time=str(song.get('publishTime', ''))
                    ))
            
            logger.info(f"☁️ 网易云获取歌手热歌: 取回 {len(results)} 首 - ID:{artist_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ 网易云获取歌手热歌失败: {e}")
            return []
    
    async def get_song_metadata(self, song_id: str) -> Optional[Dict]:
        """获取歌曲元数据"""
        try:
            from pyncm import apis
            
            loop = asyncio.get_event_loop()
            
            # 获取歌词
            lyrics_info = await loop.run_in_executor(
                None,
                partial(apis.track.GetTrackLyrics, song_id)
            )
            
            # 获取详情
            detail = await loop.run_in_executor(
                None,
                partial(apis.track.GetTrackDetail, [song_id])
            )
            
            metadata = {
                'lyrics': lyrics_info.get('lrc', {}).get('lyric', '') if lyrics_info else '',
                'cover_url': '',
                'album': ''
            }
            
            if detail and detail.get('songs'):
                song = detail['songs'][0]
                if song.get('al'):
                    metadata['cover_url'] = song['al'].get('picUrl', '')
                    metadata['album'] = song['al'].get('name', '')
                metadata['publish_time'] = str(song.get('publishTime', ''))
            
            logger.info(f"☁️ 网易云详情获取成功: {song_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Netease get_song_metadata failed: {e}")
            return None

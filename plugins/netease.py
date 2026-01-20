from typing import List
from datetime import datetime
import logging
import pyncm.apis as apis
from domain.models import MediaInfo, MediaType
from plugins.base import MonitorPlugin
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

class NeteaseMonitor(MonitorPlugin):
    @property
    def source_name(self) -> str:
        return "netease"

    async def get_new_content(self, user_id: str, user_name: str = "") -> List[MediaInfo]:
        """
        Get latest songs for the artist (热门歌曲50首).
        Changed from albums to songs for consistency with QQ Music.
        """
        logger.info(f"正在获取网易云歌曲: {user_name} ({user_id})")
        results = []
        
        try:
            # 获取歌手热门歌曲 (Top 500 songs)
            data = await run_in_threadpool(apis.artist.GetArtistSongs, user_id, limit=500)
            
            if data.get('code') != 200:
                logger.error(f"网易云 API 错误: {data}")
                return []

            songs = data.get('songs', [])
            logger.info(f"网易云返回 {len(songs)} 首歌曲")
            
            for song in songs:
                # publishTime is in milliseconds
                pub_ts = song.get('publishTime', 0)
                if not pub_ts:
                    # Fallback to album publish time
                    pub_ts = song.get('album', {}).get('publishTime', 0)
                
                pub_date = datetime.fromtimestamp(pub_ts / 1000) if pub_ts else datetime.now()
                
                # Get album cover
                album_data = song.get('album', {})
                cover_url = album_data.get('picUrl', '')
                
                # Get artists
                artists = song.get('ar', [])
                artist_name = user_name
                if artists and len(artists) > 0:
                    artist_name = artists[0].get('name', user_name)
                
                info = MediaInfo(
                    id=str(song.get('id')),
                    title=song.get('name'),
                    cover_url=cover_url,
                    url=f"https://music.163.com/#/song?id={song.get('id')}",
                    publish_time=pub_date,
                    type=MediaType.SONG,  # Changed from ALBUM to SONG
                    author=artist_name,
                    album=album_data.get('name', ''),
                    source=self.source_name
                )
                results.append(info)
                
        except Exception as e:
            logger.error(f"网易云数据获取失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        logger.info(f"网易云获取完成: {user_name} 共 {len(results)} 首歌曲")
        return results

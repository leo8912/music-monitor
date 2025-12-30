from typing import List
from datetime import datetime
import logging
import pyncm.apis as apis
from domain.models import MediaInfo, MediaType
from plugins.base import MonitorPlugin

logger = logging.getLogger(__name__)

class NeteaseMonitor(MonitorPlugin):
    @property
    def source_name(self) -> str:
        return "netease"

    async def get_new_content(self, user_id: str, user_name: str = "") -> List[MediaInfo]:
        """
        Get latest albums for the artist.
        pyncm usually works synchronously, so we wraps it if needed, 
        but for simplicity in MVP we might run it directly or in executor if it blocks.
        """
        logger.info(f"正在获取网易云专辑: {user_name} ({user_id})")
        results = []
        
        try:
            # Get top 5 albums. Limit is enough for "new content" check.
            # Response format: {'code': 200, 'artist': {...}, 'hotAlbums': [...]}
            import asyncio
            loop = asyncio.get_running_loop()
            # Run blocking call in thread pool
            data = await loop.run_in_executor(None, lambda: apis.artist.GetArtistAlbums(user_id, limit=5))
            
            if data.get('code') != 200:
                logger.error(f"网易云 API 错误: {data}")
                return []

            albums = data.get('hotAlbums', [])
            for album in albums:
                # publishTime is in milliseconds
                pub_ts = album.get('publishTime', 0)
                pub_date = datetime.fromtimestamp(pub_ts / 1000)
                
                info = MediaInfo(
                    id=str(album.get('id')),
                    title=album.get('name'),
                    cover_url=album.get('picUrl'),
                    url=f"https://music.163.com/#/album?id={album.get('id')}",
                    publish_time=pub_date,
                    type=MediaType.ALBUM,
                    author=album.get('artist', {}).get('name', 'Unknown'),
                    album=album.get('name'), # For Album type, title is album name
                    source=self.source_name
                )
                results.append(info)
                
        except Exception as e:
            logger.error(f"网易云数据获取失败: {e}")
            
        return results

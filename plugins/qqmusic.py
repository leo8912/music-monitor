from typing import List
from datetime import datetime
import logging
from qqmusic_api import search, singer
from domain.models import MediaInfo, MediaType
from plugins.base import MonitorPlugin

logger = logging.getLogger(__name__)

class QQMusicMonitor(MonitorPlugin):
    @property
    def source_name(self) -> str:
        return "qqmusic"

    async def get_new_content(self, user_id: str, user_name: str = "") -> List[MediaInfo]:
        """
        Get latest content for the artist.
        user_id for QQMusic is usually 'mid' (e.g., 0025NhlN2yWrP4).
        """
        logger.info(f"正在获取 QQ 音乐数据: {user_name} ({user_id})")
        results = []
        
        try:
            # Retrieve songs
            data = await singer.get_songs(user_id, num=10)
            
            song_list = []
            if isinstance(data, list):
                song_list = data
            elif isinstance(data, dict):
                song_list = data.get('list', [])
            
            for song in song_list:
                # 'time_public' is often YYYY-MM-DD
                pub_time_str = song.get('time_public', '')
                try:
                    pub_date = datetime.strptime(pub_time_str, "%Y-%m-%d")
                except ValueError:
                    # Fallback or ignore
                    pub_date = datetime.now() 
                
                mid = song.get('mid')
                
                info = MediaInfo(
                    id=mid,
                    title=song.get('name'),
                    cover_url=f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{song.get('album', {}).get('mid')}.jpg", # approximate cover
                    url=f"https://y.qq.com/n/ryqq/songDetail/{mid}",
                    publish_time=pub_date,
                    type=MediaType.SONG,
                    author=song.get('singer', [{}])[0].get('name', 'Unknown'),
                    album=song.get('album', {}).get('name'),
                    source=self.source_name
                )
                results.append(info)
                
        except Exception as e:
            logger.error(f"QQ 音乐数据获取失败: {e}")
            
        return results

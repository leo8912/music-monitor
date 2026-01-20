from typing import List
from datetime import datetime
import logging
import aiohttp
from qqmusic_api import singer
from domain.models import MediaInfo, MediaType
from plugins.base import MonitorPlugin

logger = logging.getLogger(__name__)

class QQMusicMonitor(MonitorPlugin):
    @property
    def source_name(self) -> str:
        return "qqmusic"

    async def _fetch_cover_from_gdstudio(self, song_name: str, artist_name: str) -> str:
        """使用gdstudio API获取封面URL作为备用数据源"""
        try:
            # 使用gdstudio API搜索歌曲
            keyword = f"{song_name} {artist_name}"
            url = f"https://music-api.gdstudio.xyz/api.php?types=search&source=tencent&name={keyword}&count=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and len(data) > 0:
                            pic_id = data[0].get('pic_id')
                            if pic_id:
                                # 获取封面URL
                                pic_url = f"https://music-api.gdstudio.xyz/api.php?types=pic&source=tencent&id={pic_id}&size=500"
                                return pic_url
        except Exception as e:
            logger.debug(f"gdstudio API获取封面失败: {e}")
        
        return ''

    async def get_new_content(self, user_id: str, user_name: str = "") -> List[MediaInfo]:
        """
        Get latest content for the artist.
        使用qqmusic_api库获取歌手的所有歌曲，使用gdstudio API作为备用补充封面
        user_id for QQMusic is usually 'mid' (e.g., 0025NhlN2yWrP4).
        """
        logger.info(f"正在获取 QQ 音乐数据: {user_name} ({user_id})")
        results = []
        
        try:
            # 使用qqmusic_api库获取歌曲列表 (最多500首)
            data = await singer.get_songs(user_id, num=500)
            
            song_list = []
            if isinstance(data, list):
                song_list = data
            elif isinstance(data, dict):
                song_list = data.get('list', [])
            
            logger.info(f"qqmusic_api返回 {len(song_list)} 首歌曲")
            
            for song in song_list:
                # 解析发布时间
                pub_time_str = song.get('time_public', '')
                pub_date = None
                
                if pub_time_str and pub_time_str.strip():  # 确保不是空字符串
                    try:
                        # 尝试多种日期格式
                        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                            try:
                                pub_date = datetime.strptime(pub_time_str, fmt)
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.debug(f"日期解析失败 '{pub_time_str}': {e}")
                
                # 如果没有日期，使用当前时间作为回退
                if not pub_date:
                    pub_date = datetime.now()
                
                mid = song.get('mid')
                if not mid:
                    logger.debug(f"跳过无MID的歌曲: {song.get('name')}")
                    continue
                
                song_name = song.get('name', '')
                
                # 获取专辑信息用于构造封面
                album_data = song.get('album', {})
                album_mid = album_data.get('mid', '') if isinstance(album_data, dict) else ''
                album_name = album_data.get('name', '') if isinstance(album_data, dict) else ''
                
                # 构造封面URL
                cover_url = ''
                if album_mid:
                    cover_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg"
                
                # 如果主要方法没有封面，使用gdstudio API作为备用
                if not cover_url:
                    singer_name = user_name or 'Unknown'
                    if song.get('singer') and len(song.get('singer', [])) > 0:
                        if isinstance(song['singer'][0], dict):
                            singer_name = song['singer'][0].get('name', user_name or 'Unknown')
                    
                    cover_url = await self._fetch_cover_from_gdstudio(song_name, singer_name)
                
                # 获取歌手名
                singer_data = song.get('singer', [])
                singer_name = user_name or 'Unknown'
                if singer_data and len(singer_data) > 0:
                    if isinstance(singer_data[0], dict):
                        singer_name = singer_data[0].get('name', user_name or 'Unknown')
                
                info = MediaInfo(
                    id=mid,
                    title=song_name,
                    cover_url=cover_url,
                    url=f"https://y.qq.com/n/ryqq/songDetail/{mid}",
                    publish_time=pub_date,
                    type=MediaType.SONG,
                    author=singer_name,
                    album=album_name,
                    source=self.source_name
                )
                results.append(info)
                
        except Exception as e:
            logger.error(f"QQ 音乐数据获取失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        logger.info(f"QQ音乐获取完成: {user_name} 共 {len(results)} 首歌曲")
        return results

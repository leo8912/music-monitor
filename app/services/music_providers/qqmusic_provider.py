"""
QQ音乐提供者

使用 qqmusic-api 库(混合API: 搜索和获取歌曲是异步,详情和歌词是同步)

更新日志:
- 2026-02-10: 增加重试次数至5次

Author: ali
Created: 2026-01-23
"""

from .base import MusicProvider, ArtistInfo, SongInfo, async_retry
from typing import List, Optional, Dict
import logging
import base64
import json

logger = logging.getLogger(__name__)


class QQMusicProvider(MusicProvider):
    """
    QQ音乐提供者

    使用 qqmusic-api 库(混合API)
    - search.search_by_type: 异步,直接 await
    - singer.get_songs: 异步,直接 await
    - song.query_song: Coroutine,直接 await
    - lyric.get_lyric: Coroutine,直接 await
    """

    @property
    def source_name(self) -> str:
        return "qqmusic"

    @async_retry(max_retries=5)
    async def search_artist(self, keyword: str, limit: int = 10) -> List[ArtistInfo]:
        """
        搜索歌手

        qqmusic-api 的 search.search_by_type 是异步的,直接 await
        """
        try:
            from qqmusic_api import search
            from qqmusic_api.search import SearchType

            # 直接 await (已经是异步)
            # 补丁: 允许 2001 错误码 (API 返回 code=2001 但可能有数据)
            if 2001 not in search.search_by_type.catch_error_code:
                search.search_by_type.catch_error_code.append(2001)

            qq_results = await search.search_by_type(
                keyword,
                search_type=SearchType.SINGER,
                num=limit
            )



            logger.info(f"🎵 QQMusic 原始返回数据: {len(qq_results) if qq_results else 0} 条")

            results = []
            if qq_results and isinstance(qq_results, list):
                for artist in qq_results:
                    singer_name = artist.get('singerName', '')
                    if keyword.lower() in singer_name.lower():
                        singer_mid = artist.get('singerMID', '')
                        results.append(ArtistInfo(
                            name=singer_name,
                            source=self.source_name,
                            id=singer_mid,
                            avatar=f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{singer_mid}.jpg" if singer_mid else "",
                            song_count=artist.get('songNum', 0)
                        ))

            logger.info(f"🐧 QQMusic 搜索歌手: 找到 {len(results)} 条结果 - '{keyword}'")

            # Fallback: If no artists found via SINGER search (likely due to 2001 error / auth issues),
            # try searching for songs and extract artist info.
            if not results:
                logger.info("⚠️ QQMusic 歌手搜索无结果，降级尝试歌曲搜索...")
                song_results = await self.search_song(keyword, limit=limit)

                seen_ids = set()
                for song in song_results:
                    # search_song returns SongInfo.
                    # But wait, SongInfo doesn't have artist_id easily accessible?
                    # SongInfo has `artist` (name) but not ID.
                    # We need to access the raw data or modify search_song to return IDs,
                    # OR just call the internal API again here.
                    pass # Placeholder

                # Better to call the raw API here to get full details
                qq_song_results = await search.search_by_type(
                    keyword,
                    search_type=SearchType.SONG,
                    num=limit
                )

                if qq_song_results and isinstance(qq_song_results, list):
                     for song in qq_song_results:
                        singers = song.get('singer', [])
                        for s in singers:
                            s_name = s.get('name', '')
                            s_mid = s.get('mid', '')

                            # Check if matches keyword
                            if keyword.lower() in s_name.lower() and s_mid not in seen_ids:
                                seen_ids.add(s_mid)
                                results.append(ArtistInfo(
                                    name=s_name,
                                    source=self.source_name,
                                    id=s_mid,
                                    avatar=f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{s_mid}.jpg" if s_mid else "",
                                    song_count=0 # Cannot get accurate count from song search
                                ))

            logger.info(f"🐧 QQMusic 搜索歌手(降级): 找到 {len(results)} 条结果 - '{keyword}'")
            return results

        except Exception as e:
            logger.error(f"❌ QQMusic 搜索歌手失败: {e}")
            return []

    @async_retry(max_retries=5)
    async def search_song(self, keyword: str, limit: int = 10) -> List[SongInfo]:
        """搜索歌曲 (这也是无需cookie获取元数据的关键方法)"""
        from qqmusic_api import search
        from qqmusic_api.search import SearchType

        # 补丁: 允许 2001 错误码
        if 2001 not in search.search_by_type.catch_error_code:
            search.search_by_type.catch_error_code.append(2001)

        qq_results = await search.search_by_type(
            keyword,
            search_type=SearchType.SONG,
            num=limit
        )

        results = []
        if qq_results and isinstance(qq_results, list):
            for song in qq_results:
                album_mid = song.get('album', {}).get('mid', '') if isinstance(song.get('album'), dict) else ''
                artists = song.get('singer', [])
                artist_name = artists[0]['name'] if artists else ''
                title = song.get('title', '')

                # --- 噪声过滤逻辑 ---
                if title.startswith('#'):
                    logger.info(f"🧹 过滤噪声数据: {title}")
                    continue

                results.append(SongInfo(
                    title=title,
                    artist=artist_name,
                    album=song.get('album', {}).get('name', '') if isinstance(song.get('album'), dict) else '',
                    source=self.source_name,
                    id=song.get('mid', ''), # 使用 mid
                    cover_url=f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg" if album_mid and album_mid != '00000000000000' else "",
                    duration=song.get('interval', 0),
                    publish_time=song.get('time_public', '')
                ))

        logger.info(f"🐧 QQMusic 搜索歌曲: 找到 {len(results)} 条结果 - '{keyword}'")
        return results

    @async_retry(max_retries=5)
    async def get_artist_songs(
        self,
        artist_id: str,
        offset: int = 0,
        limit: int = 1000
    ) -> List[SongInfo]:
        """
        获取歌手歌曲列表

        qqmusic-api 的 singer.get_songs 是异步的,直接 await
        """
        try:
            from qqmusic_api import singer

            # 补丁: 允许 2001 错误码
            if 2001 not in singer.get_tab_detail.catch_error_code:
                singer.get_tab_detail.catch_error_code.append(2001)

            # 直接 await (已经是异步)
            data = await singer.get_songs(artist_id, num=limit)

            songs = []
            song_list = []

            if isinstance(data, list):
                song_list = data
            elif isinstance(data, dict):
                song_list = data.get('songList', [])

            for song in song_list:
                try:
                    title = song.get('title') or song.get('name', 'Unknown')
                    mid = song.get('mid') or str(song.get('id', ''))

                    album_obj = song.get('album')
                    album_name = ''
                    album_mid = ''
                    if isinstance(album_obj, dict):
                        album_name = album_obj.get('name', '')
                        album_mid = album_obj.get('mid', '')

                    artists = song.get('singer', [])
                    artist_name = artists[0].get('name', '') if artists else ''

                    # --- 噪声过滤逻辑 ---
                    # 1. 过滤标题以 # 开头的动态/巡演信息
                    # --- 噪声过滤逻辑 ---
                    # 1. 过滤标题以 # 开头的动态/巡演信息
                    if title.startswith('#'):
                        logger.info(f"🧹 过滤噪声(动态): {title}")
                        continue

                    # 2. 过滤无专辑名且标题异常长的项 (通常是动态描述)
                    if not album_name and len(title) > 50:
                        logger.info(f"🧹 过滤噪声(长标题无专辑): {title[:30]}...")
                        continue

                    songs.append(SongInfo(
                        title=title,
                        artist=artist_name,
                        album=album_name,
                        source=self.source_name,
                        id=mid,
                        cover_url=f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg" if album_mid and album_mid != '00000000000000' else "",
                        duration=song.get('interval', 0),
                        publish_time=song.get('time_public', '')
                    ))
                except Exception as e:
                    logger.warning(f"⚠️ 解析歌曲项出错: {e}")
                    continue

            logger.info(f"🐧 QQMusic 获取歌手热歌: 取回 {len(songs)} 首 - ID:{artist_id}")
            return songs

        except Exception as e:
            logger.error(f"❌ QQMusic 获取歌手热歌失败: {e}")
            return []

    async def get_song_metadata(self, song_id: str) -> Optional[Dict]:
        """
        获取歌曲元数据

        策略:
        1. 尝试直接获取歌词 (lyric.get_lyric)
        2. 使用搜索API获取专辑和封面信息 (因为 song.query_song 需要 cookie)
        """
        try:
            from qqmusic_api import song, lyric

            metadata = {
                'lyrics': '',
                'cover_url': '',
                'album': ''
            }

            # 1. 尝试获取歌词
            # 优先尝试 qqmusic-api (需Cookie), 失败则尝试 Legacy API (无需Cookie)
            try:
                lyric_data = await lyric.get_lyric(song_id)
                if isinstance(lyric_data, dict):
                    metadata['lyrics'] = lyric_data.get('lyric', '')
                elif isinstance(lyric_data, str):
                    metadata['lyrics'] = lyric_data
            except Exception:
                # 尝试旧版接口
                try:
                    metadata['lyrics'] = await self._get_lyric_legacy(song_id)
                except Exception as e:
                    logger.debug(f"Legacy lyric fetch failed: {e}")
                    pass

            # 2. 使用搜索作为元数据来源 (无需cookie)
            try:
                # 尝试 query_song, 即使它报错, 万一用户配了 cookie 呢?
                detail = await song.query_song(song_id)
                if detail:
                    metadata['cover_url'] = detail.get('cover', '')
                    if detail.get('album'):
                        metadata['album'] = detail['album'].get('name', '')
                    metadata['publish_time'] = detail.get('time_public', '')
            except Exception:
                pass

            return metadata

        except Exception as e:
            logger.error(f"❌ QQMusic 获取元数据失败: {e}")
            return None

    async def _get_lyric_legacy(self, song_mid: str) -> str:
        """
        使用旧版接口获取歌词 (无需 Cookie)
        URL: https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg
        """
        import aiohttp

        headers = {
            "Referer": "https://y.qq.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        params = {
            "songmid": song_mid,
            "g_tk": "5381",
            "loginUin": "0",
            "hostUin": "0",
            "format": "json",
            "inCharset": "utf8",
            "outCharset": "utf-8",
            "notice": "0",
            "platform": "yqq.json",
            "needNewCode": "0"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                text = await resp.text()
                data = json.loads(text)

                if 'lyric' in data:
                    return base64.b64decode(data['lyric']).decode('utf-8')
                return ""

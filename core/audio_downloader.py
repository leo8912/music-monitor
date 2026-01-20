"""
音频下载服务模块
使用 GD Studio API 下载音频文件到本地，并自动注入元数据
"""
import asyncio
import aiohttp
import aiofiles
import os
import re
import time
import logging
import io
from typing import Optional, Dict, List, Callable, Awaitable
from dataclasses import dataclass

# 引入 mutagen 处理音频标签
from mutagen.mp3 import MP3, EasyMP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, USLT
from mutagen.flac import FLAC, Picture
from mutagen.easyid3 import EasyID3

logger = logging.getLogger(__name__)

# 音频缓存目录
AUDIO_CACHE_DIR = "audio_cache"


class RateLimiter:
    """
    令牌桶限流器
    GD Studio API 限制: 5分钟内最多50次请求
    """
    def __init__(self, max_tokens: int = 50, refill_period: int = 300):
        self.max_tokens = max_tokens
        self.refill_period = refill_period  # 秒
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, wait: bool = True) -> bool:
        """获取一个令牌"""
        async with self._lock:
            self._refill()
            
            if self.tokens > 0:
                self.tokens -= 1
                return True
            
            if not wait:
                return False
            
        # 等待令牌恢复
        wait_time = self.refill_period - (time.time() - self.last_refill)
        if wait_time > 0:
            logger.info(f"令牌不足,等待 {wait_time:.1f} 秒...")
            await asyncio.sleep(wait_time)
            return await self.acquire(wait=False)
        
        return False
    
    def _refill(self):
        """检查并补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed >= self.refill_period:
            self.tokens = self.max_tokens
            self.last_refill = now


@dataclass
class AudioInfo:
    """音频信息"""
    url: str
    quality: int  # kbps
    size: int  # bytes
    format: str  # mp3/flac

@dataclass
class AudioMetadata:
    """音频元数据"""
    title: str
    artist: list[str]
    album: str
    cover_url: Optional[str] = None
    cover_data: Optional[bytes] = None
    lyric: Optional[str] = None  # 歌词内容(LRC格式)


class AudioDownloader:
    """
    音频下载服务
    使用 GD Studio API 获取音频链接并下载到本地
    """
    
    API_BASE = "https://music-api.gdstudio.xyz/api.php"
    
    # 音乐源映射
    SOURCE_MAP = {
        "netease": "netease",
        "qqmusic": "tencent", 
    }
    
    def __init__(self, cache_dir: str = AUDIO_CACHE_DIR):
        self.cache_dir = cache_dir
        self.library_dir: Optional[str] = None # 外部设置
        self.rate_limiter = RateLimiter(max_tokens=45, refill_period=300)
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _find_in_library(self, artist: str, title: str) -> Optional[str]:
        """
        在本地媒体库中查找音频文件
        返回: 相对于 library_dir 的路径 (用于 URL 拼接)
        """
        if not self.library_dir or not os.path.exists(self.library_dir):
            return None
            
        safe_artist = self._sanitize_filename(artist)
        safe_title = self._sanitize_filename(title)
        
        # 1. 尝试直接匹配 (Artist - Title.ext)
        target_name_base = f"{safe_artist} - {safe_title}"
        
        # 递归搜索 (支持子目录)
        # 注意：若库很大，os.walk 可能慢。假设库结构良好，或者我们只搜一层?
        # 用户需求: "本地媒体库文件夹"
        # 性能折衷: 限制搜索深度或只搜 root?
        # 暂时用 os.walk 但遇到第一个匹配就返回
        
        try:
            for root, dirs, files in os.walk(self.library_dir):
                for file in files:
                    if file.startswith(target_name_base):
                        # 检查扩展名
                        ext = os.path.splitext(file)[1].lower()
                        if ext in ['.mp3', '.flac', '.wav', '.m4a']:
                            # Found it
                            abs_path = os.path.join(root, file)
                            # 计算相对路径
                            rel_path = os.path.relpath(abs_path, self.library_dir)
                            # 统一用 / 分隔符 (URL safe)
                            return rel_path.replace("\\", "/")
        except Exception as e:
            logger.warning(f"Library search error: {e}")
            
        return None
    
    def _sanitize_filename(self, name: str) -> str:
        """清理文件名中的非法字符"""
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        if len(name) > 100:
            name = name[:100]
        return name
    
    def _get_local_path(self, artist: str, title: str, ext: str) -> str:
        """生成本地文件路径"""
        safe_artist = self._sanitize_filename(artist)
        safe_title = self._sanitize_filename(title)
        return os.path.join(self.cache_dir, f"{safe_artist} - {safe_title}.{ext}")
    
    async def search_songs(self, title: str, artist: str, source: str = "netease", count: int = 5) -> List[Dict]:
        """搜索歌曲"""
        if not title and not artist:
            return []
            
        if not await self.rate_limiter.acquire(wait=True):
            logger.warning(f"Rate limited during search for: {title} {artist}")
            return []
            
        api_source = self.SOURCE_MAP.get(source, source)
        clean_title = re.sub(r'[<>:"/\\|?*]', ' ', title).strip()
        clean_artist = re.sub(r'[<>:"/\\|?*]', ' ', artist).strip()
        keyword = f"{clean_title} {clean_artist}"
        
        params = {
            "types": "search",
            "count": count,
            "source": api_source,
            "pages": 1,
            "name": keyword
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        logger.info(f"Search Songs [{source}]: {keyword}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_BASE, params=params, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(f"搜索请求失败 [{source}], 状态码: {resp.status}")
                        return []
                    data = await resp.json()
                    if not data:
                        return []
                    
                    results = []
                    for item in data:
                        results.append({
                            "id": str(item.get("id")),
                            "source": source,
                            "title": item.get("name"),
                            "artist": item.get("artist", []),
                            "album": item.get("album"),
                            "pic_id": item.get("pic_id"),
                            "url_id": item.get("url_id")
                        })
                    return results
        except Exception as e:
            logger.warning(f"搜索失败 [{source}]: {e}")
        return []

    async def search_songs_all_sources(self, title: str, artist: str, album: str = None, count_per_source: int = 5) -> List[Dict]:
        """并行从所有来源搜索歌曲"""
        sources = ["netease", "qqmusic", "kugou", "kuwo", "migu"]
        tasks = [self.search_songs(title, artist, src, count_per_source) for src in sources]
        
        all_results_lists = await asyncio.gather(*tasks)
        
        # 合并结果
        merged = []
        for results in all_results_lists:
            merged.extend(results)
            
        return merged

    async def _search_match(self, source: str, title: str, artist: str, album: str = None) -> Optional[str]:
        """通过搜索获取最新 ID (用于 ID 失效的情况)"""
        results = await self.search_songs(title, artist, source, count=5)
        if not results:
            return None
            
        # 简单比对匹配，如果提供了专辑信息则优先匹配专辑
        for item in results:
            item_title = item.get("title", "").lower()
            item_artist = " ".join(item.get("artist", [])).lower()
            item_album = (item.get("album") or "").lower()
            
            # 基础匹配：标题和歌手包含在内
            if title.lower() in item_title and artist.lower() in item_artist:
                # 如果有专辑信息，尝试进一步匹配
                if album and item_album:
                    if album.lower() in item_album or item_album in album.lower():
                        return item["id"]
                # 如果没提供专辑名，或者专辑名不匹配但标题歌手高度匹配，也可以返回第一个
                if not album:
                    return item["id"]

        # 回退：如果没有完美符合专辑的，取第一个结果
        return results[0]["id"]

    async def _fetch_audio_url(self, source: str, song_id: str, quality: int = 999, title: str = None, artist: str = None, album: str = None) -> Optional[AudioInfo]:
        """
        从 API 获取音频下载链接 
        策略: 
        1. 尝试原始 ID (高音质)
        2. 尝试搜索匹配新 ID (高音质) [ID失效时]
        3. 降级尝试原始 ID (128k)
        4. 降级尝试新 ID (128k)
        """
        api_source = self.SOURCE_MAP.get(source, source)
        
        async def try_get(sid, br):
            params = {
                "types": "url",
                "source": api_source,
                "id": sid,
                "br": br
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            for attempt in range(3):
                if not await self.rate_limiter.acquire(wait=True): return None
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(self.API_BASE, params=params, headers=headers, timeout=30) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data.get("url"):
                                    return AudioInfo(
                                        url=data["url"],
                                        quality=int(data.get("br", 0)),
                                        size=int(data.get("size", 0)),
                                        format=data.get("url", "").split(".")[-1].split("?")[0] or "mp3"
                                    )
                            elif resp.status == 503:
                                logger.warning(f"API 503 错误, 重试中... ({attempt+1}/3)")
                                await asyncio.sleep(1 * (attempt+1))
                                continue
                            return None
                except Exception as e:
                    logger.error(f"获取 URL 异常 [{attempt+1}/3]: {e}")
                    await asyncio.sleep(1)
            return None

        # 1. 尝试原始 ID (Requested Quality)
        best_candidate = await try_get(song_id, quality)
        
        # 如果原始源已经是高音质 (>=320k) 或者我们不要求高音质，则直接返回
        if best_candidate and (best_candidate.quality >= 320 or quality < 320):
            return best_candidate
            
        if best_candidate:
            logger.info(f"原始源音质 ({best_candidate.quality}k) 未达预期，尝试跨源搜索更高音质...")

        # 2. 尝试智能匹配 ID (Requested Quality) - 支持跨源搜索
        # (ID失效 或 原始音质不佳时执行)
        if title and artist:
            # logger.info(f"尝试跨源智能匹配...") # Reducing log noise
            
            # 优先尝试原始源，然后尝试其他源
            all_sources = ["netease", "tencent", "kugou", "kuwo", "migu"]
            api_source_key = self.SOURCE_MAP.get(source, source)
            
            # 调整顺序：如果在 all_sources 中，移到最前（优先重试当前源，也许能搜到新ID）
            if api_source_key in all_sources:
                all_sources.remove(api_source_key)
                all_sources.insert(0, api_source_key)
            
            for src in all_sources:
                # logger.info(f"正在搜索源: {src} ...")
                new_id = await self._search_match(src, title, artist, album=album)
                
                if new_id:
                    # 定义内部获取函数用于跨源
                    async def fetch_cross(s, sid, q):
                        if not await self.rate_limiter.acquire(wait=True): return None
                        p = {"types": "url", "source": s, "id": sid, "br": q}
                        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(self.API_BASE, params=p, headers=h, timeout=30) as resp:
                                    if resp.status != 200: return None
                                    d = await resp.json()
                                    au = d.get("url")
                                    if au:
                                        real_br = d.get("br", 0)
                                        e = "flac" if ".flac" in au or real_br > 320 else "mp3"
                                        return AudioInfo(url=au, quality=real_br, size=d.get("size", 0), format=e)
                        except Exception as e:
                             logger.warning(f"跨源获取链接失败 [{s}, {sid}]: {e}")
                        return None

                    # 2.1 尝试从该源下载
                    info = await fetch_cross(src, new_id, quality)
                    
                    if info:
                        # 如果找到了满意的高音质 (>= 320k)
                        if info.quality >= 320:
                            logger.info(f"跨源匹配成功 (高音质) [{src}]: {new_id} ({info.quality}k)")
                            return info
                        
                        # 如果没找到高音质，但比当前的候选好 (或者当前没候选)
                        if not best_candidate or info.quality > best_candidate.quality:
                            logger.info(f"找到更好音质候选 [{src}]: {info.quality}k > {best_candidate.quality if best_candidate else 0}k")
                            best_candidate = info
        
        # 3. 返回现有最好的结果 (可能为 None，或低音质)
        if best_candidate:
            return best_candidate
            
        return None


    async def _fetch_metadata(self, source: str, song_id: str) -> Optional[AudioMetadata]:
        """获取歌曲元数据(封面等)"""
        # 复用 RateLimiter，虽然是不同的接口，但为了安全起见
        if not await self.rate_limiter.acquire(wait=True):
            return None

        api_source = self.SOURCE_MAP.get(source, source)
        
        # 1. 搜索歌曲信息获取专辑图ID
        # 注意：这里可能需要优化，因为搜索不一定精准，最好有直接详情接口
        # 但 GD Studio API 似乎主要依赖搜索。
        # 尝试使用 types=song 可能更好？文档未提及，但通常 Meting 有。
        # 先用 search 接口搜索 ID (虽然这是用来下载的ID，但搜索结果里有)
        # 或者直接用 types=pic 如果已知 pic_id。但即使已知 song_id 也不一定知道 pic_id。
        # 暂时只通过 song_id 似乎无法直接查详情，除非再次搜索。
        # 考虑到 API 限制，这里简单起见，如果传入了 metadata 就不查了？
        # 为了稳健，我们尝试获取封面。
        
        # 假设: 我们从外部调用者那里已经大致知道这些信息，
        # 但为了封面，我们可能需要 types=pic。可是我们需要 pic_id。
        # 如果不知道 pic_id, 很难获取封面。
        
        # 策略: 暂时返回 None, 由上层填充基础信息。
        # 如果需要封面，必须要有 pic_id。
        # 我们可以尝试用 song_id 当 pic_id 试试？(不一定对)
        # 或者调用 types=search&name=歌曲名 精确查找?
        
        # 暂时只做基本的对象构建
        return None 

    async def _download_content(self, url: str) -> Optional[bytes]:
        """下载内容到内存"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=300) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            logger.error(f"下载内容失败: {e}")
        return None

    async def _download_cover(self, pic_url: str) -> Optional[bytes]:
        """下载封面图片"""
        if not pic_url:
            return None
        return await self._download_content(pic_url)
    
    async def _fetch_lyric(self, title: str, artist: str) -> Optional[str]:
        """
        获取歌词
        优先级: OIAPI酷狗 > OIAPI QQ音乐
        """
        import base64
        import urllib.parse
        
        if not title or not artist:
            return None
        
        search_query = f"{title} {artist}"
        
        # 1. OIAPI 酷狗歌词
        try:
            url = f"https://oiapi.net/api/Kggc?msg={urllib.parse.quote(search_query)}&n=1&type=json"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == 1 and data.get("data", {}).get("base64"):
                            lyric = base64.b64decode(data["data"]["base64"]).decode("utf-8")
                            if self._is_valid_lyric(lyric):
                                logger.info(f"酷狗歌词获取成功: {title}")
                                return lyric
        except Exception as e:
            logger.warning(f"OIAPI酷狗歌词获取失败: {e}")
        
        # 2. OIAPI QQ音乐歌词
        try:
            url = f"https://oiapi.net/api/QQMusicLyric?keyword={urllib.parse.quote(search_query)}&n=1&type=json"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == 1 and data.get("data", {}).get("content"):
                            lyric = data["data"]["content"]
                            if data["data"].get("base64"):
                                lyric = base64.b64decode(data["data"]["base64"]).decode("utf-8")
                            if self._is_valid_lyric(lyric):
                                logger.info(f"QQ音乐歌词获取成功: {title}")
                                return lyric
        except Exception as e:
            logger.warning(f"OIAPI QQ音乐歌词获取失败: {e}")
        
        return None
    
    def _is_valid_lyric(self, lyric_text: str) -> bool:
        """检查歌词是否有效（非占位符）"""
        if not lyric_text or len(lyric_text) < 30:
            return False
        placeholders = ["暂无歌词", "纯音乐", "无歌词", "此歌曲为没有填词的纯音乐", "没有歌词"]
        for p in placeholders:
            if p in lyric_text:
                return False
        lrc_lines = [l for l in lyric_text.split('\n') if ']' in l and len(l.split(']')[-1].strip()) > 0]
        return len(lrc_lines) >= 3

    def _inject_metadata(self, file_path: str, metadata: AudioMetadata):
        """注入 ID3 标签"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                # 处理 MP3
                try:
                    audio = EasyMP3(file_path)
                except:
                    audio = MP3(file_path)
                    audio.add_tags()
                
                # 写入基础信息 (EasyID3)
                if isinstance(audio, EasyMP3):
                    audio['title'] = metadata.title
                    audio['artist'] = metadata.artist
                    audio['album'] = metadata.album
                    audio.save()
                
                # 写入封面 (需用 ID3)
                if metadata.cover_data:
                    audio = ID3(file_path)
                    audio.add(
                        APIC(
                            encoding=3, # 3 is UTF-8
                            mime='image/jpeg', # assume jpeg
                            type=3, # 3 is cover(front)
                            desc=u'Cover',
                            data=metadata.cover_data
                        )
                    )
                    audio.save()
                
                # 写入歌词 (USLT标签)
                if metadata.lyric:
                    audio = ID3(file_path)
                    audio.add(
                        USLT(
                            encoding=3,  # UTF-8
                            lang='chi',  # 中文
                            desc='',
                            text=metadata.lyric
                        )
                    )
                    audio.save()
                    logger.info(f"歌词注入成功 (MP3): {file_path}")
                    
            elif ext == '.flac':
                # 处理 FLAC
                audio = FLAC(file_path)
                audio['title'] = metadata.title
                audio['artist'] = metadata.artist
                audio['album'] = metadata.album
                
                if metadata.cover_data:
                    image = Picture()
                    image.type = 3
                    image.mime = 'image/jpeg'
                    image.desc = 'Cover'
                    image.data = metadata.cover_data
                    audio.add_picture(image)
                
                # 写入歌词
                if metadata.lyric:
                    audio['lyrics'] = metadata.lyric
                    logger.info(f"歌词注入成功 (FLAC): {file_path}")
                
                audio.save()
                
            logger.info(f"元数据注入成功: {file_path}")
            
        except Exception as e:
            logger.warning(f"注数据注入失败: {e}")

    async def download(
        self, 
        source: str, 
        song_id: str, 
        title: str, 
        artist: str,
        album: str = "",
        pic_url: str = "",
        quality: int = 999,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[Dict]:
        """
        下载音频文件 (包含元数据)
        """
        logger.info(f"开始处理: {artist} - {title}")
        
        # 0. 检查本地媒体库 (优先)
        lib_rel_path = self._find_in_library(artist, title)
        if lib_rel_path:
            full_lib_path = os.path.join(self.library_dir, lib_rel_path)
            logger.info(f"本地媒体库已存在: {full_lib_path}")
            if progress_callback: await progress_callback("📂 从本地媒体库加载...")
            return {
                "local_path": f"LIBRARY/{lib_rel_path}", 
                "quality": 999, 
                "size": os.path.getsize(full_lib_path),
                "format": os.path.splitext(full_lib_path)[1].lower().replace('.', '')
            }
        
        # 1. 检查本地缓存
        cached_filename = self.get_cached_path(artist, title)
        if cached_filename:
            if progress_callback: await progress_callback("⚡ 从缓存/收藏加载...")
            
            full_path = os.path.join(self.cache_dir, cached_filename)
            # If not in cache, check favorites (since get_cached_path might find it there)
            if not os.path.exists(full_path):
                from core.config import config
                fav_dir = config.get('storage', {}).get('favorites_dir', 'favorites')
                fav_path = os.path.join(fav_dir, cached_filename)
                if os.path.exists(fav_path):
                    full_path = fav_path

            logger.info(f"本地已存在 (恢复): {full_path}")
            return {
                "local_path": cached_filename,
                "quality": 999 if cached_filename.endswith(".flac") else 320, # 估算
                "size": os.path.getsize(full_path),
                "format": cached_filename.split(".")[-1],
                "has_lyric": False # 暂不重新解析歌词，假设已有
            }

        # 2. 获取下载链接
        if progress_callback: await progress_callback("🔍 正在全网搜索最佳音源...")
        audio_info = await self._fetch_audio_url(source, song_id, quality, title=title, artist=artist, album=album)
        if not audio_info:
            logger.warning(f"无法获取音频链接: {title}")
            return None
        
        # 2. 检查本地是否存在
        local_path = self._get_local_path(artist, title, audio_info.format)
        if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
            logger.info(f"文件已存在: {local_path}")
            return {
                "local_path": os.path.basename(local_path),
                "quality": audio_info.quality,
                "size": os.path.getsize(local_path),
                "format": audio_info.format
            }
            
        # 3. 下载音频到内存
        logger.info(f"正在下载音频流...")
        if progress_callback: await progress_callback("⬇️ 正在下载音频内容...")
        audio_data = await self._download_content(audio_info.url)
        if not audio_data:
            return None
            
        # 4. 获取歌词
        lyric = None
        logger.info(f"正在获取歌词...")
        if progress_callback: await progress_callback("🎵 正在解析并匹配歌词...")
        lyric = await self._fetch_lyric(title, artist)
        if lyric:
            logger.info(f"歌词获取成功: {title}")
        else:
            logger.warning(f"歌词获取失败: {title}")
        
        # 5. 下载封面图
        cover_data = None
        if pic_url:
            logger.info(f"正在下载封面图...")
            if progress_callback: await progress_callback("🖼️ 正在处理封面图片...")
            cover_data = await self._download_cover(pic_url)
            
        # 6. 写入文件
        logger.info(f"写入文件: {local_path}")
        if progress_callback: await progress_callback("💾 正在写入文件并注入元数据...")
        async with aiofiles.open(local_path, 'wb') as f:
            await f.write(audio_data)
            
        # 7. 注入元数据(包含歌词)
        metadata = AudioMetadata(
            title=title,
            artist=[artist], # 简单处理，视为单个歌手
            album=album if album else title, # 无专辑名时用歌名代替
            cover_data=cover_data,
            lyric=lyric  # 歌词
        )
        # 在线程池中运行 mutagen (它是同步 IO)
        await asyncio.to_thread(self._inject_metadata, local_path, metadata)
        
        if progress_callback: await progress_callback("✅ 准备就绪，即将播放！")
        return {
            "local_path": os.path.basename(local_path),
            "quality": audio_info.quality,
            "size": len(audio_data),
            "format": audio_info.format,
            "has_lyric": bool(lyric),
            "lyric": lyric # Return content for DB update
        }

    def get_cached_path(self, artist: str, title: str) -> Optional[str]:
        """检查缓存 (包括收藏目录)"""
        # 0. Check Favorites
        from core.config import config
        fav_dir = config.get('storage', {}).get('favorites_dir', 'favorites')
        if not os.path.isabs(fav_dir) and fav_dir.startswith("/config"):
             # Handle absolute path docker case if needed, but config usually has abs or rel.
             pass
             
        # Normalize favorites lookup
        safe_artist = self._sanitize_filename(artist)
        safe_title = self._sanitize_filename(title)
        
        for ext in ['flac', 'mp3']:
            target_name = f"{safe_artist} - {safe_title}.{ext}"
            
            # 1. Favorites
            if os.path.exists(fav_dir):
                fav_path = os.path.join(fav_dir, target_name)
                if os.path.exists(fav_path) and os.path.getsize(fav_path) > 1024:
                    logger.info(f"Found in favorites: {fav_path}")
                    return target_name # Return basename, serve_audio will handle lookup
            
            # 2. Cache
            path = self._get_local_path(artist, title, ext)
            if os.path.exists(path) and os.path.getsize(path) > 1024:
                return os.path.basename(path)
        return None

# 全局单例
audio_downloader = AudioDownloader()

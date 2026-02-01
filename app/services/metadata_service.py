# -*- coding: utf-8 -*-
"""
元数据服务 - 歌词、封面、专辑信息获取

此模块通过 music_providers 获取歌曲元数据。
- 歌词获取: 通过 pyncm (网易云) 和 qqmusic-api (QQ音乐)
- 封面获取: 通过 music_providers 搜索结果
- 专辑信息: 通过 music_providers 搜索结果

注意: GDStudio API 仅用于下载，不用于元数据获取。

Author: google
Created: 2026-01-23
"""
import asyncio
import os
import aiohttp
import logging
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import anyio

try:
    import mutagen
    from mutagen.id3 import ID3, USLT, SYLT
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
except ImportError:
    mutagen = None

from app.services.smart_merger import SongMetadata

logger = logging.getLogger(__name__)


@dataclass
class MetadataResult:
    """元数据结果"""
    lyrics: Optional[str] = None
    cover_data: Optional[bytes] = None
    cover_url: Optional[str] = None
    album: Optional[str] = None
    publish_time: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None


class MetadataService:
    """
    元数据服务
    
    通过 music_providers (pyncm, qqmusic-api) 获取歌曲元数据。
    """
    
    def __init__(self):
        self._netease_provider = None
        self._qqmusic_provider = None
    
    def _get_netease_provider(self):
        """获取网易云 provider（懒加载）"""
        if self._netease_provider is None:
            try:
                from app.services.music_providers.netease_provider import NeteaseProvider
                self._netease_provider = NeteaseProvider()
            except ImportError as e:
                logger.warning(f"无法加载 NeteaseProvider: {e}")
        return self._netease_provider
    
    def _get_qqmusic_provider(self):
        """获取QQ音乐 provider（懒加载）"""
        if self._qqmusic_provider is None:
            try:
                from app.services.music_providers.qqmusic_provider import QQMusicProvider
                self._qqmusic_provider = QQMusicProvider()
            except ImportError as e:
                logger.warning(f"无法加载 QQMusicProvider: {e}")
        return self._qqmusic_provider
    
    # ========== 歌词获取 ==========
    
    # ========== 歌词获取 ==========
    
    async def fetch_lyrics(self, title: str, artist: str, 
                           source: str = None, source_id: str = None,
                           local_path: str = None) -> Optional[str]:
        """
        获取歌词
        
        策略:
        1. [优先] 读取本地音频文件的内嵌歌词 (ID3/FLAC Tags)
        2. [Fallback] 在线获取 (Netease/QQ)
        3. [Auto-Embed] 在线获取成功后，异步写入本地文件
        """
        # 1. 尝试本地读取
        print(f"=== DEBUG === fetch_lyrics called for '{title}' by '{artist}'. local_path: {local_path}, source_id: {source_id}", flush=True)

        # 1. Try to read embedded lyrics first if local path is available
        if local_path and mutagen:
            print(f"=== DEBUG === Attempting to read embedded lyrics from: {local_path}", flush=True)
            if os.path.exists(local_path):
                print("=== DEBUG === File exists, attempting to read embedded lyrics...", flush=True)
                try:
                    embedded_lyrics = await self._read_embedded_lyrics(local_path)
                    if embedded_lyrics:
                        print(f"=== DEBUG === ✅ Found embedded lyrics ({len(embedded_lyrics)} chars)", flush=True)
                        return embedded_lyrics
                    else:
                        print("=== DEBUG === ❌ No embedded lyrics found in file.", flush=True)
                except Exception as e:
                    print(f"=== DEBUG === ❌ Error reading embedded lyrics: {e}", flush=True)
            else:
                 print(f"=== DEBUG === ❌ Local file not found at: {local_path}", flush=True)
        elif local_path and not mutagen:
            print("=== DEBUG === Skipping embedded lyrics check: mutagen not installed.", flush=True)
        elif not local_path:
            print("=== DEBUG === No local_path provided, skipping embedded lyrics check.", flush=True)

        # 2. Fallback to online providers
        print(f"=== DEBUG === Falling back to online search for: {title} - {artist}", flush=True)
        lyrics = await self._fetch_online_lyrics(title, artist, source, source_id)
        
        # 3. 自动回写 (Auto-Embed)
        if lyrics and local_path and mutagen:
            # Fire and forget task to write tags
            # 由于这是个耗时IO操作，且非阻断性，建议在后台通过 anyio/asyncio 运行
            # 这里简单起见直接 await，或者以后放到后台任务队列中
            try:
                await self._write_embedded_lyrics(local_path, lyrics)
            except Exception as e:
                logger.warning(f"Failed to auto-embed lyrics: {e}")
                
        return lyrics

    async def _fetch_online_lyrics(self, title: str, artist: str, 
                           source: str = None, source_id: str = None) -> Optional[str]:
        # 如果有 source_id，直接获取
        if source and source_id:
            lyrics = await self._fetch_lyrics_by_id(source, source_id)
            if lyrics:
                return lyrics
        
        # 否则搜索后获取
        providers = [
            ("netease", self._get_netease_provider()),
            ("qqmusic", self._get_qqmusic_provider())
        ]
        
        for source_name, provider in providers:
            if not provider:
                continue
            
            try:
                keyword = f"{title} {artist}"
                results = await provider.search_song(keyword, limit=5)
                
                if results:
                    song_id = results[0].id
                    lyrics = await provider.get_lyrics(song_id)
                    if lyrics:
                        logger.info(f"从 {source_name} 获取歌词成功: {title}")
                        return lyrics
            except Exception as e:
                logger.warning(f"从 {source_name} 获取歌词失败: {e}")
                continue
        
        logger.warning(f"未能获取歌词: {title} - {artist}")
        return None

    async def _read_embedded_lyrics(self, file_path: str) -> Optional[str]:
        """读取内嵌歌词"""
        def _read_sync():
            path = Path(file_path)
            if not path.exists(): return None
            
            audio = mutagen.File(file_path)
            if not audio: return None

            lyrics = None
            
            # ID3 (MP3)
            if isinstance(audio.tags, ID3):
                # 尝试 USLT (Unsynchronized lyrics)
                for key in audio.tags.keys():
                    if key.startswith('USLT'):
                        return audio.tags[key].text
            
            # FLAC / Vorbis
            elif isinstance(audio, FLAC) or hasattr(audio, 'tags'):
                 if 'LYRICS' in audio:
                     return audio['LYRICS'][0]
                 if 'UNSYNCEDLYRICS' in audio: # Common in Ogg/FLAC
                     return audio['UNSYNCEDLYRICS'][0]
            
            # MP4 / M4A
            elif isinstance(audio, MP4):
                if '\xa9lyr' in audio:
                    return audio['\xa9lyr'][0]
            
            return None

        return await anyio.to_thread.run_sync(_read_sync)

    async def _write_embedded_lyrics(self, file_path: str, lyrics: str):
        """写入内嵌歌词"""
        def _write_sync():
            path = Path(file_path)
            if not path.exists(): return
            
            try:
                audio = mutagen.File(file_path)
                if not audio: return
                
                # MP3 / ID3
                if path.suffix.lower() == '.mp3':
                    if audio.tags is None:
                        audio.add_tags()
                    # USLT frame
                    audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))
                    audio.save()
                
                # FLAC
                elif path.suffix.lower() == '.flac':
                     audio['LYRICS'] = lyrics
                     audio.save()
                     
                # M4A
                elif path.suffix.lower() in ['.m4a', '.mp4']:
                    audio['\xa9lyr'] = lyrics
                    audio.save()
                    
                logger.info(f"Lyrics embedded to {file_path}")
            except Exception as e:
                logger.warning(f"Error writing lyrics to file: {e}")

        await anyio.to_thread.run_sync(_write_sync)
    
    async def _fetch_lyrics_by_id(self, source: str, source_id: str) -> Optional[str]:
        """通过ID直接获取歌词"""
        provider = None
        if source == "netease":
            provider = self._get_netease_provider()
        elif source == "qqmusic":
            provider = self._get_qqmusic_provider()
        
        if not provider:
            return None
        
        try:
            return await provider.get_lyrics(source_id)
        except Exception as e:
            logger.warning(f"通过ID获取歌词失败: {e}")
            return None
    
    # ========== 封面获取 ==========
    
    async def fetch_cover_url(self, title: str, artist: str) -> Optional[str]:
        """
        获取封面URL
        
        通过 music_providers 搜索获取封面URL。
        """
        providers = [
            ("netease", self._get_netease_provider()),
            ("qqmusic", self._get_qqmusic_provider())
        ]
        
        for source_name, provider in providers:
            if not provider:
                continue
            
            try:
                keyword = f"{title} {artist}"
                results = await provider.search_song(keyword, limit=1)
                if results and results[0].cover_url:
                    logger.info(f"从 {source_name} 获取封面成功: {title}")
                    return results[0].cover_url
            except Exception as e:
                logger.warning(f"从 {source_name} 获取封面失败: {e}")
                continue
        
        return None
    
    async def fetch_cover_data(self, cover_url: str) -> Optional[bytes]:
        """下载封面图片数据"""
        if not cover_url:
            return None
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(cover_url, headers=headers, timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            logger.warning(f"下载封面失败: {e}")
        
        return None
    
    # ========== 完整元数据获取 ==========
    
    async def fetch_metadata(self, title: str, artist: str, 
                              source: str = None, source_id: str = None) -> MetadataResult:
        """
        获取完整的元数据（歌词、封面、专辑、发布日期）
        """
        logger.info(f"获取元数据: {title} - {artist}")
        result = MetadataResult()
        
        providers = [
            ("netease", self._get_netease_provider()),
            ("qqmusic", self._get_qqmusic_provider())
        ]
        
        # Helper to safely access attributes or dict keys
        def get_val(obj, key, default=None):
            if isinstance(obj, dict): return obj.get(key, default)
            return getattr(obj, key, default)

        # 2. 搜索获取最佳匹配信息 (包含专辑、日期、封面)
        # 我们先按顺序尝试 Provider。如果第一个 Provider 的结果不全（比如缺封面），我们会尝试第二个。
        
        for source_name, provider in providers:
            if not provider: continue
            try:
                keyword = f"{title} {artist}"
                # 搜索
                search_results = await provider.search_song(keyword, limit=3)
                if not search_results: continue
                
                # 简单匹配：取第一个 或者 匹配度最高的
                best_match = search_results[0]
                
                # 检查是否匹配（基本的名称校验）
                # 如果搜索结果太离谱，可能需要跳过
                
                # 尝试获取完整元数据 (Lyrics + Extra)
                try:
                    song_meta = await provider.get_song_metadata(best_match.id)
                    if song_meta:
                        # 补全 result
                        if not result.lyrics: result.lyrics = get_val(song_meta, 'lyrics')
                        if not result.cover_url: result.cover_url = get_val(song_meta, 'cover_url')
                        if not result.album: result.album = get_val(song_meta, 'album')
                        if not result.publish_time: result.publish_time = get_val(song_meta, 'publish_time')
                        
                        # 特殊补全：有的 provider get_metadata 不返回 publish_time 而是返回在 search result 里
                        if not result.publish_time and best_match.publish_time:
                            result.publish_time = best_match.publish_time
                        if not result.cover_url and best_match.cover_url:
                            result.cover_url = best_match.cover_url
                            
                        logger.info(f"从 {source_name} 获取/补全了元数据")
                except Exception as sub_e:
                     # Fallback to search result info
                     if not result.cover_url: result.cover_url = best_match.cover_url
                     if not result.album: result.album = best_match.album
                     if not result.publish_time: result.publish_time = best_match.publish_time
                     logger.warning(f"{source_name} get_song_metadata failed, using search result: {sub_e}")

                # 策略：如果核心元数据（封面和歌词）都有了，就可以停止了
                # 如果还是没有封面，继续尝试下一个 provider
                if result.cover_url and result.lyrics:
                    break
                     
            except Exception as e:
                logger.warning(f"从 {source_name} 搜索元数据失败: {e}")
                continue
        
        # 3. 下载封面数据
        if result.cover_url:
            result.cover_data = await self.fetch_cover_data(result.cover_url)
        
        result.success = bool(result.lyrics or result.cover_url or result.publish_time)
        return result
    
    async def get_best_match_metadata(self, title: str, artist: str) -> SongMetadata:
        """
        获取最佳匹配元数据 (标准化输出)
        
        Args:
            title: 歌曲标题
            artist: 歌手
            
        Returns:
            SongMetadata 对象
        """
        # 复用现有的 fetch_metadata 逻辑
        # TODO: 未来可以将 search 逻辑移入这里，实现更细粒度的控制
        raw_result = await self.fetch_metadata(title, artist)
        
        # 计算置信度
        confidence = 0.0
        if raw_result.success:
            confidence += 0.5
            if raw_result.lyrics: confidence += 0.2
            if raw_result.cover_url: confidence += 0.2
            if raw_result.album: confidence += 0.1
            
        return SongMetadata(
            title=title,
            artist=artist,
            album=raw_result.album,
            cover_url=raw_result.cover_url,
            publish_time=raw_result.publish_time,
            lyrics=raw_result.lyrics,
            source="aggregator", # 实际上是 netease/qq混合
            confidence=min(confidence, 1.0)
        )
    
    async def close(self):
        """关闭服务"""
        pass
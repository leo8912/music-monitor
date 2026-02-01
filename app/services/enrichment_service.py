
import logging
import os
import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from app.services.music_providers import MusicAggregator
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3

from app.services.metadata_service import MetadataService
from app.services.smart_merger import SmartMerger, SongMetadata

logger = logging.getLogger(__name__)

class EnrichmentService:
    """
    元数据补全服务 (EnrichmentService)
    
    核心功能:
    1. 扫描本地歌曲库，查找缺失元数据(封面/专辑/年份)的歌曲
    2. 使用 MusicAggregator 在线搜索最佳匹配
    3. 下载高清封面并保存到本地 (uploads/covers)
    4. 将元数据和封面回写到音频文件 (ID3/FLAC Tags)
    5. 更新数据库记录
    """
    
    def __init__(self):
        self.metadata_service = MetadataService()
        self.merger = SmartMerger()
        self.upload_root = os.path.join(os.getcwd(), "uploads")
        self.cover_dir = os.path.join(self.upload_root, "covers")
        os.makedirs(self.cover_dir, exist_ok=True)

    async def auto_enrich_library(self, force: bool = False):
        """
        自动补全整个资料库
        Args:
            force: 是否强制重新检查已有完整元数据的歌曲
        """
        logger.info("🚀 开始自动补全标签任务...")
        async with AsyncSessionLocal() as db:
            # 查找所有本地歌曲
            stmt = select(Song).options(selectinload(Song.sources), selectinload(Song.artist)).where(Song.local_path.isnot(None))
            result = await db.execute(stmt)
            songs = result.scalars().all()
            
            count = 0
            for song in songs:
                # 简单检查: 如果缺封面或专辑名，则进行补全
                needs_enrichment = not song.cover or not song.album or \
                                   (song.cover and not song.cover.startswith('/uploads/')) # 优先本地封面
                
                if needs_enrichment or force:
                    try:
                        await self.enrich_song(song.id)
                        count += 1
                    except Exception as e:
                        logger.error(f"❌ 补全 {song.title} 失败: {e}")
                        
        logger.info(f"✅ 标签补全任务完成，共处理 {count} 首歌曲")

    async def enrich_song(self, song_id: str):
        """
        补全单首歌曲
        """
        async with AsyncSessionLocal() as db:
            song = await db.get(Song, song_id, options=[selectinload(Song.sources), selectinload(Song.artist)])
            if not song:
                return

            logger.info(f"🔍 正在为 [{song.title}] 搜索元数据...")
            
            logger.info(f"🔍 正在为 [{song.title}] 搜索元数据...")
            
            # 使用新的 MetadataService 获取标准化结果
            online_meta = await self.metadata_service.get_best_match_metadata(song.title, song.artist.name if song.artist else "")
            
            if not online_meta.confidence > 0:
                logger.warning(f"⚠️ 未找到匹配的在线元数据: {song.title}")
                return

            # 构建本地元数据对象
            local_meta = SongMetadata(
                title=song.title,
                artist=song.artist.name if song.artist else "",
                album=song.album,
                cover_url=song.cover,
                publish_time=song.publish_time,
                lyrics=None # Assuming DB doesn't store full lyrics in song table yet, or we ignore for now
            )
            
            # 智能合并
            final_meta = self.merger.merge(local_meta, online_meta)
            
            logger.info(f"✨ 智能合并结果: {final_meta.album} (Cover: {final_meta.cover_url})")
            
            # 2. 如果有新封面，下载并保存
            local_cover_path = None
            local_cover_url = None
            
            # 只有当决定使用新封面，且新封面不是本地路径时才下载
            if final_meta.cover_url and final_meta.cover_url.startswith("http"):
                 local_cover_url, local_cover_path = await self._download_cover(final_meta.cover_url, song.title)
                 final_meta.cover_url = local_cover_url # Update to local path
            elif final_meta.cover_url and final_meta.cover_url.startswith("/uploads"):
                 local_cover_url = final_meta.cover_url
                 # Try to resolve path if possible, or just keep url
                 local_cover_path = os.path.join(self.upload_root, final_meta.cover_url.replace("/uploads/", ""))
            
            # 3. 更新数据库 Song
            song.album = final_meta.album
            song.publish_time = final_meta.publish_time
            if local_cover_url:
                song.cover = local_cover_url
            
            # 4. 更新本地文件 (Tags) 和 SongSource
            for src in song.sources:
                if src.source == 'local' and src.url and os.path.exists(src.url):
                    # 回写 Tags
                    await self._write_tags_to_file(src.url, final_meta.album, local_cover_path)
                    
                    # 更新 Source 数据
                    data = src.data_json or {}
                    if isinstance(data, str): 
                        import json
                        try: data = json.loads(data)
                        except: data = {}
                        
                    data['cover'] = local_cover_url
                    data['album'] = final_meta.album
                    
                    src.data_json = data
                    src.cover = local_cover_url
            
            await db.commit()
            logger.info(f"✅ [{song.title}] 补全完成")

    async def _download_cover(self, url: str, prefix: str) -> tuple[Optional[str], Optional[str]]:
        """下载封面，返回 (web_url, local_abs_path)"""
        try:
            import hashlib
            ext = "jpg"
            if ".png" in url: ext = "png"
            
            md5 = hashlib.md5(url.encode()).hexdigest()
            filename = f"{md5}.{ext}"
            save_path = os.path.join(self.cover_dir, filename)
            web_url = f"/uploads/covers/{filename}"
            
            if os.path.exists(save_path):
                return web_url, save_path
                
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(save_path, "wb") as f:
                            f.write(content)
                        return web_url, save_path
            return None, None
        except Exception as e:
            logger.warning(f"下载封面失败 {url}: {e}")
            return None, None

    async def _write_tags_to_file(self, file_path: str, album_name: str, cover_path: str = None):
        """由于 mutagen 操作通常是阻塞的 IO，可以放入线程池执行"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._sync_write_tags(file_path, album_name, cover_path))

    def _sync_write_tags(self, file_path: str, album_name: str, cover_path: str = None):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.flac':
                audio = FLAC(file_path)
                if album_name:
                    audio['album'] = album_name
                # audio['date'] = str(metadata.publish_time)[:4] # Optional
                
                if cover_path and os.path.exists(cover_path):
                    image = Picture()
                    image.type = 3 # Front Cover
                    if cover_path.endswith('.png'):
                        image.mime = 'image/png'
                    else:
                        image.mime = 'image/jpeg'
                    
                    with open(cover_path, 'rb') as f:
                        image.data = f.read()
                    
                    audio.clear_pictures()
                    audio.add_picture(image)
                
                audio.save()
                
            elif ext == '.mp3':
                audio = MP3(file_path, ID3=ID3)
                if not audio.tags:
                    audio.add_tags()
                
                tag = audio.tags
                tag.add(APIC(
                    encoding=3, # 3 is UTF-8
                    mime='image/jpeg', # or image/png
                    type=3, # 3 is for the cover image
                    desc=u'Cover',
                    data=open(cover_path, 'rb').read()
                ))
                audio.save()
                
        except Exception as e:
            logger.error(f"写入音频标签失败 {file_path}: {e}")


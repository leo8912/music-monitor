# -*- coding: utf-8 -*-
"""
EnrichmentService - 元数据补全服务 (智能混合模式)

核心功能:
1. 扫描本地歌曲库，查找缺失/低质量元数据的歌曲
2. 使用 SmartMerger 智能决策是否更新字段
3. 下载高清封面并保存到本地 (uploads/covers)
4. 将元数据和封面回写到音频文件 (ID3/FLAC Tags)
5. 更新数据库记录

Author: google
Created: 2026-01-23
Updated: 2026-02-02 - 接入 SmartMerger 智能合并逻辑
"""
import logging
import os
import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from app.services.music_providers import MusicAggregator
from app.services.smart_merger import SmartMerger, SongMetadata
from app.services.metadata_service import MetadataService
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    元数据补全服务 (EnrichmentService) - 智能混合模式
    
    核心功能:
    1. 扫描本地歌曲库，查找缺失/低质量元数据的歌曲
    2. 使用 SmartMerger 智能决策是否更新字段
    3. 下载高清封面并保存到本地 (uploads/covers)
    4. 将元数据回写到音频文件 (ID3/FLAC Tags)
    5. 更新数据库记录
    """
    
    def __init__(self):
        self.aggregator = MusicAggregator()
        self.metadata_service = MetadataService()
        self.upload_root = os.path.join(os.getcwd(), "uploads")
        self.cover_dir = os.path.join(self.upload_root, "covers")
        os.makedirs(self.cover_dir, exist_ok=True)

    async def auto_enrich_library(self, force: bool = False, limit: int = 100):
        """
        全量扫描并智能补全本地库中的歌曲元数据。
        
        该任务通常作为后台维护任务运行：
        1. 遍历所有具有本地路径的歌曲。
        2. 智能识别元数据不完整或画质较低（非本地封面）的歌曲。
        3. 批量调用在线接口并发抓取（通过 MetadataService）。
        
        Args:
            force (bool): 为 True 时，即使元数据看似完整也会重新检查抓取。
            limit (int): 本次运行处理的最大歌曲数。
        """
        logger.info("🚀 开始自动补全标签任务 (智能混合模式)...")
        async with AsyncSessionLocal() as db:
            # 查找所有本地歌曲
            stmt = select(Song).options(
                selectinload(Song.sources), 
                selectinload(Song.artist)
            ).where(Song.local_path.isnot(None)).limit(limit)
            
            result = await db.execute(stmt)
            songs = result.scalars().all()
            
            count = 0
            updated_count = 0
            
            for song in songs:
                # 智能判断是否需要补全
                needs_enrichment = self._needs_enrichment(song) or force
                
                if needs_enrichment:
                    try:
                        updated = await self.enrich_song(song.id)
                        count += 1
                        if updated:
                            updated_count += 1
                    except Exception as e:
                        logger.error(f"❌ 补全 {song.title} 失败: {e}")
                        
        logger.info(f"✅ 标签补全任务完成，共检查 {count} 首歌曲，实际更新 {updated_count} 首")
    
    def _needs_enrichment(self, song: Song) -> bool:
        """
        智能判断歌曲是否需要补全
        
        条件：
        1. 缺少封面或封面是远程URL（非本地）
        2. 缺少专辑名或专辑名为垃圾值
        3. 缺少发布时间或发布时间无效
        """
        # 检查重试退避 (Backoff)
        if song.last_enrich_at:
            # 如果 24 小时内刚尝试过补全，则跳过
            delta = datetime.now() - song.last_enrich_at
            if delta.total_seconds() < 24 * 3600:
                return False

        # 检查封面
        if not song.cover:
            return True
        if song.cover and not song.cover.startswith('/uploads/'):
            return True  # 优先本地封面
        
        # 检查专辑
        if SmartMerger.is_garbage_value(song.album):
            return True
        
        # 检查发布时间
        if SmartMerger.is_invalid_date(song.publish_time):
            return True
        
        return False
    
    async def _get_current_cover_size(self, song: Song) -> int:
        """获取当前封面大小（字节）"""
        if not song.cover:
            return 0
        
        if song.cover.startswith('/uploads/'):
            # 本地封面
            local_path = os.path.join(os.getcwd(), song.cover.lstrip('/'))
            if os.path.exists(local_path):
                return os.path.getsize(local_path)
        
        return 0  # 远程封面暂不获取大小

    async def enrich_song(self, song_id: str) -> bool:
        """
        基于智能合并策略补全单首歌曲的元数据。
        
        决策逻辑 (由 SmartMerger 驱动):
        - 补充空缺：如果本地缺少封面、日期或专辑名，则直接补充。
        - 画质升级：如果在线封面文件体积显著大于本地现有封面，则替换。
        - 格式升级：如果在线拥有带时间锚点的歌词，且本地只有纯文本，则替换。
        
        Args:
            song_id (str): 数据库中的歌曲 ID。
            
        Returns:
            bool: 若该歌曲至少有一个字段被更新（或标签已回写），返回 True。
        """
        async with AsyncSessionLocal() as db:
            song = await db.get(
                Song, song_id, 
                options=[selectinload(Song.sources), selectinload(Song.artist)]
            )
            if not song:
                return False

            artist_name = song.artist.name if song.artist else ""
            logger.info(f"🔍 智能补全: [{song.title}] - {artist_name}")
            
            # 1. 构建当前元数据
            current_cover_size = await self._get_current_cover_size(song)
            current = SongMetadata(
                title=song.title,
                artist=artist_name,
                album=song.album,
                cover_url=song.cover,
                cover_size_bytes=current_cover_size,
                lyrics=self._get_song_lyrics(song),
                publish_time=song.publish_time
            )
            
            # 2. 获取在线最佳元数据
            online_meta = await self.metadata_service.get_best_match_metadata(
                song.title, artist_name
            )
            
            if not online_meta.success:
                logger.warning(f"⚠️ 未找到在线元数据: {song.title}")
                song.last_enrich_at = datetime.now()
                await db.commit()
                return False
            
            # 转换为 SongMetadata
            new = SongMetadata(
                title=song.title,
                artist=artist_name,
                album=online_meta.album,
                cover_url=online_meta.cover_url,
                cover_size_bytes=online_meta.cover_size_bytes,
                lyrics=online_meta.lyrics,
                publish_time=self._parse_date(online_meta.publish_time),
                source=online_meta.source
            )
            
            # 3. 智能合并决策
            updates = SmartMerger.merge(current, new)
            
            if not updates:
                logger.info(f"⏭️ [{song.title}] 元数据已完整，无需更新")
                song.last_enrich_at = datetime.now()
                await db.commit()
                return False
            
            logger.info(f"📝 将更新字段: {list(updates.keys())}")
            
            # [Fix] 强制本地化逻辑：
            # 如果当前封面是远程链接（非 /uploads/ 开头），且 SmartMerger 因画质原因没有决定更新，
            # 我们仍然强制将 online_meta.cover_url 加入 updates，以便后续流程下载并转为本地连接。
            # 这样可以防止 _needs_enrichment 此后一直返回 True 造成死循环。
            if song.cover and not song.cover.startswith('/uploads/'):
                if "cover" not in updates and online_meta.cover_url:
                    logger.info("⚠️ 发现远程封面，强制加入本地化更新队列")
                    updates["cover"] = online_meta.cover_url
            
            # 4. 执行更新
            local_cover_path = None
            local_cover_url = None
            
            # 处理封面更新
            if "cover" in updates and updates["cover"]:
                local_cover_url, local_cover_path = await self._download_cover(
                    updates["cover"], song.title
                )
                if local_cover_url:
                    song.cover = local_cover_url
            
            # 处理专辑更新
            if "album" in updates:
                song.album = updates["album"]
            
            # 处理发布时间更新
            if "publish_time" in updates:
                song.publish_time = updates["publish_time"]
            
            # 5. 更新本地文件 Tags
            for src in song.sources:
                if src.source == 'local' and src.url and os.path.exists(src.url):
                    await self._write_tags_to_file(
                        src.url, 
                        updates.get("album"), 
                        local_cover_path
                    )
                    
                    # 更新 Source 数据
                    data = self._parse_data_json(src.data_json)
                    if local_cover_url:
                        data['cover'] = local_cover_url
                    if "album" in updates:
                        data['album'] = updates["album"]
                    
                    src.data_json = data
                    if local_cover_url:
                        src.cover = local_cover_url
            
            song.last_enrich_at = datetime.now()
            await db.commit()
            logger.info(f"✅ [{song.title}] 智能补全完成")
            return True
    
    def _get_song_lyrics(self, song: Song) -> Optional[str]:
        """从歌曲源获取歌词"""
        for src in song.sources:
            if src.data_json:
                data = self._parse_data_json(src.data_json)
                if data.get("lyrics"):
                    return data["lyrics"]
        return None
    
    def _parse_data_json(self, data_json) -> Dict:
        """解析 data_json 字段"""
        if data_json is None:
            return {}
        if isinstance(data_json, dict):
            return data_json
        if isinstance(data_json, str):
            import json
            try:
                return json.loads(data_json)
            except:
                return {}
        return {}
    
    def _parse_date(self, date_value) -> Optional[datetime]:
        """解析日期值"""
        if date_value is None:
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            # 尝试多种格式
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d",
                "%Y年%m月%d日"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
            
            # 尝试只解析年份
            try:
                year = int(date_value[:4])
                if 1900 < year < 2100:
                    return datetime(year, 1, 1)
            except:
                pass
        
        if isinstance(date_value, (int, float)):
            # 毫秒时间戳
            try:
                if date_value > 1e12:
                    date_value = date_value / 1000
                return datetime.fromtimestamp(date_value)
            except:
                pass
        
        return None

    async def _download_cover(self, url: str, prefix: str) -> Tuple[Optional[str], Optional[str]]:
        """
        下载封面，返回 (web_url, local_abs_path)
        
        Args:
            url: 封面远程URL
            prefix: 文件名前缀（用于生成唯一文件名）
            
        Returns:
            Tuple[web_url, local_abs_path]
        """
        try:
            import hashlib
            ext = "jpg"
            if ".png" in url.lower(): 
                ext = "png"
            
            md5 = hashlib.md5(url.encode()).hexdigest()
            filename = f"{md5}.{ext}"
            save_path = os.path.join(self.cover_dir, filename)
            web_url = f"/uploads/covers/{filename}"
            
            # 已存在则直接返回
            if os.path.exists(save_path):
                logger.info(f"🖼️ 封面已缓存: {filename}")
                return web_url, save_path
            
            # 下载封面
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(save_path, "wb") as f:
                            f.write(content)
                        logger.info(f"✅ 封面下载成功: {filename} ({len(content)/1024:.1f}KB)")
                        return web_url, save_path
                    else:
                        logger.warning(f"封面下载失败, HTTP {resp.status}: {url}")
                        
            return None, None
        except Exception as e:
            logger.warning(f"下载封面失败 {url}: {e}")
            return None, None

    async def _write_tags_to_file(self, file_path: str, album_name: str = None, cover_path: str = None):
        """
        回写元数据到音频文件
        
        由于 mutagen 操作是阻塞 IO，使用线程池执行
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, 
            lambda: self._sync_write_tags(file_path, album_name, cover_path)
        )

    def _sync_write_tags(self, file_path: str, album_name: str = None, cover_path: str = None):
        """同步写入音频标签"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.flac':
                self._write_flac_tags(file_path, album_name, cover_path)
            elif ext == '.mp3':
                self._write_mp3_tags(file_path, album_name, cover_path)
            else:
                logger.debug(f"跳过不支持的格式: {ext}")
                
        except Exception as e:
            logger.error(f"写入音频标签失败 {file_path}: {e}")
    
    def _write_flac_tags(self, file_path: str, album_name: str = None, cover_path: str = None):
        """写入 FLAC 标签"""
        audio = FLAC(file_path)
        
        if album_name:
            audio['album'] = album_name
        
        if cover_path and os.path.exists(cover_path):
            image = Picture()
            image.type = 3  # Front Cover
            image.mime = 'image/png' if cover_path.endswith('.png') else 'image/jpeg'
            
            with open(cover_path, 'rb') as f:
                image.data = f.read()
            
            audio.clear_pictures()
            audio.add_picture(image)
        
        audio.save()
        logger.info(f"✅ FLAC 标签已更新: {os.path.basename(file_path)}")
    
    def _write_mp3_tags(self, file_path: str, album_name: str = None, cover_path: str = None):
        """写入 MP3 标签 (带容错)"""
        try:
            # 尝试作为 MP3 解析 (会检查 MPEG 帧)
            audio = MP3(file_path, ID3=ID3)
        except Exception:
            # 如果音频帧损坏，尝试仅操作 ID3 标签
            try:
                audio = ID3(file_path)
            except Exception:
                # 如果完全没有标签，创建一个新的
                audio = ID3()
        
        # 确保有 tags 属性 (对于 MP3 对象) 或本身就是 ID3 对象
        if isinstance(audio, MP3) and not audio.tags:
            audio.add_tags()
        
        if cover_path and os.path.exists(cover_path):
            mime = 'image/png' if cover_path.endswith('.png') else 'image/jpeg'
            with open(cover_path, 'rb') as f:
                # 无论 audio 是 MP3 还是 ID3，add 方法都可用
                target = audio.tags if isinstance(audio, MP3) else audio
                target.add(APIC(
                    encoding=3,  # UTF-8
                    mime=mime,
                    type=3,  # Front cover
                    desc='Cover',
                    data=f.read()
                ))
        
        if album_name:
            target = audio.tags if isinstance(audio, MP3) else audio
            target.add(TALB(encoding=3, text=album_name))
            
        if isinstance(audio, MP3):
            audio.save()
        else:
            audio.save(file_path)
        logger.info(f"✅ MP3 标签已更新: {os.path.basename(file_path)}")

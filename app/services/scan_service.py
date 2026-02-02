# -*- coding: utf-8 -*-
"""
ScanService - 本地媒体库文件扫描服务

功能：
- 扫描本地音频文件目录 (audio_cache, favorites)
- 发现未入库的歌曲并添加到数据库
- 清理数据库中物理文件已不存在的"死键"
- 支持增量扫描模式
- 提供扫描进度回调

Author: google
Created: 2026-01-30
"""
from typing import Optional, Callable, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import os
from datetime import datetime
from pathlib import Path
import anyio
import logging

from app.repositories.song import SongRepository
from app.repositories.artist import ArtistRepository
from app.models.song import Song, SongSource
from sqlalchemy import select, delete
import hashlib
import binascii  # For manual APIC parsing if needed, though mutagen usually handles it

logger = logging.getLogger(__name__)


class ScanService:
    """本地媒体库文件扫描服务"""
    
    def __init__(self):
        self.supported_extensions = ('.mp3', '.flac', '.m4a', '.wav')
        self.scan_directories = ["audio_cache", "favorites"]
    
    @staticmethod
    def _normalize_cn_brackets(text: str) -> str:
        """
        归一化中文括号为英文括号，并移除所有空格以最大化匹配容错率
        
        Args:
            text: 待归一化的文本
            
        Returns:
            归一化后的文本
        """
        if not text:
            return ""
        text = text.replace('（', '(').replace('）', ')')
        text = text.replace('【', '[').replace('】', ']')
        # 移除所有空格以实现严格的模糊匹配
        return text.replace(" ", "").strip()
    
    async def scan_local_files(
        self,
        db: AsyncSession,
        progress_callback: Optional[Callable[[Dict], None]] = None,
        incremental: bool = False
    ) -> Dict[str, int]:
        """
        全量/增量扫描本地音频文件目录。
        
        该方法负责发现物理磁盘上存在但数据库中缺失的歌曲，并进行“入库”操作。
        它会自动提取音频文件的内嵌标签（封面、歌手、标题、音质）。
        
        优化点:
        - 预加载所有现有的本地源 ID，避免 N+1 查询。
        - 缓存所有歌手信息，减少重复的歌手查询/创建。
        - 延迟提交 (Bulk Commit)，显著提升数千个文件时的扫描性能。
        
        Args:
            db (AsyncSession): 异步数据库会话。
            progress_callback (Callable): 用于实时推送扫描进度的回调函数。
            incremental (bool): 若为 True，则跳过清理阶段（Pruning），仅扫描新文件。
            
        Returns:
            Dict[str, int]: 包含结果统计的字典:
                {
                    "new_files_found": int, # 新增入库数量
                    "removed_files_count": int # 清理失效记录数量
                }
        """
        from mutagen import File as MutagenFile
        from app.models.artist import Artist
        
        new_count = 0
        removed_count = 0
        
        song_repo = SongRepository(db)
        
        # --- 阶段 1: 清理阶段 (Pruning) ---
        if not incremental:
            removed_count = await self._prune_missing_files(db, progress_callback)
        
        # 获取所有现有的本地源 ID
        stmt = select(SongSource.source_id).where(SongSource.source == "local")
        existing_source_ids = set((await db.execute(stmt)).scalars().all())
        logger.info(f"📊 数据库中已存在 {len(existing_source_ids)} 个本地文件记录")

        # 缓存所有歌手信息以减少查询
        all_artists = (await db.execute(select(Artist))).scalars().all()
        artist_map = {a.name: a for a in all_artists}
        
        # --- 阶段 2: 扫描阶段 (Scanning) ---
        for dir_name in self.scan_directories:
            exists = await anyio.to_thread.run_sync(os.path.exists, dir_name)
            if not exists:
                logger.debug(f"目录不存在,跳过: {dir_name}")
                continue
            
            files = await anyio.to_thread.run_sync(os.listdir, dir_name)
            audio_files = [f for f in files if f.endswith(self.supported_extensions)]
            total_files = len(audio_files)
            processed_files = 0
            
            for filename in audio_files:
                processed_files += 1
                
                # 进度回调
                if progress_callback:
                    progress_callback({
                        "stage": "scanning",
                        "directory": dir_name,
                        "current": processed_files,
                        "total": total_files,
                        "filename": filename
                    })
                
                file_path = os.path.join(dir_name, filename).replace("\\", "/")
                
                # 检查是否已处理过 (内存中检查)
                if filename in existing_source_ids:
                    # 如果需要更新音质，可以在这里加逻辑，但通常扫描不需要在这里频繁更新
                    continue
                
                # 发现新文件
                logger.info(f"📂 发现新本地文件: {file_path}")
                metadata = await self._extract_metadata(file_path, filename)
                
                # 获取歌手 (使用缓存)
                artist_name = metadata['artist_name']
                if artist_name in artist_map:
                    artist_obj = artist_map[artist_name]
                else:
                    artist_repo = ArtistRepository(db)
                    artist_obj = await artist_repo.get_or_create_by_name(artist_name)
                    artist_map[artist_name] = artist_obj
                
                # 查找或创建歌曲
                song_obj = await self._find_or_create_song(
                    db, song_repo, metadata, artist_obj
                )
                
                # 创建本地源记录
                data_json = {
                    "quality": metadata.get('quality_info', 'PQ'),
                    "format": os.path.splitext(filename)[1].replace('.', '').upper(),
                    "cover": metadata.get('cover')
                }
                
                new_source = SongSource(
                    song_id=song_obj.id,
                    source="local",
                    source_id=filename,
                    url=file_path,
                    data_json=data_json,
                    cover=data_json.get('cover')
                )
                db.add(new_source)
                existing_source_ids.add(filename)
                new_count += 1
                
                # 每 50 个文件 flush 一次，防止事务过大
                if new_count % 50 == 0:
                    await db.flush()

        # 统一提交
        if new_count > 0:
            await db.commit()
            logger.info(f"💾 扫描完成,已入库 {new_count} 个新文件")
        
        # 最终进度回调
        if progress_callback:
            progress_callback({
                "stage": "completed",
                "new_files_found": new_count,
                "removed_files_count": removed_count
            })
        
        return {
            "new_files_found": new_count,
            "removed_files_count": removed_count
        }
    
    async def _prune_missing_files(
        self,
        db: AsyncSession,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> int:
        """
        清理“死键”：移除数据库中存在但物理磁盘文件已丢失的记录。
        
        如果一首歌曲仅有该本地源且文件丢失，则会连同歌曲记录一起删除；
        如果该歌曲还有其他在线源，则仅清除本地路径并重置状态为 PENDING。
        
        Args:
            db (AsyncSession): 数据库会话。
            progress_callback (Callable): 进度回调。
            
        Returns:
            int: 被清理或修正的记录统计。
        """
        removed_count = 0
        
        # 查找所有标记为本地已下载的歌曲
        stmt = select(Song).where(Song.local_path.isnot(None))
        res = await db.execute(stmt)
        all_local_songs = res.scalars().all()
        
        total_songs = len(all_local_songs)
        
        for idx, song in enumerate(all_local_songs, 1):
            # 进度回调
            if progress_callback:
                progress_callback({
                    "stage": "pruning",
                    "current": idx,
                    "total": total_songs,
                    "song_title": song.title
                })
            
            # 校验物理文件是否存在
            exists = await anyio.to_thread.run_sync(os.path.exists, song.local_path)
            if not exists:
                logger.info(f"🗑️ 发现失效本地文件记录,正在清理: {song.title} ({song.local_path})")
                
                # 1. 移除本地源信息
                source_del_stmt = delete(SongSource).where(
                    SongSource.song_id == song.id,
                    SongSource.source == "local"
                )
                await db.execute(source_del_stmt)
                await db.flush()  # 必须即时刷新，否则下方的查询会包含已删除的源
                
                # 2. 检查是否还有其他在线源
                source_count_stmt = select(SongSource).where(SongSource.song_id == song.id)
                sources = (await db.execute(source_count_stmt)).scalars().all()
                
                if not sources:
                    # 彻底孤立的歌曲记录,直接删除
                    await db.delete(song)
                else:
                    # 仍然有在线监控,只是本地文件丢了,重置状态
                    song.local_path = None
                    song.status = "PENDING"
                
                removed_count += 1
        
        if removed_count > 0:
            await db.commit()
            logger.info(f"✅ 成功清理了 {removed_count} 条失效本地记录")
            
        return removed_count
    
    async def _extract_metadata(self, file_path: str, filename: str) -> Dict[str, any]:
        """
        从音频文件中提取元数据
        
        Args:
            file_path: 文件路径
            filename: 文件名
            
        Returns:
            元数据字典 { title, artist_name, album, publish_time }
        """
        from mutagen import File as MutagenFile
        
        title = None
        artist_name = "Unknown"
        album = None
        publish_time = None
        cover_url = None
        
        try:
            audio_file = MutagenFile(file_path, easy=False)
            if audio_file is not None:
                # 提取封面
                try:
                    cover_data = None
                    # ID3 (MP3)
                    if hasattr(audio_file, 'tags') and hasattr(audio_file.tags, 'getall'):
                        apic_frames = audio_file.tags.getall('APIC')
                        if apic_frames:
                            cover_data = apic_frames[0].data
                    
                    # FLAC / Vorbis
                    if not cover_data and hasattr(audio_file, 'pictures'):
                        if audio_file.pictures:
                            cover_data = audio_file.pictures[0].data
                            
                    # M4A (MP4)
                    if not cover_data and hasattr(audio_file, 'tags') and 'covr' in audio_file.tags:
                        covrs = audio_file.tags['covr']
                        if covrs:
                            cover_data = covrs[0] # bytes

                    if cover_data:
                        # Save to /uploads/covers/
                        md5 = hashlib.md5(cover_data).hexdigest()
                        
                        # Determine Log/Config dir (Hack: assume relative or env)
                        # We use relative path 'uploads' based on main.py logic matching
                        # Better to read global config but for now relative 'uploads' works if CWD is consistent
                        upload_root = "uploads"
                        if os.path.exists("/config"): # Docker env
                             upload_root = "/config/uploads"
                        
                        cover_dir = os.path.join(upload_root, "covers")
                        os.makedirs(cover_dir, exist_ok=True)
                        
                        cover_filename = f"{md5}.jpg" # Assume jpg for simplicity or detect magic
                        # Simple magic check
                        if cover_data.startswith(b'\x89PNG'): cover_filename = f"{md5}.png"
                        
                        save_path = os.path.join(cover_dir, cover_filename)
                        if not os.path.exists(save_path):
                            with open(save_path, "wb") as f:
                                f.write(cover_data)
                        
                        cover_url = f"/uploads/covers/{cover_filename}"
                        
                except Exception as e:
                    logger.warning(f"封面提取失败 {filename}: {e}")

                # 提取基本信息
                # 提取基本信息
                if 'title' in audio_file:
                    title = audio_file['title'][0]
                if 'artist' in audio_file:
                    artist_name = audio_file['artist'][0]
                if 'album' in audio_file:
                    album = audio_file['album'][0]
                
                # 提取日期
                date_str = None
                if 'date' in audio_file:
                    date_str = audio_file['date'][0]
                elif 'TDRC' in audio_file:
                    date_str = str(audio_file['TDRC'])
                elif 'TYER' in audio_file:
                    date_str = str(audio_file['TYER'])
                
                if date_str:
                    try:
                        # 提取前4位数字作为年份
                        year_str = str(date_str)[:4]
                        if year_str.isdigit():
                            publish_time = datetime.strptime(year_str, "%Y")
                    except:
                        pass
        except Exception as e:
            logger.warning(f"❌ 读取标签失败 {filename}: {e}")
        
        # 文件名回退策略
        clean_name = os.path.splitext(filename)[0]
        if not title:
            if " - " in clean_name:
                parts = clean_name.split(" - ", 1)
                artist_name = parts[0].strip()
                title = parts[1].strip()
            else:
                title = clean_name.strip()
        
        return {
            "title": title,
            "artist_name": artist_name,
            "album": album,
            "publish_time": publish_time,
            "cover": cover_url,
            "quality_info": self._analyze_quality(audio_file)
        }

    def _analyze_quality(self, audio_file) -> str:
        """
        优雅的音质判定逻辑 (Elegant Quality Logic):
        
        优先级 (Priority):
        1. HI-RES (HR): 采样率 > 48kHz 或 位深 > 16bit (无论格式)
        2. LOSSLESS (SQ): 无损编码格式 (FLAC/WAV/ALAC/APE) 且非 HR
        3. HIGH QUALITY (HQ): 有损格式 (MP3/AAC/OGG) 且比特率 >= 320kbps (宽松处理 >= 250k)
        4. STANDARD (PQ): 其他情况
        """
        try:
            if not audio_file or not hasattr(audio_file, 'info'):
                return "PQ"
            
            info = audio_file.info
            
            # --- 1. 获取基础音频参数 ---
            sample_rate = getattr(info, 'sample_rate', 0) or 0
            bitrate = getattr(info, 'bitrate', 0) or 0
            bits_per_sample = getattr(info, 'bits_per_sample', 0) or 0 # FLAC/WAV/ALAC usually have this
            
            # --- 2. 判定 Hi-Res (HR) ---
            # 定义: 超过 CD 画质标准 (44.1kHz/16bit)
            # 只要采样率 > 48k (如 96k, 192k) 或者 位深 > 16 (如 24bit) 即视为 HR
            # 注意: 48kHz 16bit 通常也被视为常规无损(SQ)，只有 > 48k 才算 HR
            if sample_rate > 48000 or bits_per_sample > 16:
                return "HR"
            
            # --- 3. 判定无损 (SQ) ---
            # 检查文件容器/编码格式
            # Mutagen 类名通常包含格式信息，如 'mutagen.flac.FLAC', 'mutagen.wave.WAVE'
            file_type = type(audio_file).__name__.lower()
            mime = getattr(audio_file, 'mime', [])
            
            is_lossless_format = (
                'flac' in file_type or 
                'wave' in file_type or 
                'alac' in file_type or
                'monkeysaudio' in file_type or # APE
                'aiff' in file_type
            )
            
            # 也可以通过 mime 判断
            if not is_lossless_format and mime:
                for m in mime:
                    if 'flac' in m or 'wav' in m:
                        is_lossless_format = True
                        break
            
            if is_lossless_format:
                return "SQ"
                
            # --- 4. 判定高品质有损 (HQ) ---
            # 对于 MP3/AAC/OGG
            # 320kbps MP3 (≈320000 bps)
            # AAC 256kbps 实际上音质接近/优于 320k MP3，这里放宽阈值到 256k (250000)
            if bitrate >= 250000:
                return "HQ"
                
            # --- 5. 标准音质 (PQ) ---
            # 128kbps, 192kbps 等
            return "PQ"
            
        except Exception as e:
            logger.warning(f"Quality analysis error: {e}")
            return "PQ"
    
    async def _find_or_create_song(
        self,
        db: AsyncSession,
        song_repo: SongRepository,
        metadata: Dict[str, any],
        artist_obj
    ) -> Song:
        """
        查找或创建歌曲记录 (支持增强模糊匹配)
        
        Args:
            db: 数据库会话
            song_repo: 歌曲仓库
            metadata: 元数据
            artist_obj: 歌手对象
            
        Returns:
            歌曲对象
        """
        title = metadata['title']
        album = metadata['album']
        publish_time = metadata['publish_time']
        
        cover = metadata.get('cover')

        # 精确匹配
        song_obj = await song_repo.get_by_title_artist(title, artist_obj.id)
        
        if not song_obj:
            # 尝试归一化匹配 (解决 "Title (Live)" vs "Title(Live)")
            all_artist_songs = await song_repo.get_by_artist(artist_obj.id)
            norm_local_title = self._normalize_cn_brackets(title).lower().strip()
            
            for existing in all_artist_songs:
                norm_db_title = self._normalize_cn_brackets(existing.title).lower().strip()
                if norm_local_title == norm_db_title:
                    song_obj = existing
                    logger.info(f"  🔗 模糊匹配成功: '{title}' -> '{existing.title}'")
                    break
        
        if not song_obj:
            # 创建新歌曲
            song_obj = Song(
                title=title,
                album=album,
                artist_id=artist_obj.id,
                status="DOWNLOADED",  # 本地文件已存在
                local_path=None,  # 稍后设置
                created_at=datetime.now(),
                publish_time=publish_time,
                cover=cover
            )
            db.add(song_obj)
            await db.flush()  # 获取 ID
        else:
            # 更新现有记录
            if not song_obj.album and album:
                song_obj.album = album
            # 优先使用本地高清封面 (如果是本地文件扫描，说明用户希望以此为准)
            if cover:
                 # Check if current cover is already local to avoid churn? 
                 # But cover filename is hash of content, so it's stable.
                 song_obj.cover = cover
                 
            song_obj.status = "DOWNLOADED"
        
        return song_obj
    
    async def _create_song_source(
        self,
        db: AsyncSession,
        song_obj: Song,
        filename: str,
        file_path: str,
        data_json: Dict = None
    ):
        """
        创建歌曲源记录
        
        Args:
            db: 数据库会话
            song_obj: 歌曲对象
            filename: 文件名
            file_path: 文件路径
            data_json: 额外数据
        """
        # 更新歌曲的本地路径
        if not song_obj.local_path:
            song_obj.local_path = file_path
        
        # 检查该特定的本地文件源是否已存在
        stmt = select(SongSource).where(
            SongSource.song_id == song_obj.id,
            SongSource.source == "local",
            SongSource.source_id == filename
        )
        existing_source = (await db.execute(stmt)).scalar_one_or_none()
        
        if existing_source:
            # 如果存在，更新 data_json (为了修复旧数据)
            if data_json:
                existing_source.data_json = data_json
                existing_source.url = file_path # 确保路径也是最新的
        else:
            # 创建本地源记录
            new_source = SongSource(
                song_id=song_obj.id,
                source="local",
                source_id=filename,
                url=file_path,
                data_json=data_json,
                cover=data_json.get('cover') if data_json else None
            )
            db.add(new_source)

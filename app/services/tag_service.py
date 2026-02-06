# -*- coding: utf-8 -*-
"""
TagService - 音频文件标签管理服务

统一管理 MP3/FLAC 等音频文件的元数据写入。
核心职责：
1. 屏蔽底层 mutagen 差异
2. 强制支持歌词写入 (USLT/SYLT)
3. 统一处理封面嵌入

Author: google
Created: 2026-02-05
"""
import logging
import os
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import anyio

logger = logging.getLogger(__name__)

try:
    import mutagen
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC, USLT, ID3NoHeaderError
    from mutagen.flac import FLAC, Picture
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4, MP4Cover
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    logger.warning("❌ mutagen 未安装, TagService 无法写入文件标签")

class TagService:
    """
    统一的音频标签写入服务
    支持: MP3 (ID3v2.3/2.4), FLAC
    """
    
    @classmethod
    async def write_tags(cls, file_path: str, metadata: Dict[str, Any]) -> bool:
        """
        异步写入标签 (包装同步IO)
        
        Args:
            file_path: 文件绝对路径
            metadata: 元数据字典, 标准键名:
                - title: str
                - artist: str
                - album: str
                - date: str/datetime (YYYY-MM-DD)
                - lyrics: str (纯文本或LRC)
                - cover_data: bytes (封面图片数据)
        
        Returns:
            bool: 是否成功
        """
        if not HAS_MUTAGEN:
            return False
            
        if not os.path.exists(file_path):
            logger.error(f"❌ 文件不存在: {file_path}")
            return False

        # 放到线程池执行阻塞IO
        return await anyio.to_thread.run_sync(cls._sync_write_tags, file_path, metadata)

    @classmethod
    async def read_tags(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """
        异步读取标签 (包装同步IO)
        
        Args:
            file_path: 文件绝对路径
        
        Returns:
            Dict 包含: title, artist, album, date, lyrics
            如果失败返回 None
        """
        if not HAS_MUTAGEN:
            return None
            
        if not os.path.exists(file_path):
            return None

        # 放到线程池执行阻塞IO
        return await anyio.to_thread.run_sync(cls._sync_read_tags, file_path)

    @classmethod
    def _sync_read_tags(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """同步读取标签逻辑"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                return cls._read_mp3(file_path)
            elif ext == '.flac':
                return cls._read_flac(file_path)
            elif ext in ['.m4a', '.mp4']:
                return cls._read_m4a(file_path)
            else:
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ 标签读取失败 [{file_path}]: {e}")
            return None

    @staticmethod
    def _read_mp3(path: str) -> Optional[Dict[str, Any]]:
        """读取 MP3 ID3 标签"""
        try:
            audio = MP3(path, ID3=ID3)
            result = {}
            
            # 基础字段
            result['title'] = str(audio.get('TIT2', '')) or None
            result['artist'] = str(audio.get('TPE1', '')) or None
            result['album'] = str(audio.get('TALB', '')) or None
            result['date'] = str(audio.get('TDRC', '')) or None
            
            # 歌词 (尝试多个语言)
            lyrics = None
            for lang in ['zho', 'eng', 'xxx']:
                uslt = audio.get(f'USLT::{lang}')
                if uslt:
                    lyrics = str(uslt)
                    break
            result['lyrics'] = lyrics
            
            return result
            
        except Exception as e:
            logger.warning(f"MP3 Read Error: {e}")
            return None

    @staticmethod
    def _read_flac(path: str) -> Optional[Dict[str, Any]]:
        """读取 FLAC 标签"""
        try:
            audio = FLAC(path)
            result = {}
            
            result['title'] = audio.get('title', [None])[0]
            result['artist'] = audio.get('artist', [None])[0]
            result['album'] = audio.get('album', [None])[0]
            result['date'] = audio.get('date', [None])[0]
            
            # 歌词 (尝试多个字段)
            lyrics = audio.get('LYRICS', [None])[0] or audio.get('lyrics', [None])[0] or audio.get('UNSYNCEDLYRICS', [None])[0]
            result['lyrics'] = lyrics
            
            return result
            
        except Exception as e:
            logger.warning(f"FLAC Read Error: {e}")
            return None

    @staticmethod
    def _read_m4a(path: str) -> Optional[Dict[str, Any]]:
        """读取 M4A/MP4 标签"""
        try:
            audio = MP4(path)
            result = {}
            
            result['title'] = audio.get('\xa9nam', [None])[0]
            result['artist'] = audio.get('\xa9ART', [None])[0]
            result['album'] = audio.get('\xa9alb', [None])[0]
            result['date'] = audio.get('\xa9day', [None])[0]
            result['lyrics'] = audio.get('\xa9lyr', [None])[0]
            
            return result
            
        except Exception as e:
            logger.warning(f"M4A Read Error: {e}")
            return None

    @classmethod
    def _sync_write_tags(cls, file_path: str, metadata: Dict[str, Any]) -> bool:
        """同步写入逻辑"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                return cls._write_mp3(file_path, metadata)
            elif ext == '.flac':
                return cls._write_flac(file_path, metadata)
            elif ext in ['.m4a', '.mp4']:
                return cls._write_m4a(file_path, metadata)
            else:
                logger.warning(f"⚠️ 不支持的文件格式: {ext}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 标签写入失败 [{file_path}]: {e}", exc_info=True)
            return False

    @staticmethod
    def _write_mp3(path: str, meta: Dict[str, Any]) -> bool:
        """写入 MP3 ID3 标签"""
        try:
            # 1. 加载或创建 ID3
            try:
                audio = ID3(path)
            except ID3NoHeaderError:
                audio = ID3()
            
            # 2. 基础文本
            if meta.get('title'):
                audio.add(TIT2(encoding=3, text=meta['title']))
            if meta.get('artist'):
                audio.add(TPE1(encoding=3, text=meta['artist']))
            if meta.get('album'):
                audio.add(TALB(encoding=3, text=meta['album']))
            if meta.get('date'):
                # 能够处理 datetime 对象或字符串
                d = meta['date']
                if hasattr(d, 'strftime'):
                    d = d.strftime('%Y-%m-%d')
                audio.add(TDRC(encoding=3, text=str(d)))
            
            # 3. 歌词 (USLT)
            if meta.get('lyrics'):
                # encoding=3 (UTF-8)
                # lang='eng' (通用)
                # desc='' (空描述)
                audio.add(USLT(encoding=3, lang='zho', desc='', text=meta['lyrics']))
                # 同时也写一份 eng 以防兼容性
                audio.add(USLT(encoding=3, lang='eng', desc='', text=meta['lyrics']))
                
            # 4. 封面
            if meta.get('cover_data'):
                # 自动检测 mime
                data = meta['cover_data']
                mime = 'image/jpeg'
                if data.startswith(b'\x89PNG'):
                    mime = 'image/png'
                    
                audio.add(APIC(
                    encoding=3,
                    mime=mime,
                    type=3, # Front Cover
                    desc='Cover',
                    data=data
                ))
                
            audio.save(path, v2_version=3) # 保存为 ID3v2.3 (兼容性最好)
            logger.info(f"✅ MP3标签已更新: {os.path.basename(path)} (含歌词: {bool(meta.get('lyrics'))})")
            return True
            
        except Exception as e:
            logger.error(f"MP3 Write Error: {e}")
            raise e

    @staticmethod
    def _write_flac(path: str, meta: Dict[str, Any]) -> bool:
        """写入 FLAC 标签"""
        try:
            audio = FLAC(path)
            
            # FLAC 使用 Vorbis Comment (Key=Value)
            if meta.get('title'):
                audio['title'] = meta['title']
            if meta.get('artist'):
                audio['artist'] = meta['artist']
            if meta.get('album'):
                audio['album'] = meta['album']
            if meta.get('date'):
                d = meta['date']
                if hasattr(d, 'strftime'): d = d.strftime('%Y-%m-%d')
                audio['date'] = str(d)
                
            # 歌词
            if meta.get('lyrics'):
                audio['LYRICS'] = meta['lyrics']
                # 兼容性字段
                audio['UNSYNCEDLYRICS'] = meta['lyrics']
            
            # 封面
            if meta.get('cover_data'):
                data = meta['cover_data']
                image = Picture()
                image.type = 3
                image.desc = 'Cover'
                image.data = data
                
                if data.startswith(b'\x89PNG'):
                    image.mime = 'image/png'
                else:
                    image.mime = 'image/jpeg'
                
                audio.clear_pictures()
                audio.add_picture(image)
                
            audio.save()
            logger.info(f"✅ FLAC标签已更新: {os.path.basename(path)}")
            return True
            
        except Exception as e:
            logger.error(f"FLAC Write Error: {e}")
            raise e

    @staticmethod
    def _write_m4a(path: str, meta: Dict[str, Any]) -> bool:
        """写入 M4A/MP4 标签"""
        try:
            audio = MP4(path)
            
            if meta.get('title'):
                audio['\xa9nam'] = meta['title']
            if meta.get('artist'):
                audio['\xa9ART'] = meta['artist']
            if meta.get('album'):
                audio['\xa9alb'] = meta['album']
            if meta.get('date'):
                d = meta['date']
                if hasattr(d, 'strftime'): d = d.strftime('%Y-%m-%d')
                audio['\xa9day'] = str(d)
                
            # 歌词
            if meta.get('lyrics'):
                audio['\xa9lyr'] = meta['lyrics']
                
            # 封面
            if meta.get('cover_data'):
                data = meta['cover_data']
                covr_format = MP4Cover.FORMAT_JPEG
                if data.startswith(b'\x89PNG'):
                    covr_format = MP4Cover.FORMAT_PNG
                
                audio['covr'] = [MP4Cover(data, imageformat=covr_format)]
                
            audio.save()
            logger.info(f"✅ M4A标签已更新: {os.path.basename(path)}")
            return True
            
        except Exception as e:
            logger.error(f"M4A Write Error: {e}")
            raise e

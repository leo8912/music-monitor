# -*- coding: utf-8 -*-
"""
下载服务 - GDStudio API 专用下载

此模块是下载功能的核心，直接使用 GDStudio API 进行音频搜索和下载。
整合了多源搜索、频率限制、权重评分等功能。

依赖:
- GDStudio API: https://music-api.gdstudio.xyz/api.php
- 频率限制: 5分钟50次请求

Author: google
Created: 2026-01-23
"""
import asyncio
import aiohttp
import aiofiles
import os
import re
import time
import logging
import anyio
from enum import Enum
from typing import Optional, Dict, List, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ============== 繁简转换 ==============
try:
    import opencc
    _opencc_instance = opencc.OpenCC('t2s')
except ImportError:
    _opencc_instance = None
    logger.warning("opencc not installed, 繁简转换功能将不可用")


# ============== 数据类 ==============

class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "PENDING"
    SEARCHING = "SEARCHING"
    DOWNLOADING = "DOWNLOADING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    source: str
    title: str
    artist: List[str]
    album: str
    quality: int = 0
    size: int = 0
    weight_score: int = 0
    cover_url: str = ""


@dataclass
class DownloadTask:
    """下载任务"""
    task_id: str
    title: str
    artist: str
    album: str
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    download_path: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None


# ============== 频率限制器 ==============

class RateLimiter:
    """
    API 频率限制器
    
    GDStudio API 限制: 5分钟50次请求
    """
    def __init__(self, max_tokens: int = 45, refill_period: int = 300):
        self.max_tokens = max_tokens
        self.refill_period = refill_period
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, wait: bool = True) -> bool:
        """获取令牌"""
        async with self._lock:
            self._refill()
            
            if self.tokens > 0:
                self.tokens -= 1
                return True
            
            if not wait:
                return False
            
            wait_time = self.refill_period - (time.time() - self.last_refill)
            if wait_time > 0:
                logger.info(f"频率限制，等待 {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                return await self.acquire(wait=False)
        
        return False
    
    def _refill(self):
        """刷新令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed >= self.refill_period:
            self.tokens = self.max_tokens
            self.last_refill = now


# ============== 下载服务 ==============

class DownloadService:
    """
    下载服务 - 使用 GDStudio API 搜索和下载音频
    
    功能:
    - 多源搜索 (kuwo, netease, joox 等)
    - 权重评分算法匹配最佳结果
    - 频率限制 (5分钟45次)
    - 自动下载和保存
    """
    
    API_BASE = "https://music-api.gdstudio.xyz/api.php"
    
    # 搜索优先级顺序
    SEARCH_PRIORITY = [
        "kuwo", "netease", "joox", "kugou", "migu", 
        "tencent", "ximalaya"
    ]
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            from core.config_manager import get_config_manager
            storage_cfg = get_config_manager().get("storage", {})
            cache_dir = storage_cfg.get("cache_dir", "audio_cache")
            
        self.cache_dir = cache_dir
        self.rate_limiter = RateLimiter(max_tokens=45, refill_period=300)
        self._tasks: Dict[str, DownloadTask] = {}
        self._execution_locks: Dict[str, asyncio.Event] = {}
        
        # 确保缓存目录存在
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
    
    # ---------- 搜索相关 ----------
    
    def _convert_traditional_to_simplified(self, text: str) -> str:
        """繁体转简体"""
        if not _opencc_instance or not text:
            return text
        try:
            return _opencc_instance.convert(text)
        except Exception:
            return text
    
    def _calculate_weight_score(self, result: SearchResult, 
                                 expected_title: str, 
                                 expected_artist: str) -> int:
        """计算搜索结果的权重分数"""
        score = 0
        
        result_title = result.title.lower().strip()
        result_artist = " ".join(result.artist).lower().strip() if result.artist else ""
        expected_title = expected_title.lower().strip()
        expected_artist = expected_artist.lower().strip()
        
        # 检查翻唱/器乐版本
        is_cover = any(word in result_title for word in 
                       ['cover', '翻唱', '(cover)', '原唱'])
        is_instrumental = any(word in result_title for word in 
                              ['钢琴', 'instrumental', '纯音乐', 'piano'])
        
        # 歌曲名匹配
        if expected_title == result_title:
            score += 1000
        elif expected_title in result_title:
            score += 500
        
        # 歌手匹配
        if expected_artist == result_artist:
            score += 1000
        elif expected_artist in result_artist:
            score += 500
        
        # 降低翻唱/器乐版本分数
        if is_cover:
            score -= 200
        if is_instrumental:
            score -= 300
        
        return score
    
    async def search_single_source(self, title: str, artist: str, 
                                    source: str, count: int = 5) -> List[SearchResult]:
        """在单个源中搜索"""
        if not await self.rate_limiter.acquire(wait=True):
            logger.warning(f"频率限制: {title} {artist}")
            return []
        
        # 清理搜索关键词
        clean_title = re.sub(r'[<>:"/\\|?*]', ' ', title).strip()
        clean_artist = re.sub(r'[<>:"/\\|?*]', ' ', artist).strip()
        keyword = f"{clean_title} {clean_artist}"
        
        params = {
            "types": "search",
            "count": count,
            "source": source,
            "pages": 1,
            "name": keyword
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        
        logger.info(f"搜索 [{source}]: {keyword}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_BASE, params=params, 
                                       headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(f"搜索失败 [{source}], 状态码: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    if not data:
                        return []
                    
                    results = []
                    for item in data:
                        # JOOX 源繁简转换
                        if source == "joox":
                            item["name"] = self._convert_traditional_to_simplified(
                                item.get("name", ""))
                            if isinstance(item.get("artist"), list):
                                item["artist"] = [
                                    self._convert_traditional_to_simplified(str(a)) 
                                    for a in item["artist"]
                                ]
                        
                        result = SearchResult(
                            id=str(item.get("id", "")),
                            source=source,
                            title=item.get("name", ""),
                            artist=item.get("artist", []),
                            album=item.get("album", ""),
                            quality=int(item.get("br", 0)),
                            size=int(item.get("size", 0))
                        )
                        # Store image: Construct using proxy if direct pic is missing
                        # Since types=pic returns JSON, we use our backend proxy /api/discovery/cover
                        direct_pic = item.get("pic")
                        pic_id = item.get("pic_id")
                        
                        if direct_pic and direct_pic.startswith("http"):
                            result.cover_url = direct_pic
                        else:
                            # Use our backend proxy
                            # The track ID itself is often a good enough ID for the pic API
                            target_id = pic_id if pic_id else result.id
                            result.cover_url = f"/api/discovery/cover?source={source}&id={target_id}"
                        
                        result.weight_score = self._calculate_weight_score(
                            result, title, artist)
                        results.append(result)
                    
                    return results
        except Exception as e:
            logger.warning(f"搜索异常 [{source}]: {e}")
            return []
    
    async def find_candidates(self, title: str, artist: str, 
                               album: str = None, limit_per_source: int = 2) -> List[SearchResult]:
        """
        从多个源搜集候选列表，按分数排序 (瀑布重试核心)
        """
        all_candidates = []
        # 并发搜索多个源 (受限于频率限制，我们依然顺序或分批)
        for source in self.SEARCH_PRIORITY:
            results = await self.search_single_source(title, artist, source, count=5)
            if results:
                # 仅保留匹配度高的前几个候选
                valid = [r for r in results[:limit_per_source] if r.weight_score >= 500]
                all_candidates.extend(valid)
        
        # 全局按分数降序排列
        all_candidates.sort(key=lambda x: x.weight_score, reverse=True)
        return all_candidates

    async def find_best_match(self, title: str, artist: str, 
                               album: str = None) -> Optional[SearchResult]:
        """按优先级搜索，返回最佳匹配结果 (保留接口，内部调用新逻辑)"""
        candidates = await self.find_candidates(title, artist, album, limit_per_source=1)
        return candidates[0] if candidates else None

    async def probe_available_qualities(self, source: str, track_id: str) -> List[Dict]:
        """并发探测该歌曲在不同音质下的可用性"""
        qualities = [128, 320, 999]
        tasks = []
        
        async with aiohttp.ClientSession() as session:
            for q in qualities:
                tasks.append(self._probe_single_quality(session, source, track_id, q))
            results = await asyncio.gather(*tasks)
            
        return [r for r in results if r["available"]]

    async def _probe_single_quality(self, session, source, track_id, br) -> Dict:
        """探测单个音质"""
        params = {
            "types": "url",
            "source": source,
            "id": track_id,
            "br": br
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        try:
            async with session.get(self.API_BASE, params=params, headers=headers, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and data.get("url"):
                        return {
                            "quality": br,
                            "actual_br": data.get("br", br),
                            "size": data.get("size", 0),
                            "available": True
                        }
        except Exception:
            pass
            
        return {"quality": br, "available": False}
    
    # ---------- 下载相关 ----------
    
    async def get_audio_url(self, source: str, track_id: str, 
                            quality: int = 999) -> Optional[Dict]:
        """获取音频下载链接 (带自动降质重试)"""
        # 定义重试序列
        quality_fallback = [999, 320, 192, 128]
        
        # 如果初始请求不在序列中，将其插入头部
        if quality not in quality_fallback:
            quality_fallback.insert(0, quality)
        else:
            # 调整起始点
            idx = quality_fallback.index(quality)
            quality_fallback = quality_fallback[idx:]

        for br in quality_fallback:
            # [Fix] Retry each quality level 3 times before downgrading
            for attempt in range(3):
                if not await self.rate_limiter.acquire(wait=True):
                    continue
                
                params = {
                    "types": "url",
                    "source": source,
                    "id": track_id,
                    "br": br
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
                }
                
                try:
                    retry_suffix = f"(Attempt {attempt+1}/3)" if attempt > 0 else ""
                    logger.info(f"正在尝试获取音质 {br} [{source}:{track_id}] {retry_suffix}")
                    async with aiohttp.ClientSession() as session:
                        async with session.get(self.API_BASE, params=params, 
                                               headers=headers, timeout=15) as resp:
                            if resp.status != 200:
                                logger.warning(f"音质 {br} 获取失败, 状态码: {resp.status}")
                                if attempt < 2: await asyncio.sleep(1)
                                continue
                            
                            data = await resp.json()
                            if data and data.get("url"):
                                return {
                                    "url": data["url"],
                                    "br": data.get("br", br),
                                    "size": data.get("size", 0),
                                    "title": data.get("name"),   # GDStudio returns name for title
                                    "artist": data.get("artist"),
                                    "pic": data.get("pic")
                                }
                            else:
                                # URL is empty, strictly implies this quality is unavailable
                                logger.info(f"音质 {br} 数据为空")
                                # If data implies unavailable, maybe don't retry? 
                                # But API might be flaky, so we retry unless it's a hard 404 meaning "not exists"
                                # For now, let's retry to be safe as user requested stability.
                                if attempt < 2: await asyncio.sleep(1)
                                
                except Exception as e:
                    logger.error(f"获取音频链接异常 ({br}): {e}")
                    if attempt < 2: await asyncio.sleep(1)
            
            logger.info(f"音质 {br} 尝试3次均失败，尝试更低音质...")
        
        return None
    async def download_file(self, url: str, filepath: str,
                            progress_callback: Callable[[float], Awaitable[None]] = None) -> bool:
        """下载文件到指定路径"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        # [New] Add simple retry for network flakes
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=300) as resp:
                        if resp.status != 200:
                            logger.error(f"下载失败 (尝试 {attempt+1}), 状态码: {resp.status}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1)
                                continue
                            return False
                        
                        total_size = int(resp.headers.get('content-length', 0))
                        downloaded = 0
                        
                        temp_path = filepath + ".tmp"
                        async with aiofiles.open(temp_path, 'wb') as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                await f.write(chunk)
                                downloaded += len(chunk)
                                
                                if progress_callback and total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    await progress_callback(progress)
                        
                        if await anyio.to_thread.run_sync(os.path.exists, filepath):
                            await anyio.to_thread.run_sync(os.remove, filepath)
                        await anyio.to_thread.run_sync(os.rename, temp_path, filepath)
                        return True
                        
            except Exception as e:
                logger.error(f"下载异常 (尝试 {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                # 清理
                temp_path = filepath + ".tmp"
                exists = await anyio.to_thread.run_sync(os.path.exists, temp_path)
                if exists:
                    await anyio.to_thread.run_sync(os.remove, temp_path)
                return False
        return False
    
    # ---------- 主下载方法 ----------
    
    async def download_audio(self, 
                             title: str, 
                             artist: str, 
                             album: str = "",
                             quality: int = 999,
                             progress_callback: Callable[[str], Awaitable[None]] = None) -> Optional[Dict]:
        """
        主下载方法
        
        Args:
            title: 歌曲名
            artist: 歌手名
            album: 专辑名 (可选)
            quality: 音质 (128/192/320/740/999)
            progress_callback: 进度回调
        
        Returns:
            下载结果字典，包含 local_path, quality, size, format
        """
        task_id = f"{artist}_{title}".replace(" ", "_")
        
        # 防止重复下载
        if task_id in self._execution_locks:
            await self._execution_locks[task_id].wait()
            # 返回已有结果
            if task_id in self._tasks and self._tasks[task_id].download_path:
                return {"local_path": self._tasks[task_id].download_path}
        
        self._execution_locks[task_id] = asyncio.Event()
        
        try:
            # 创建任务
            task = DownloadTask(
                task_id=task_id, title=title, artist=artist, album=album,
                created_at=datetime.now()
            )
            self._tasks[task_id] = task
            
            # 1. 搜集候选池 (瀑布式重试基础)
            task.status = DownloadStatus.SEARCHING
            if progress_callback:
                await progress_callback("🔍 搜集全球音源候选池...")
            
            candidates = await self.find_candidates(title, artist, album)
            if not candidates:
                if progress_callback:
                    await progress_callback("❌ 未找到匹配音源")
                return None
            
            # 2. 瀑布式尝试下载
            for idx, search_result in enumerate(candidates):
                try:
                    if progress_callback:
                        retry_msg = f" (尝试 {idx+1}/{len(candidates)})" if idx > 0 else ""
                        await progress_callback(f"🎵 尝试音源: [{search_result.source}]{retry_msg}")
                    
                    audio_info = await self.get_audio_url(search_result.source, search_result.id, quality)
                    if not audio_info:
                        continue
                    
                    # 生成文件名
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    safe_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)
                    ext = "flac" if audio_info.get("br", 0) >= 740 else "mp3"
                    filename = f"{safe_artist} - {safe_title}.{ext}"
                    filepath = os.path.join(self.cache_dir, filename)
                    
                    # 定义内部进度逻辑
                    async def update_progress(pct):
                        if progress_callback:
                            await progress_callback(f"⬇️ 下载中... {pct:.0f}%")
                    
                    # 尝试下载
                    success = await self.download_file(audio_info["url"], filepath, update_progress)
                    if success:
                        task.status = DownloadStatus.SUCCESS
                        task.download_path = filename
                        if progress_callback:
                            await progress_callback("✅ 下载完成！")
                        
                        return {
                            "local_path": filename,
                            "quality": audio_info.get("br", quality),
                            "size": audio_info.get("size", 0),
                            "format": ext,
                            "source": search_result.source
                        }
                    
                except Exception as e:
                    logger.warning(f"候选源尝试失败 ({search_result.source}): {e}")
                    continue
            
            # 如果走到这里，说明全部候选都失败了
            task.status = DownloadStatus.FAILED
            if progress_callback:
                await progress_callback("❌ 尝试了所有音源，均下载失败")
            return None
            
        except Exception as e:
            logger.error(f"下载失败: {e}", exc_info=True)
            if task_id in self._tasks:
                self._tasks[task_id].status = DownloadStatus.FAILED
                self._tasks[task_id].error_message = str(e)
            if progress_callback:
                await progress_callback(f"❌ 下载失败: {e}")
            return None
            
        finally:
            if task_id in self._execution_locks:
                self._execution_locks[task_id].set()
                del self._execution_locks[task_id]
    
    def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """获取下载任务状态"""
        return self._tasks.get(task_id)
    
    async def get_download_status(self, task_id: str) -> Optional[Dict]:
        """获取下载状态 (异步版本)"""
        task = self.get_task_status(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "error_message": task.error_message,
            "download_path": task.download_path
        }
    
    async def retry_failed_download(self, task_id: str) -> bool:
        """重试失败的下载"""
        task = self.get_task_status(task_id)
        if not task or task.status != DownloadStatus.FAILED:
            return False
        
        # 重新执行下载
        result = await self.download_audio(
            title=task.title,
            artist=task.artist,
            album=task.album
        )
        return result is not None
    
    async def get_play_url(self, source: str, track_id: str) -> Optional[str]:
        """获取播放链接"""
        return await self.get_audio_url(source, track_id)
    
    def get_local_file(self, artist: str, title: str) -> Optional[str]:
        """检查本地是否已有文件"""
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)
        
        for ext in ['flac', 'mp3', 'wav', 'm4a']:
            filename = f"{safe_artist} - {safe_title}.{ext}"
            filepath = os.path.join(self.cache_dir, filename)
            # 注意: 此处为同步方法 get_local_file，通常在同步 context 调用，保持原有逻辑或针对特定场景优化
            if os.path.exists(filepath):
                return filepath
        
        return None


# ============== 重试管理器 ==============

class RetryManager:
    """简单的重试管理器"""
    
    def get_retry_options(self) -> Dict:
        """获取重试配置选项"""
        return {
            "max_retries": 3,
            "retry_delay": 5,
            "sources": ["kuwo", "netease", "joox", "kugou", "migu"]
        }


# 为 DownloadService 添加 retry_manager 属性
DownloadService.retry_manager = RetryManager()


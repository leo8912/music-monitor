# -*- coding: utf-8 -*-
"""
MediaAssetService - 媒体资源本地化服务

统一负责歌单封面 (cover) 与歌手头像 (avatar) 的本地化：
- DB 中资源字段只认两种状态：本地路径 /uploads/...（终态）或空（待补）
- 远程 URL 只是中间态，任何写入点都应通过 ensure_* 落地为本地文件

用法：
    from app.services.media_asset_service import MediaAssetService
    svc = MediaAssetService()
    ok = await svc.ensure_cover(song, candidate_url)
    ok = await svc.ensure_avatar(artist, candidate_url)
    ok = await svc.ensure_localized(entity)

Author: refactor
"""
import logging
import os
import hashlib
import json
import urllib.parse as urlparse
from typing import Optional, Tuple

from app.container import get_aggregator
from app.models.artist import Artist
from app.models.song import Song

logger = logging.getLogger(__name__)


class MediaAssetService:
    """媒体资源本地化服务"""

    def __init__(self):
        if os.path.exists("/config"):
            self.upload_root = "/config/uploads"
        else:
            self.upload_root = os.path.join(os.getcwd(), "uploads")
        self.cover_dir = os.path.join(self.upload_root, "covers")
        self.avatar_dir = os.path.join(self.upload_root, "avatars")
        os.makedirs(self.cover_dir, exist_ok=True)
        os.makedirs(self.avatar_dir, exist_ok=True)
        self._aggregator = None

    @property
    def aggregator(self):
        if self._aggregator is None:
            self._aggregator = get_aggregator()
        return self._aggregator

    # ------------------------------------------------------------------
    # 对外入口
    # ------------------------------------------------------------------

    async def ensure_cover(self, song, candidate_url: Optional[str] = None) -> bool:
        """
        确保歌曲封面已本地化到 /uploads/covers/。
        成功把 song.cover 写成 /uploads/ 路径，返回 True。
        """
        url = candidate_url or getattr(song, "cover", None)
        if not url:
            return False

        # 已是本地路径 → 校验文件存在即可
        if str(url).startswith("/uploads/"):
            return self._local_file_exists(url)

        return await self._localize(song, "cover", url, "covers")

    async def ensure_avatar(self, artist, candidate_url: Optional[str] = None,
                           sources: Optional[list] = None) -> bool:
        """
        确保歌手头像已本地化到 /uploads/avatars/。
        已本地化 / 有候选URL / 空值搜索补源 三种情况统一处理。
        成功会把 artist.avatar 及所有 ArtistSource.avatar 写成 /uploads/ 路径。

        Args:
            artist: Artist 实例
            candidate_url: 优先使用的候选头像 URL
            sources: 显式传入已加载的 ArtistSource 列表（避免异步懒加载 MissingGreenlet）
        """
        url = candidate_url or getattr(artist, "avatar", None) or None

        # 已是本地路径 → 校验文件
        if url and str(url).startswith("/uploads/"):
            return self._local_file_exists(url)

        # 空值 → 尝试补源
        if not url:
            url = await self._resolve_avatar_source(artist, sources)
            if not url:
                logger.info(f"🎨 无可用头像源: {artist.name}")
                return False

        ok = await self._localize_avatar(artist, url, sources)
        if ok:
            logger.info("✅ 歌手头像本地化成功: %s -> %s", artist.name, artist.avatar)
        return ok

    async def ensure_localized(self, entity) -> bool:
        """按实体类型统一分发本地化。"""
        # artist / song 都由其 attr 判别
        if isinstance(entity, Artist):
            return await self.ensure_avatar(entity)
        if isinstance(entity, Song):
            return await self.ensure_cover(entity)
        return False

    # ------------------------------------------------------------------
    # 头像补源
    # ------------------------------------------------------------------

    async def _resolve_avatar_source(self, artist, sources: Optional[list] = None) -> Optional[str]:
        """
        头像补源顺序：
        ① 已关联的 ArtistSource.avatar（单个来源的头像更准确）
        ② aggregator.search_artist 搜索，取第一个带头像的候选
        """
        src_list = sources if sources is not None else (getattr(artist, "sources", None) or [])
        for src in src_list:
            av = getattr(src, "avatar", None)
            if av and str(av).startswith("http"):
                return str(av)

        try:
            results = await self.aggregator.search_artist(artist.name, limit=8)
            for r in results:
                av = getattr(r, "avatar", None)
                if av and str(av).startswith("http"):
                    return str(av)
        except Exception as e:
            logger.warning(f"🎨 搜索歌手头像失败 ({artist.name}): {e}")

        return None

    # ------------------------------------------------------------------
    # 本地化实现
    # ------------------------------------------------------------------

    async def _localize(self, entity, attr: str, url: str, folder: str) -> bool:
        """下载 url 到 folder，成功后回写 entity.<attr> 为 /uploads/... 路径。"""
        web_url, local_path = await self._download(url, folder)
        if not web_url or not local_path:
            logger.warning(f"下载图片失败: {url}")
            return False
        setattr(entity, attr, web_url)
        return True

    async def _localize_avatar(self, artist, url: str, sources: Optional[list] = None) -> bool:
        """头像本地化并同步到所有 ArtistSource。"""
        web_url, local_path = await self._download(url, "avatars")
        if not web_url or not local_path:
            return False
        artist.avatar = web_url
        src_list = sources if sources is not None else (getattr(artist, "sources", None) or [])
        for src in src_list:
            src.avatar = web_url
        return True

    def _local_file_exists(self, web_url: str) -> bool:
        """校验 /uploads/... 对应的本地文件是否存在。"""
        parts = web_url.split("/")
        # web_url 形如 /uploads/covers/x.jpg → 相对 upload_root 是 covers/x.jpg
        if len(parts) >= 3 and parts[1] == "uploads":
            rel_path = os.path.join(*parts[2:])
        else:
            rel_path = os.path.basename(web_url)
        full = os.path.join(self.upload_root, rel_path)
        exists = os.path.exists(full)
        if not exists:
            logger.warning(f"🖼️ 本地资源缺失: {web_url}")
        return exists

    async def _download(self, url: str, folder: str = "covers") -> Tuple[Optional[str], Optional[str]]:
        """
        下载图片并保存到指定目录。
        支持代理 URL (/api/discovery/cover) 与 GDStudio JSON 包裹响应。
        返回 (web_url, local_path)，失败返回 (None, None)。
        """
        try:
            import aiohttp

            # 处理代理 URL: /api/discovery/cover?source=xxx&id=yyy
            if str(url).startswith("/api/discovery/cover"):
                parsed = urlparse.urlparse(url)
                qs = urlparse.parse_qs(parsed.query)
                source = qs.get("source", [""])[0]
                target_id = qs.get("id", [""])[0]
                if source and target_id:
                    url = f"https://music-api.gdstudio.xyz/api.php?types=pic&source={source}&id={target_id}"

            ext = "png" if ".png" in url.lower() else "jpg"
            md5 = hashlib.md5(url.encode()).hexdigest()
            filename = f"{md5}.{ext}"

            target_dir = os.path.join(self.upload_root, folder)
            os.makedirs(target_dir, exist_ok=True)

            save_path = os.path.join(target_dir, filename)
            web_url = f"/uploads/{folder}/{filename}"

            if os.path.exists(save_path):
                return web_url, save_path

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        if b'{"url":' in content[:100]:
                            try:
                                data = json.loads(content.decode("utf-8"))
                                img_real_url = data.get("url")
                                if img_real_url:
                                    return await self._download(img_real_url, folder)
                            except Exception:
                                pass
                        with open(save_path, "wb") as f:
                            f.write(content)
                        return web_url, save_path
                    logger.warning(f"下载图片失败 ({url}): HTTP {resp.status}")
                    return None, None
        except Exception as e:
            logger.warning(f"下载图片失败 ({url}): {e}")
            return None, None

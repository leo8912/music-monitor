# -*- coding: utf-8 -*-
"""
Discovery API路由 - 提供在线音乐发现相关API端点

此文件定义了发现相关的API路由，包括：
- 综合搜索
- 歌手搜索

Author: google
Created: 2026-01-23
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_async_session
from app.container import get_download_service, get_aggregator
from app.dependencies import require_auth
from app.schemas import (
    SongInfoResponse, ArtistInfoResponse, ArtistOnlineSongsResponse,
    LocalizeAvatarResponse, SearchDownloadItemResponse, ProbeQualityResponse,
    ApiHealthItemResponse, ApiHealthResponse,
)

router = APIRouter(prefix="/api/discovery", tags=["discovery"])
logger = logging.getLogger(__name__)

# ========== GDStudio API 健康检查 ==========
# 网页文档 (2026-06-26) 列出的全部音乐源; 逐源探测 search/url 接口有效性
_HEALTH_SOURCES = [
    "netease", "tencent", "kuwo", "tidal", "qobuz",
    "joox", "bilibili", "apple", "ytmusic", "spotify",
]
_HEALTH_API = "https://music-api.gdstudio.xyz/api.php"
_HEALTH_KEYWORD = "月亮代表我的心 邓丽君"  # 非周杰伦, 版权安全, 多数源可命中
_HEALTH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
}
_HEALTH_TTL = 180  # 秒; 缓存避免频繁触发 API 限流 (50次/5min)
_health_cache: Optional[ApiHealthResponse] = None
_health_cache_ts: float = 0.0
_health_lock = asyncio.Lock()


async def _probe_one_source(source: str) -> ApiHealthItemResponse:
    """探测单个音乐源的 search + url 接口"""
    import aiohttp

    item = ApiHealthItemResponse(source=source, search_status="error", message="")
    first_track_id = ""

    # --- 探测 search 接口 (count=1) ---
    t0 = time.monotonic()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _HEALTH_API,
                params={"types": "search", "source": source,
                        "name": _HEALTH_KEYWORD, "count": 1, "pages": 1},
                headers=_HEALTH_HEADERS, timeout=10,
            ) as resp:
                status = resp.status
                if status == 200:
                    data = await resp.json()
                    data_list = data if isinstance(data, list) else []
                    item.search_count = len(data_list)
                    item.search_status = "ok" if data_list else "empty"
                    if data_list:
                        first_track_id = str(data_list[0].get("id", ""))
                elif status == 400:
                    item.search_status = "unsupported"
                    try:
                        body = await resp.json()
                        if isinstance(body, dict) and body.get("detail"):
                            item.message = str(body["detail"])
                    except Exception:
                        pass
                else:
                    item.search_status = "error"
                    item.message = f"HTTP {status}"
    except Exception as e:
        item.search_status = "error"
        item.message = str(e)[:120]
    item.search_latency_ms = int((time.monotonic() - t0) * 1000)

    # --- 若 search 可用, 用返回的真实 id 探测 url 接口 (br=320) ---
    if item.search_status == "ok" and first_track_id:
        url_status = "skip"
        url_latency = 0
        try:
            t1 = time.monotonic()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    _HEALTH_API,
                    params={"types": "url", "source": source,
                            "id": first_track_id, "br": 320},
                    headers=_HEALTH_HEADERS, timeout=10,
                ) as url_resp:
                    url_latency = int((time.monotonic() - t1) * 1000)
                    if url_resp.status == 200:
                        url_data = await url_resp.json()
                        if isinstance(url_data, dict) and url_data.get("url"):
                            url_status = "ok"
                        else:
                            url_status = "empty"
                    elif url_resp.status == 400:
                        url_status = "unsupported"
                    else:
                        url_status = "error"
        except Exception:
            url_status = "error"
        item.url_status = url_status
        item.url_latency_ms = url_latency

    return item


async def _probe_health_sources() -> ApiHealthResponse:
    """逐源探测 search + url 接口, 返回健康检查结果"""
    items: list[ApiHealthItemResponse] = []

    for source in _HEALTH_SOURCES:
        items.append(await _probe_one_source(source))
        # 节流: 避免触发 50次/5min 限流
        await asyncio.sleep(0.3)

    return ApiHealthResponse(
        tested_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        cached=False,
        ttl_seconds=_HEALTH_TTL,
        total=len(items),
        items=items,
    )


@router.get("/api_health", response_model=ApiHealthResponse, dependencies=[Depends(require_auth)])
async def api_health_endpoint(
    refresh: int = Query(0, description="1=强制重新探测, 忽略缓存"),
    source: Optional[str] = Query(None, description="只探测指定音乐源 (如 netease), 忽略缓存"),
):
    """
    GDStudio API 接口有效性检查

    对网页文档列出的全部音乐源逐源探测 search(搜索) 与 url(取链接) 接口,
    用于在 Web 界面监控各源当前是否可用。结果缓存 _HEALTH_TTL 秒,
    避免频繁点击触发外部 API 限流 (50次/5min)。refresh=1 强制重测。

    指定 source 参数时仅探测该源 (单源测试, 不走缓存), 供界面逐行"测试"按钮使用。
    """
    if source:
        if source not in _HEALTH_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"未知音乐源: {source}, 可选: {', '.join(_HEALTH_SOURCES)}"
            )
        item = await _probe_one_source(source)
        logger.info("GDStudio API 单源健康检查: %s -> search=%s url=%s",
                    source, item.search_status, item.url_status)
        return ApiHealthResponse(
            tested_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            cached=False,
            ttl_seconds=_HEALTH_TTL,
            total=1,
            items=[item],
        )

    global _health_cache, _health_cache_ts

    # 有缓存且未过期 → 直接返回 (不重复探测)
    if not refresh and _health_cache is not None:
        if time.time() - _health_cache_ts < _HEALTH_TTL:
            _health_cache.cached = True
            return _health_cache

    # 并发请求下用锁避免重复探测
    async with _health_lock:
        if not refresh and _health_cache is not None:
            if time.time() - _health_cache_ts < _HEALTH_TTL:
                _health_cache.cached = True
                return _health_cache

        logger.info("开始 GDStudio API 健康检查 (refresh=%s)", bool(refresh))
        result = await _probe_health_sources()
        _health_cache = result
        _health_cache_ts = time.time()
        return result


@router.get("/search", response_model=list[SongInfoResponse], dependencies=[Depends(require_auth)])
async def search_discovery(
    keyword: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    artist: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50)
):
    """
    搜索在线歌曲

    使用 music_providers 聚合多个来源的搜索结果。
    支持直接 keyword 搜索，也支持 title+artist 组合。
    """
    try:

        if not keyword:
            if title and artist:
                keyword = f"{title} {artist}"
            elif title:
                keyword = title
            elif artist:
                keyword = artist
            else:
                raise HTTPException(status_code=400, detail="Missing parameter: keyword or (title, artist)")

        aggregator = get_aggregator()
        results = await aggregator.search_song(keyword, limit=limit)

        # 转换为字典格式
        return [song.to_dict() for song in results]
    except Exception:
        raise HTTPException(status_code=500, detail="搜索失败: 服务器内部错误, 请查看日志")


@router.get("/search_download", response_model=list[SearchDownloadItemResponse], dependencies=[Depends(require_auth)])
async def search_download(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=100)
):
    """
    搜索可供下载的音源 (GDStudio API)

    专门用于"重新下载"功能，确保搜索结果 ID 与下载接口兼容。
    """
    try:
        service = get_download_service()

        # 为了提高效率，我们并行搜索几个主要源 (与网页文档稳定源一致:
        # netease/joox/bilibili; kugou/migu/ximalaya 已废弃, tencent 等未开放)
        sources = ["netease", "joox", "bilibili"]

        tasks = []
        # 将关键词拆分为 title 和 artist (简单拆分，GDStudio 内部会再处理)
        # 假设关键词通常是 "Artist - Title" 或其变体
        # 如果关键词包含 " - ", 则尝试拆分
        parts = keyword.split(" - ", 1)
        if len(parts) == 2:
            artist, title = parts[0], parts[1]
        else:
            artist, title = "", keyword

        for source in sources:
            tasks.append(service.search_single_source(title, artist, source, count=limit))

        # 执行聚合搜索
        results_nested = await asyncio.gather(*tasks)

        # 展平并按权重排序
        all_results = []
        for source_results in results_nested:
            all_results.extend(source_results)

        # 按权重分数排序 (DownloadService 内部计算了分数)
        all_results.sort(key=lambda x: x.weight_score, reverse=True)

        # 转换为前端需要的格式 (兼容 SongInfo 字典结构)
        output = []
        for r in all_results:
            output.append({
                "id": r.id,
                "source": r.source,
                "title": r.title,
                "artist": ", ".join(r.artist) if isinstance(r.artist, list) else r.artist,
                "album": r.album,
                "cover_url": r.cover_url,
                "quality": r.quality,
                "size": r.size,
                "publish_time": ""
            })

        return output[:20] # 返回前 20 条最相关的
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")

@router.get("/probe_qualities", response_model=list[ProbeQualityResponse], dependencies=[Depends(require_auth)])
async def probe_qualities_endpoint(
    source: str,
    id: str
):
    """
    实时探测该歌曲在不同音质下的可用性
    """
    try:
        service = get_download_service()
        results = await service.probe_available_qualities(source, id)
        return results
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")


@router.get("/cover")
async def cover_proxy_endpoint(
    source: str,
    id: str
):
    """
    由于 GDStudio 的 types=pic 返回的是 JSON 链接，我们需要一个代理来处理重定向，
    以便前端可以直接在 <img> 标签中使用。
    """
    try:
        url = f"https://music-api.gdstudio.xyz/api.php?types=pic&source={source}&id={id}"
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    img_url = data.get("url")
                    if img_url:
                        from fastapi.responses import RedirectResponse
                        return RedirectResponse(img_url)

        # Fallback to a default placeholder or 404
        raise HTTPException(status_code=404, detail="Cover not found")
    except Exception as e:
        logger.error(f"Cover proxy error: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")


@router.post("/localize_artist_avatar", response_model=LocalizeAvatarResponse, dependencies=[Depends(require_auth)])
async def localize_artist_avatar_endpoint(
    artist_name: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    前端兜底：按歌手名确保头像本地化到 /uploads/avatars/。
    返回该歌手最终的 avatar 字段（本地路径或空）。
    """
    try:
        from app.models.artist import Artist
        from app.services.media_asset_service import MediaAssetService
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Artist)
            .options(selectinload(Artist.sources))
            .where(Artist.name == artist_name)
        )
        result = await db.execute(stmt)
        artist = result.scalars().first()
        if not artist:
            raise HTTPException(status_code=404, detail="未找到该艺人")

        svc = MediaAssetService()
        ok = await svc.ensure_avatar(artist, sources=list(artist.sources))
        if ok:
            await db.commit()
        return {"name": artist.name, "avatar": artist.avatar or ""}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Localize artist avatar error: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")


@router.get("/search_artists", response_model=list[ArtistInfoResponse], dependencies=[Depends(require_auth)])
async def search_artists(keyword: str):
    """
    搜索歌手

    在多个平台搜索歌手,返回包含头像、平台等信息的结果列表。
    """
    try:
        aggregator = get_aggregator()
        results = await aggregator.search_artist(keyword, limit=10)

        return [artist.to_dict() for artist in results]
    except Exception:
        raise HTTPException(status_code=500, detail="搜索歌手失败: 服务器内部错误, 请查看日志")


@router.get("/artist/{source}/{artist_id}/songs", response_model=ArtistOnlineSongsResponse, dependencies=[Depends(require_auth)])
async def get_artist_online_songs(
    source: str,
    artist_id: str,
    offset: int = 0,
    limit: int = 50
):
    """
    获取歌手的在线歌曲列表
    """
    try:
        aggregator = get_aggregator()

        # 获取指定源的 provider
        provider = aggregator.get_provider(source)
        if not provider:
            raise HTTPException(status_code=404, detail=f"不支持的音乐源: {source}")

        songs = await provider.get_artist_songs(artist_id, offset, limit)

        return {
            "source": source,
            "artist_id": artist_id,
            "offset": offset,
            "limit": limit,
            "items": [song.to_dict() for song in songs],
            "total": len(songs)
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="获取歌曲列表失败: 服务器内部错误, 请查看日志")

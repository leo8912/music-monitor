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
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.services.download_service import DownloadService
from app.services.music_providers import MusicAggregator

router = APIRouter(prefix="/api/discovery", tags=["discovery"])
logger = logging.getLogger(__name__)


@router.get("/search")
@router.get("/search")
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
        from app.services.music_providers import MusicAggregator
        
        if not keyword:
            if title and artist:
                keyword = f"{title} {artist}"
            elif title:
                keyword = title
            elif artist:
                keyword = artist
            else:
                raise HTTPException(status_code=400, detail="Missing parameter: keyword or (title, artist)")

        aggregator = MusicAggregator()
        results = await aggregator.search_song(keyword, limit=limit)
        
        # 转换为字典格式
        return [song.to_dict() for song in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/search_download")
async def search_download(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=100)
):
    """
    搜索可供下载的音源 (GDStudio API)
    
    专门用于"重新下载"功能，确保搜索结果 ID 与下载接口兼容。
    """
    try:
        service = DownloadService()
        
        # 为了提高效率，我们并行搜索几个主要源 (已剔除目前返回 400 的 tencent, kugou)
        sources = ["kuwo", "netease", "migu", "joox"]
        
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/probe_qualities")
async def probe_qualities_endpoint(
    source: str,
    id: str
):
    """
    实时探测该歌曲在不同音质下的可用性
    """
    try:
        service = DownloadService()
        results = await service.probe_available_qualities(source, id)
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search_artists")
async def search_artists(keyword: str):
    """
    搜索歌手
    
    在多个平台搜索歌手,返回包含头像、平台等信息的结果列表。
    """
    try:
        aggregator = MusicAggregator()
        results = await aggregator.search_artist(keyword, limit=10)
        
        return [artist.to_dict() for artist in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索歌手失败: {str(e)}")


@router.get("/artist/{source}/{artist_id}/songs")
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
        aggregator = MusicAggregator()
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取歌曲列表失败: {str(e)}")

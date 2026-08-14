# -*- coding: utf-8 -*-
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_async_session
from app.services.subscription import SubscriptionService
from app.schemas import ArtistConfig, SubscriptionResponse, ArtistListItem, ArtistDetailResponse
from app.dependencies import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["subscription"], dependencies=[Depends(require_auth)])

async def run_refresh_task(artist_name: str, source: str = None, artist_id: str = None):
    """
    后台任务入口 (兼容 FastAPI BackgroundTasks):
    投递到任务队列 (arq 模式由 worker 消费; inline 模式进程内后台执行)。
    实际逻辑见 app/workers/tasks.py::refresh_artist
    """
    from core.queue import enqueue
    await enqueue("refresh_artist", artist_name=artist_name, source=source, artist_id=artist_id)

@router.get("/api/subscription/artists", response_model=list[ArtistListItem])
async def get_monitored_artists(db: AsyncSession = Depends(get_async_session)):
    """获取所有关注的歌手"""
    try:
        return await SubscriptionService.get_monitored_artists(db)
    except Exception as e:
        logger.error(f"Get artists error: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")

@router.get("/api/subscription/artists/{artist_id}", response_model=ArtistDetailResponse)
async def get_artist_detail(
    artist_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """获取艺人详情（歌曲列表 + 专辑分组）"""
    try:
        detail = await SubscriptionService.get_artist_detail(db, artist_id)
        if not detail:
            raise HTTPException(status_code=404, detail="未找到该艺人")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get artist detail error: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")

@router.post("/api/subscription/artists", response_model=SubscriptionResponse)
async def add_artist(
    req: ArtistConfig,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    """
    添加关注歌手
    支持自动搜索模式和直接指定模式
    """
    try:
        if not req.id or not req.source:
            # 自动搜索模式 (兼容老版本 media.py 逻辑)
            from app.services.media_service import find_artist_ids
            logger.info(f"Auto-searching for artist IDs: {req.name}")
            found = await find_artist_ids(req.name)

            if not found:
                # 如果没找到，至少先建个逻辑节点，后台慢慢搜
                success = await SubscriptionService.add_artist(db, req.name, "", "")
                if success:
                    background_tasks.add_task(run_refresh_task, req.name.strip())
                    return {"success": True, "message": f"已创建 {req.name}，正在尝试后台关联..."}
                raise HTTPException(status_code=404, detail="未找到歌手且无法创建")

            added_names = []
            notified_artist_ids = set()

            for item in found:
                await SubscriptionService.add_artist(
                    db, item['name'], item['source'],
                    item['id'], item.get('avatar')
                )
                added_names.append(item['name'])
                # 为每个找到的实例触发后台拉取
                background_tasks.add_task(run_refresh_task, item['name'], item['source'], item['id'])

                # 尝试通知 (去重)
                from app.models.artist import Artist
                from app.services.notification import NotificationService
                stmt = select(Artist).where(Artist.name == item['name'])
                art = (await db.execute(stmt)).scalars().first()
                if art and art.id not in notified_artist_ids:
                    await NotificationService.send_artist_card(art.name, str(art.id), art.avatar)
                    notified_artist_ids.add(art.id)

            return {"success": True, "message": f"已添加 {', '.join(added_names)}"}
        else:
            # 直接指定模式
            logger.info(f"Directly adding artist: {req.name} ({req.source}:{req.id})")
            success = await SubscriptionService.add_artist(
                db, req.name, req.source, req.id, req.avatar
            )

            if success:
                # 触发后台关联与刷新任务
                background_tasks.add_task(run_refresh_task, req.name.strip(), req.source, req.id)

                # 发送通知
                from app.models.artist import Artist
                from app.services.notification import NotificationService
                stmt = select(Artist).where(Artist.name == req.name)
                art = (await db.execute(stmt)).scalars().first()
                if art:
                    # 使用 background_task 发送? 不，await 即可
                    await NotificationService.send_artist_card(art.name, str(art.id), art.avatar or req.avatar)

                return {"success": True, "message": f"已成功关注 {req.name}"}
            else:
                return {"success": False, "message": "添加歌手失败"}

    except Exception as e:
        logger.error(f"Add artist error: {e}")
        raise HTTPException(status_code=500, detail="添加失败: 服务器内部错误, 请查看日志")

@router.delete("/api/subscription/artists/{artist_id}", response_model=SubscriptionResponse)
async def delete_artist(
    db: AsyncSession = Depends(get_async_session),
    artist_id: Optional[int] = None,
    source: Optional[str] = None,
    id: Optional[str] = None
):
    """
    删除歌手
    同时支持按 artist_id 或按 source/id 删除
    """
    try:
        if artist_id:
            success_count = await SubscriptionService.delete_artist(db, artist_id)
        elif source and id:
            # 找到对应的逻辑艺人 ID
            from app.models.artist import ArtistSource
            stmt = select(ArtistSource).where(ArtistSource.source == source, ArtistSource.source_id == id)
            src = (await db.execute(stmt)).scalar_one_or_none()
            if src:
                success_count = await SubscriptionService.delete_artist(db, src.artist_id)
            else:
                success_count = 0
        else:
            raise HTTPException(status_code=400, detail="Missing deletion parameters")

        if success_count > 0:
            return {"success": True, "message": "已成功删除艺人及其所有数据"}
        else:
            raise HTTPException(status_code=404, detail="未找到该艺人")

    except Exception as e:
        logger.error(f"Delete artist error: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")

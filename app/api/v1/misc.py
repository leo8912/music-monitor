# -*- coding: utf-8 -*-
"""
系统杂项路由 - WebSocket 广播测试与数据库重置

从 system.py 拆出（阶段 4.6）：杂项域。
test_ws 为匿名端点（鉴权白名单），reset_database 需鉴权且为危险操作。

Author: google
Updated: 2026-08-13
"""
import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import GenericActionResponse
from app.services.library import LibraryService
from core.websocket import manager
from core.database import get_async_session
from app.dependencies import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/test_ws", response_model=GenericActionResponse)
async def test_ws_broadcast(msg: str = "Test Message"):
    """Test broadcasting to all connected clients"""
    await manager.broadcast({
        "type": "notification",
        "level": "success",
        "message": f"🔔 WebSocket Test: {msg}"
    })
    return {"count": len(manager.active_connections), "message": "Broadcast sent"}


@router.post("/api/system/reset_database", response_model=GenericActionResponse, dependencies=[Depends(require_auth)])
async def reset_database(db: AsyncSession = Depends(get_async_session)):
    """
    重置数据库：清除所有歌曲和歌手数据
    (不删除本地文件)
    """
    try:
        service = LibraryService()
        success = await service.reset_database(db)
        if success:
            return {"status": "success", "message": "Database reset successfully"}
        else:
            raise HTTPException(status_code=500, detail="Database reset failed")
    except Exception as e:
        logger.error(f"Reset DB endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")

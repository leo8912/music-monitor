# -*- coding: utf-8 -*-
"""
系统管理路由器 - 提供系统级API接口

此模块负责提供系统级的API接口，包括：
- 配置管理
- 日志查看
- 任务调度
- 通知测试
- WebSocket连接管理

更新日志:
- 2026-01-22: 添加了EventType.NEW_CONTENT支持通知功能
- 2026-01-22: 修复了事件发布中的类型错误
"""

import logging
import yaml
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Core Imports
from core.config import config
from core.scheduler import scheduler
from core.logger import api_log_handler
from core.database import get_async_session, get_db, AsyncSessionLocal
from core.event_bus import get_event_bus, EventType

event_bus = get_event_bus()
from core.websocket import manager
from notifiers.wecom import WeComNotifier

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for client 'ping' or just block
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            manager.disconnect(websocket)
        except: pass

@router.get("/api/test_ws")
async def test_ws_broadcast(msg: str = "Test Message"):
    """Test broadcasting to all connected clients"""
    await manager.broadcast({
        "type": "notification", 
        "level": "success", 
        "message": f"🔔 WebSocket Test: {msg}"
    })
    return {"count": len(manager.active_connections), "message": "Broadcast sent"}


@router.get("/api/settings")
async def get_settings():
    """Get global configuration."""
    from core.config_manager import get_config_manager
    return get_config_manager()._config

@router.post("/api/settings")
def update_settings(new_config: dict):
    """Update global configuration."""
    try:
        from core.config_manager import get_config_manager
        config_instance = get_config_manager()
        
        # Validate structure roughly
        if 'global' not in new_config or 'monitor' not in new_config:
            # We allow partial updates if we use deep_merge, but the frontend usually sends full object
            pass
            
        # Update memory and save
        config_instance.update(new_config)
        config_instance.save_config()
        
        logger.info("Configuration updated via API (ConfigManager)")
        return {"status": "success", "message": "Settings saved"}
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/logs")
async def get_logs():
    """Get recent logs."""
    return api_log_handler.get_recent_logs()

@router.post("/api/system/scan")
async def trigger_library_scan(db: AsyncSession = Depends(get_async_session)):
    """
    手动触发本地资料库扫描与补全 (Phase 9)
    """
    from app.services.library import LibraryService
    
    try:
        service = LibraryService()
        
        # 1. 扫描文件
        new_count = await service.scan_local_files(db)
        
        # 2. 补全元数据 (可以异步执行，或者这里只触发少量)
        # 为即时反馈，这里同步执行一次小批量补全
        enrich_count = await service.enrich_metadata(db, limit=5)
        
        # 3. 如果还有更多，可以后台执行 (TODO: 集成到 Scheduler)
        
        return {
            "status": "success", 
            "new_files_found": new_count,
            "metadata_enriched": enrich_count,
            "message": f"Scanned {new_count} new files, enriched {enrich_count}."
        }
    except Exception as e:
        logger.error(f"Library scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/check/{source}")
@router.post("/api/run_check/{source}")
async def trigger_check(source: str):
    """手动触发指定平台的同步检查"""
    if source not in ['netease', 'qqmusic']:
        raise HTTPException(status_code=400, detail="Invalid source")
    
    # 触发对应平台的立即检查
    # Correct ID from main.py is "job_{source}"
    job_id = f"job_{source}"
    job = scheduler.get_job(job_id)
    
    if not job:
        logger.warning(f"Job {job_id} not found in scheduler, available: {[j.id for j in scheduler.get_jobs()]}")
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    try:
        # 立即执行任务
        job.modify(next_run_time=datetime.now()) # Use datetime.now() for immediate run in some APScheduler versions or modify next_run_time
        # In APScheduler, next_run_time=None usually means paused. 
        # To trigger now, we can use scheduler.trigger_job(job_id) if it exists or just modify to now.
        # scheduler.add_job(..., next_run_time=datetime.now())
        # Let's use the most reliable way for APScheduler
        try:
            scheduler.modify_job(job_id, next_run_time=datetime.now())
        except:
             job.modify(next_run_time=datetime.now())
             
        logger.info(f"手动触发 {source} 同步检查")
        return {"status": "success", "message": f"{source} 同步已触发"}
    except Exception as e:
        logger.error(f"触发 {source} 检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/status")
async def get_status():
    jobs = scheduler.get_jobs()
    job_info = [{"id": j.id, "next_run": j.next_run_time} for j in jobs]
    return {"status": "running", "jobs": job_info}

@router.post("/api/test_notify/{channel}")
async def test_notify(channel: str):
    """Send a test notification to the specified channel."""
    try:
        # Load fresh config logic
        notify_cfg = config.get('notify', {})
        
        if channel == 'wecom':
            cfg = notify_cfg.get('wecom', {})
            # Try to get short names first (frontend standard), fall back to long names locally if needed for migration
            # But we want to enforce short names 'corpid', 'agentid', 'corpsecret'
            notifier = WeComNotifier(
                corp_id=cfg.get('corpid') or cfg.get('corp_id'),
                secret=cfg.get('corpsecret') or cfg.get('secret'),
                agent_id=cfg.get('agentid') or cfg.get('agent_id')
            )
            await notifier.send_test_message()
            return {"status": "success", "message": "WeCom test message sent"}
            
        elif channel == 'telegram':
            from notifiers.telegram import TelegramNotifier
            cfg = notify_cfg.get('telegram', {})
            notifier = TelegramNotifier(
                bot_token=cfg.get('bot_token'),
                chat_id=cfg.get('chat_id')
            )
            await notifier.send_test_message()
            return {"status": "success", "message": "Telegram test message sent"}
            
        else:
            raise HTTPException(status_code=400, detail="Unknown channel")
            
    except Exception as e:
        logger.error(f"Test notify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/test_notify_card/{channel}")
async def test_notify_card(channel: str):
    """Send a test CARD notification with Deep Link to verify remote playback."""
    try:
        from core.database import MediaRecord
        from datetime import datetime
        
        # Mock MediaRecord
        mock_media = MediaRecord(
             title="Testing Remote Playback Test Song",
             author="Test Artist",
             album="Test Album",
             url="https://music.163.com/#/song?id=123456",
             publish_time=datetime.now(),
             source="netease",
             media_id="123456",
             cover="https://p2.music.126.net/tGHU62DTszbTsM7vzNgHjw==/109951165631226326.jpg" 
             # If I want it to play, I should probably use a real ID that exists in history or I can add to.
             # "123456" might not exist in history, so frontend will just warn.
             # But the link is what matters.
        )
        # We simulate the event
        # Note: main.py subscribes to "new_content"
        await event_bus.publish(EventType.NEW_CONTENT, mock_media)
        
        return {"status": "success", "message": "Test card event published"}
    except Exception as e:
        logger.error(f"Test card notify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/check_notify_status/{channel}")
async def check_notify_status(channel: str):
    """Check connectivity status for notification channel."""
    try:
        notify_cfg = config.get('notify', {})
        if channel == 'wecom':
            cfg = notify_cfg.get('wecom', {})
            notifier = WeComNotifier(
                corp_id=cfg.get('corpid') or cfg.get('corp_id'),
                secret=cfg.get('corpsecret') or cfg.get('secret'),
                agent_id=cfg.get('agentid') or cfg.get('agent_id')
            )
            ok = await notifier.check_connectivity()
            return {"status": "ok" if ok else "error", "connected": ok}
            
        elif channel == 'telegram':
            from notifiers.telegram import TelegramNotifier
            cfg = notify_cfg.get('telegram', {})
            notifier = TelegramNotifier(
                bot_token=cfg.get('bot_token'),
                chat_id=cfg.get('chat_id')
            )
            ok = await notifier.check_connectivity()
            return {"status": "ok" if ok else "error", "connected": ok}
            
        return {"status": "error", "connected": False}
    except Exception as e:
         return {"status": "error", "connected": False, "detail": str(e)}

@router.post("/api/system/reset_database")
async def reset_database(db: AsyncSession = Depends(get_async_session)):
    """
    重置数据库：清除所有歌曲和歌手数据
    (不删除本地文件)
    """
    from app.services.library import LibraryService
    try:
        service = LibraryService()
        success = await service.reset_database(db)
        if success:
            return {"status": "success", "message": "Database reset successfully"}
        else:
            raise HTTPException(status_code=500, detail="Database reset failed")
    except Exception as e:
        logger.error(f"Reset DB endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

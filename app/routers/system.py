import logging
import yaml
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

# Core Imports
from core.config import config
from core.scheduler import scheduler
from core.logger import api_log_handler
from core.event_bus import event_bus
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


@router.get("/api/settings")
async def get_settings():
    """Get global configuration."""
    return config

@router.post("/api/settings")
def update_settings(new_config: dict):
    """Update global configuration."""
    # Note: modifying the mutable config dict updates it globally for other modules
    try:
        # Validate structure roughly
        if 'global' not in new_config or 'monitor' not in new_config or 'notify' not in new_config:
            raise HTTPException(status_code=400, detail="Invalid config structure")
            
        # Update memory
        config.update(new_config)
        
            # Cleanup legacy keys for WeCom if present
        if 'notify' in config and 'wecom' in config['notify']:
            wecom = config['notify']['wecom']
            keys_to_remove = []
            
            # Map legacy to new if new is missing, otherwise just remove legacy
            # Legacy: corp_id, agent_id, secret
            # New: corpid, agentid, corpsecret, token, encoding_aes_key
            
            legacy_map = {
                'corp_id': 'corpid',
                'agent_id': 'agentid', 
                'secret': 'corpsecret',
                # Assuming no legacy keys for token/aes_key yet, but good to be safe if any
            }
            
            for old_k, new_k in legacy_map.items():
                if old_k in wecom:
                    # If new key is missing/empty but old exists, migrate value
                    if not wecom.get(new_k) and wecom.get(old_k):
                        wecom[new_k] = wecom[old_k]
                    # Mark old key for removal
                    keys_to_remove.append(old_k)
            
            for k in keys_to_remove:
                wecom.pop(k, None)
        
        # Save to file
        with open("config.yaml", "w", encoding='utf-8') as f:
            yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)
            
        logger.info("Configuration updated via API")
        
        return {"status": "success", "message": "Settings saved"}
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/logs")
async def get_logs():
    """Get recent logs."""
    return api_log_handler.get_recent_logs()

@router.post("/api/check/{source}")
async def trigger_check(source: str):
    """手动触发指定平台的同步检查"""
    if source not in ['netease', 'qqmusic']:
        raise HTTPException(status_code=400, detail="Invalid source")
    
    # 触发对应平台的立即检查
    job_id = f"{source}_check"
    job = scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    try:
        # 立即执行任务
        job.modify(next_run_time=None)  # 触发立即执行
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
        await event_bus.publish("new_content", mock_media)
        
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

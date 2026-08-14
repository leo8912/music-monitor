# -*- coding: utf-8 -*-
"""
系统通知路由 - 通知渠道测试与连接状态检查

从 system.py 拆出（阶段 4.6）：通知域单一职责。
connected 字段由前端依赖（NotifySettings.vue / SettingsModal.vue），
已并入 GenericActionResponse 保持兼容。

Author: google
Updated: 2026-08-13
"""
import logging

from fastapi import APIRouter, HTTPException, Depends

from app.schemas import GenericActionResponse
from core.config import config
from app.notifiers.wecom import WeComNotifier
from app.notifiers.telegram import TelegramNotifier
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.post("/api/test_notify/{channel}", response_model=GenericActionResponse)
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
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")


@router.get("/api/check_notify_status/{channel}", response_model=GenericActionResponse)
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
            cfg = notify_cfg.get('telegram', {})
            notifier = TelegramNotifier(
                bot_token=cfg.get('bot_token'),
                chat_id=cfg.get('chat_id')
            )
            ok = await notifier.check_connectivity()
            return {"status": "ok" if ok else "error", "connected": ok}

        return {"status": "error", "connected": False}
    except Exception:
        return {"status": "error", "connected": False, "detail": "服务器内部错误, 请查看日志"}

# -*- coding: utf-8 -*-
"""
Notification Service

Handles media content notification dispatch to different channels (WeCom, etc.).

Author: GOOGLE music-monitor development team
"""
import logging
from urllib.parse import quote
from typing import Optional, Any
from starlette.concurrency import run_in_threadpool

from core.config import config
from notifiers.wecom import WeComNotifier
from notifiers.telegram import TelegramNotifier
from core.security import generate_signed_url_params

logger = logging.getLogger(__name__)

class NotificationService:
    _wecom: Optional[WeComNotifier] = None
    _telegram: Optional[TelegramNotifier] = None
    
    @classmethod
    def initialize(cls):
        """Initialize notifiers from global config."""
        notify_cfg = config.get('notify', {})
        
        # WeCom
        wecom_cfg = notify_cfg.get('wecom', {})
        if not wecom_cfg:
            return

        if wecom_cfg.get('enabled') and (wecom_cfg.get('corpid') or wecom_cfg.get('corp_id')):
            try:
                cls._wecom = WeComNotifier(
                    corp_id=wecom_cfg.get('corpid') or wecom_cfg.get('corp_id'),
                    secret=wecom_cfg.get('corpsecret') or wecom_cfg.get('secret'),
                    agent_id=wecom_cfg.get('agentid') or wecom_cfg.get('agent_id')
                )
                logger.info("NotificationService: WeCom initialized")
            except Exception as e:
                logger.error(f"NotificationService: WeCom init failed: {e}")
        else:
            cls._wecom = None

        # Telegram
        tg_cfg = notify_cfg.get('telegram', {})
        if tg_cfg.get('enabled') and tg_cfg.get('bot_token'):
            try:
                cls._telegram = TelegramNotifier(
                    token=tg_cfg.get('bot_token'),
                    chat_id=tg_cfg.get('chat_id')
                )
                logger.info("NotificationService: Telegram initialized")
            except Exception as e:
                logger.error(f"NotificationService: Telegram init failed: {e}")
        else:
            cls._telegram = None

    @classmethod
    async def handle_new_content(cls, media: Any):
        """
        Event handler for 'new_content'.
        media: MediaInfo or Song object (duck typing usually)
        """
        # 1. Format Message
        message_text = (
            f"🎵 新歌发布: {media.title}\n"
            f"👤 歌手: {media.author}\n"
            f"💿 专辑: {media.album or '单曲'}\n"
            f"🔗 链接: {media.url}\n"
            f"📅 时间: {media.publish_time}"
        )
        
        # Custom description support (for batch summaries)
        if hasattr(media, 'custom_description') and media.custom_description:
            message_text = media.custom_description
            
        # 2. Determine Target URL
        target_url = media.url
        external_url = config.get('global', {}).get('external_url')
        
        if external_url and external_url.startswith('http'):
            external_url = external_url.rstrip('/')
            try:
                # Try generating mobile play link
                # Media object might be MediaInfo or Song. 
                # MediaInfo has unique_key(). Song has unique_key attribute.
                u_key = getattr(media, 'unique_key', None)
                if callable(u_key): u_key = u_key() # Handle method
                if not u_key: u_key = f"{media.source}:{media.id}" # Fallback
                
                sign_params = generate_signed_url_params(u_key)
                target_url = f"{external_url}/#/mobile/play?id={quote(sign_params['id'])}&sign={sign_params['sign']}&expires={sign_params['expires']}"
            except Exception as e:
                logger.warning(f"Failed to generate mobile link: {e}")
                # Fallback
                target_url = f"{external_url}?source={media.source}&songId={media.media_id if hasattr(media, 'media_id') else media.id}"

        pic_url = getattr(media, 'cover', None) or getattr(media, 'cover_url', '')

        # 3. Send WeCom
        if cls._wecom:
            try:
                # 增强消息描述，说明交互指令
                enhanced_description = message_text
                if not (hasattr(media, 'custom_description') and media.custom_description):
                    enhanced_description += f"\n\n💡 想要离线听？发送“下载 {media.title}”即可开始下载。"
                
                # Use News Message for rich display
                await cls._wecom.send_news_message(
                    title=f"🎵 新歌发布: {media.title}",
                    description=enhanced_description,
                    url=target_url,
                    pic_url=pic_url
                )
            except Exception as e:
                logger.error(f"WeCom send failed: {e}")

        # 4. Send Telegram
        if cls._telegram:
            try:
                await run_in_threadpool(
                    cls._telegram.send_message,
                    message_text,
                    image_url=pic_url
                )
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")

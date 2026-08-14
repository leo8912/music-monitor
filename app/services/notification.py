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

from core.config_manager import get_config_manager
from app.notifiers.wecom import WeComNotifier
from app.notifiers.telegram import TelegramNotifier
from core.security import generate_signed_url_params

logger = logging.getLogger(__name__)

class NotificationService:
    _wecom: Optional[WeComNotifier] = None
    _telegram: Optional[TelegramNotifier] = None

    @classmethod
    def _read_config(cls):
        """从 ConfigManager 读取最新的 notify 配置 (避免 stale 全局引用)。"""
        return get_config_manager().get('notify', {}) or {}

    @classmethod
    def reload(cls):
        """配置变更后重建 notifier，无需重启即可生效。"""
        cls.initialize()
        logger.info("NotificationService: reloaded with latest notify config")

    @classmethod
    def initialize(cls):
        """初始化 notifiers from current config."""
        notify_cfg = cls._read_config()

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
    async def notify_new_song(cls, snapshot: dict):
        """
        新歌发布通知 (发现即推，独立于下载)。

        snapshot 结构: {title, artist, album, cover_url, publish_time, source, source_id}
        """
        title = snapshot.get('title') or ''
        artist = snapshot.get('artist') or ''
        album = snapshot.get('album') or '单曲'
        cover = snapshot.get('cover_url') or ''
        publish_time = snapshot.get('publish_time')
        source = snapshot.get('source') or ''
        source_id = str(snapshot.get('source_id') or '')

        date_str = ""
        if publish_time:
            try:
                date_str = publish_time.strftime("%Y-%m-%d")
            except Exception:
                date_str = str(publish_time)

        description = (
            f"👤 歌手: {artist}\n"
            f"💿 专辑: {album}\n"
            f"📅 发布时间: {date_str or '未知'}\n\n"
            "🔽 正在自动下载高清音质，完成后将推送试听卡片。"
        )

        target_url = cls._build_play_url(source, source_id)

        if cls._wecom:
            try:
                await cls._wecom.send_news_message(
                    title=f"🎵 新歌发布: {title}",
                    description=description,
                    url=target_url or "",
                    pic_url=cover
                )
            except Exception as e:
                logger.error(f"WeCom new-song send failed: {e}")

        if cls._telegram:
            try:
                text = (
                    f"🎵 新歌发布: {title}\n"
                    f"👤 歌手: {artist}\n"
                    f"💿 专辑: {album}\n"
                    f"📅 时间: {date_str or '未知'}"
                )
                await run_in_threadpool(
                    cls._telegram.send_message,
                    text,
                    image_url=cover
                )
            except Exception as e:
                logger.error(f"Telegram new-song send failed: {e}")

    @classmethod
    def _build_play_url(cls, source: str, source_id: str) -> Optional[str]:
        """构造带签名的点开即播链接 (仅当 external_url 配置且 source 完整时)。"""
        if not source or not source_id:
            return None
        external_url = get_config_manager().get('system', {}).get('external_url', '')
        if not external_url or not external_url.startswith('http'):
            return None
        external_url = external_url.rstrip('/')
        try:
            u_key = f"{source}_{source_id}"
            sign_params = generate_signed_url_params(u_key)
            return f"{external_url}/#/mobile/play?id={quote(sign_params['id'])}&sign={sign_params['sign']}&expires={sign_params['expires']}"
        except Exception as e:
            logger.warning(f"Failed to build play url: {e}")
            return None

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
        external_url = get_config_manager().get('system', {}).get('external_url', '')

        if external_url and external_url.startswith('http'):
            external_url = external_url.rstrip('/')
            try:
                # Try generating mobile play link
                # Media object might be MediaInfo or Song.
                # MediaInfo has unique_key(). Song has unique_key attribute.
                u_key = getattr(media, 'unique_key', None)
                if callable(u_key):
                    u_key = u_key()  # Handle method
                if not u_key:
                    u_key = f"{media.source}:{media.id}"  # Fallback

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

    @classmethod
    async def send_artist_card(cls, artist_name: str, artist_id: str, avatar: str = ""):
        """发送歌手关注成功卡片"""
        # 如果未配置企业微信，直接返回
        if not cls._wecom:
            return

        try:
            # 构造链接
            external_url = get_config_manager().get('system', {}).get('external_url', '')
            if external_url and external_url.startswith('http'):
                external_url = external_url.rstrip('/')
                target_url = f"{external_url}/#/artist/{artist_id}"
            else:
                target_url = ""

            # 构造描述
            description = (
                "✅ 已添加至音乐库\n"
                "🔄 正在后台同步历史专辑与热门歌曲...\n\n"
                "💡 提示：点击卡片查看歌手详情"
            )

            await cls._wecom.send_news_message(
                title=f"关注成功：{artist_name}",
                description=description,
                url=target_url,
                pic_url=avatar or "/static/default_artist.png"
            )
            logger.info(f"Notification: Sent artist card for {artist_name}")
        except Exception as e:
            logger.error(f"Failed to send artist card: {e}")

    @classmethod
    async def send_download_card(cls, title: str, artist: str, album: str, cover: str, magic_link: str, quality: str = "Standard"):
        """发送下载完成卡片"""
        if not cls._wecom:
            return

        try:
            description = (
                f"👤 歌手: {artist}\n"
                f"💿 专辑: {album or '未知'}\n"
                f"💎 音质: {quality}\n\n"
                "✨ 点击卡片立即播放 (无需登录)"
            )

            await cls._wecom.send_news_message(
                title=f"下载完成：{title}",
                description=description,
                url=magic_link,
                pic_url=cover
            )
            logger.info(f"Notification: Sent download card for {title}")
        except Exception as e:
            logger.error(f"Failed to send download card: {e}")


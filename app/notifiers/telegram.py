import logging
import aiohttp
from app.domain.models import MediaInfo
from app.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Initialize proxy to None by default, as it's used in check_connectivity
        # but not provided in the __init__ signature in the original code.
        # This ensures the code is syntactically correct and avoids AttributeError.
        self.proxy = None

    async def send(self, media: MediaInfo):
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram config missing, skipping.")
            return

        # Prepare message
        # Use MarkdownV2 or HTML. Let's use HTML for easier link handling.

        # Helper to get source name
        source_map = {'netease': '网易云音乐', 'qqmusic': 'QQ音乐'}
        source_name = source_map.get(media.source, media.source)

        links_part = ""

        # Standard Link
        links_part += f"\n🔗 <a href='{media.url}'>前往 {source_name} 收听</a>"

        # Format:
        # 🎵 <b>Song Title</b>
        # 👤 Artist
        # 💿 Album
        # ...

        date_str = media.publish_time
        if hasattr(media.publish_time, 'strftime'):
            date_str = media.publish_time.strftime('%Y-%m-%d')

        text = (
            f"🎵 <b>{media.title}</b>\n"
            f"👤 {media.author}\n"
            f"💿 {media.album or '单曲'}\n"
            f"📅 {date_str}\n"
            f"{links_part}"
        )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    res = await resp.json()
                    if not res.get('ok'):
                        logger.error(f"Telegram 发送失败: {res}")
                    else:
                        logger.info(f"Telegram 推送成功: {media.title}")
        except Exception as e:
             logger.error(f"Telegram 网络错误: {e}")

    async def send_test_message(self):
        """Send a test message to verify config."""
        if not self.bot_token or not self.chat_id:
             raise ValueError("Missing Token or Chat ID")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": "<b>Music Monitor Configuration Test</b>\nIf you see this, Telegram notification is working!",
            "parse_mode": "HTML"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res = await resp.json()
                if not res.get('ok'):
                    raise Exception(f"Telegram API Error: {res.get('description')}")
                return True

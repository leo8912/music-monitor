import logging
import aiohttp
from typing import Optional
from domain.models import MediaInfo
from notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)

class WeComNotifier(BaseNotifier):
    def __init__(self, corp_id: str, secret: str, agent_id: str):
        self.corp_id = corp_id
        self.secret = secret
        self.agent_id = agent_id
        self._token: Optional[str] = None
        self._token_expires_at = 0

    async def _get_token(self):
        # TODO: Implement token caching logic
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get('errcode') == 0:
                    return data.get('access_token')
                logger.error(f"WeCom token error: {data}")
                return None

    async def check_connectivity(self) -> bool:
        """Check if WeCom API is reachable and config is valid."""
        if not self.corp_id or not self.secret:
            logger.warning("WeCom config missing.")
            return False
        token = await self._get_token()
        return token is not None

    async def send(self, media: MediaInfo):
        if not self.corp_id or not self.secret:
            logger.warning("WeCom config missing, skipping.")
            return

        token = await self._get_token()
        if not token:
            logger.error("无法获取企业微信 Token")
            return

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        
        # Helper to get source name
        source_map = {'netease': '网易云音乐', 'qqmusic': 'QQ音乐', 'bilibili': 'Bilibili'}
        source_name = source_map.get(media.source, media.source)
        
        # New "Card + Emoji" Style
        # Title: 🎵 Song Name
        card_title = f"🎵 {media.title}"
        
        # Description:
        # 👤 Artist
        # 💿 Album
        # 📅 Time | 🔗 Source
        
        desc_lines = [
            f"👤 <div class=\"highlight\">{media.author}</div>",
            f"💿 {media.album or '单曲'}",
            f"📅 {media.publish_time.strftime('%Y-%m-%d') if hasattr(media.publish_time, 'strftime') else media.publish_time}",
            f"🔗 {source_name}"
        ]
        
        if media.trial_url:
             desc_lines.append(f"\n📺 <b>已包含 B站试听链接</b>")
        
        description = "\n".join(desc_lines)
        
        if media.trial_url:
            main_url = media.trial_url
            btn_txt = "立即试听 (Bilibili)"
        else:
            main_url = media.url
            btn_txt = "前往收听"
        
        payload = {
            "touser": "@all",
            "msgtype": "textcard",
            "agentid": self.agent_id,
            "textcard": {
                "title": card_title,
                "description": description,
                "url": main_url, 
                "btntxt": btn_txt
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res = await resp.json()
                if res.get('errcode') != 0:
                    logger.error(f"企业微信发送失败: {res}")
                else:
                    logger.info(f"企业微信推送成功: {media.title}")

    async def send_test_message(self):
        """Send a test message to verify config."""
        if not self.corp_id or not self.secret:
             raise ValueError("WeCom config missing")
        
        token = await self._get_token()
        if not token:
             raise ValueError("Failed to get Access Token")
             
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        payload = {
            "touser": "@all",
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": "🎉 音乐监控系统: 这是一条测试消息。\nMusic Monitor: This is a test message."
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res = await resp.json()
                if res.get('errcode') != 0:
                    raise Exception(f"WeCom API Error: {res}")
                return True

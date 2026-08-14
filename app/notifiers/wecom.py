import logging
import aiohttp
import time
"""
WeCom Notifier

Handles WeChat Work message sending (Text, TextCard, News) and token management.

Author: GOOGLE music-monitor development team
"""
from typing import Optional
from app.domain.models import MediaInfo
from app.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)

class WeComNotifier(BaseNotifier):
    def __init__(self, corp_id: str = None, secret: str = None, agent_id: str = None):
        if not corp_id or not secret or not agent_id:
            from core.config import config
            wc = config.get('notify', {}).get('wecom', {})
            corp_id = corp_id or wc.get('corpid') or wc.get('corp_id')
            secret = secret or wc.get('corpsecret') or wc.get('secret')
            agent_id = agent_id or wc.get('agentid') or wc.get('agent_id')

        self.corp_id = corp_id
        self.secret = secret
        self.agent_id = agent_id
        self._token: Optional[str] = None
        self._token_expires_at = 0

    async def send_text(self, content: str, user_ids: list[str] = None):
        """Send a simple text message."""
        if not self.corp_id or not self.secret:
             raise ValueError("WeCom config (corp_id or secret) is missing")

        token = await self._get_token()
        if not token:
             raise ValueError("Failed to obtain WeCom access token")

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        touser = "|".join(user_ids) if user_ids else "@all"

        payload = {
            "touser": touser,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res = await resp.json()
                if res.get('errcode') != 0:
                    logger.error(f"WeCom text error: {res}")
                    raise Exception(f"WeCom API Error: {res.get('errmsg')} (code: {res.get('errcode')})")

    async def _get_token(self):
        # 检查缓存是否有效 (Check cache)
        if self._token and time.time() < self._token_expires_at:
            return self._token

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get('errcode') == 0:
                    self._token = data.get('access_token')
                    # 有效期内提前 5 分钟 (300秒) 刷新
                    self._token_expires_at = time.time() + data.get('expires_in', 7200) - 300
                    return self._token
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
        source_map = {'netease': '网易云音乐', 'qqmusic': 'QQ音乐'}
        source_name = source_map.get(media.source, media.source)

        # New "Card + Emoji" Style
        # Title: 🎉 新歌发布 | Song Name
        card_title = f"🎉 新歌发布 | {media.title}"

        # Description:
        # 🎙️ 歌手: Artist
        # 💿 专辑: Album
        # 🗓️ 时间: Date
        # 📺 来源: Source

        desc_lines = [
            f"🎙️ 歌手: <div class=\"highlight\">{media.author}</div>",
            f"💿 专辑: {media.album or '单曲'}",
            f"🗓️ 时间: {media.publish_time.strftime('%Y-%m-%d') if hasattr(media.publish_time, 'strftime') else media.publish_time}",
            f"📺 来源: {source_name}"
        ]

        if media.trial_url:
             desc_lines.append("\n✨ <b>已匹配试听，点击直达</b>")

        description = "\n".join(desc_lines)

        if media.trial_url:
            main_url = media.trial_url
        else:
            main_url = media.url

        btn_txt = "▶️ 立即播放"

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
                "content": "👋 嗨！Music Monitor 通知服务连接正常 🚀\nMusic Monitor: Notification service connected."
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res = await resp.json()
                if res.get('errcode') != 0:
                    raise Exception(f"WeCom API Error: {res}")
                return True

    async def send_text_card(self, title: str, description: str, url: str, btntxt: str = "详情"):
        """Send a versatile text card."""
        if not self.corp_id or not self.secret:
             logger.warning("WeCom config missing, skipping.")
             return

        token = await self._get_token()
        if not token:
            logger.error("无法获取企业微信 Token")
            return

        api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        payload = {
            "touser": "@all",
            "msgtype": "textcard",
            "agentid": self.agent_id,
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": btntxt
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as resp:
                res = await resp.json()
                if res.get('errcode') != 0:
                    logger.error(f"企业微信发送失败: {res}")
                else:
                    logger.info(f"企业微信推送成功: {title}")

    async def send_news_message(self, title: str, description: str, url: str, pic_url: str, user_ids: list[str] = None):
        """Send a News (Article) message with a large header image."""
        if not self.corp_id or not self.secret:
             logger.warning("WeCom config missing, skipping.")
             return

        token = await self._get_token()
        if not token:
            logger.error("无法获取企业微信 Token")
            return

        api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        # Fallback to default image if empty
        if not pic_url:
            pic_url = "https://p2.music.126.net/tGHU62DTszbTsM7vzNgHjw==/109951165631226326.jpg"

        # 确定发送对象
        touser = "|".join(user_ids) if user_ids else "@all"

        payload = {
            "touser": touser,
            "msgtype": "news",
            "agentid": self.agent_id,
            "news": {
                "articles": [
                    {
                       "title": title,
                       "description": description,
                       "url": url,
                       "picurl": pic_url
                    }
                ]
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as resp:
                res = await resp.json()
                if res.get('errcode') != 0:
                    logger.error(f"企业微信发送图文失败: {res}")
                else:
                    logger.info(f"企业微信图文推送成功: {title}")

# -*- coding: utf-8 -*-
"""
微信企业号路由 - 处理微信回调

此模块处理企业微信的消息回调：
- 验证签名
- 解密消息
- 歌曲/歌手搜索
- 后台下载收藏

Author: google
Updated: 2026-01-26
"""
import logging
import asyncio
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Request, Response, HTTPException

try:
    from wechatpy.exceptions import InvalidSignatureException
    from wechatpy.crypto import WeChatCrypto
    from wechatpy import parse_message, create_reply
    HAS_WECHATPY = True
except ImportError:
    HAS_WECHATPY = False

from core.config import config, add_monitored_user
from core.database import AsyncSessionLocal
from app.services.wechat_download_service import WeChatDownloadService
from app.services.download_service import DownloadService
from app.services.music_providers import MusicAggregator
from notifiers.wecom import WeComNotifier

from app.models.wechat_session import WeChatSession
from datetime import timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_db_session(user_id: str) -> Optional[dict]:
    """从数据库获取搜索会话"""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(WeChatSession).where(WeChatSession.user_id == user_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session and session.expires_at > datetime.now():
            return session.session_data
        
        if session:
            await db.delete(session)
            await db.commit()
    return None

async def set_db_session(user_id: str, data: dict, expire_seconds: int = 300):
    """保存搜索会话到数据库"""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(WeChatSession).where(WeChatSession.user_id == user_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        expires_at = datetime.now() + timedelta(seconds=expire_seconds)
        
        if session:
            session.session_data = data
            session.expires_at = expires_at
        else:
            session = WeChatSession(
                user_id=user_id,
                session_data=data,
                expires_at=expires_at
            )
            db.add(session)
        await db.commit()

async def clear_db_session(user_id: str):
    """清除搜索会话"""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        stmt = delete(WeChatSession).where(WeChatSession.user_id == user_id)
        await db.execute(stmt)
        await db.commit()


def get_crypto():
    """获取微信加密器"""
    if not HAS_WECHATPY:
        return None
    
    # 获取配置，支持两种可能的路径
    wecom_cfg = config.get('notify', {}).get('wecom', {})
    if not wecom_cfg:
        wecom_cfg = config.get('notifications', {}).get('providers', {}).get('wecom', {})
        
    if not wecom_cfg:
        return None

    # 映射可能的字段名
    token = wecom_cfg.get('token')
    encoding_aes_key = wecom_cfg.get('encoding_aes_key') or wecom_cfg.get('aes_key')
    corpid = wecom_cfg.get('corpid') or wecom_cfg.get('corp_id')
    
    if not token or not encoding_aes_key or not corpid:
        logger.warning(f"WeCom回调配置不完整: token={bool(token)}, aes_key={bool(encoding_aes_key)}, corpid={bool(corpid)}")
        return None
    
    try:
        from core.wechat import FixedWeChatCrypto
        return FixedWeChatCrypto(token, encoding_aes_key, corpid)
    except Exception as e:
        logger.error(f"初始化 FixedWeChatCrypto 失败: {e}")
        return WeChatCrypto(token, encoding_aes_key, corpid)


@router.get("/api/wecom/callback")
async def wechat_verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    """微信验证接口"""
    crypto = get_crypto()
    if not crypto:
        return Response("WeCom config missing", status_code=500)
    
    try:
        decrypted_echostr = crypto.check_signature(
            msg_signature, timestamp, nonce, echostr
        )
        return Response(content=decrypted_echostr)
    except InvalidSignatureException:
        raise HTTPException(status_code=403, detail="Invalid signature")
    except Exception as e:
        logger.error(f"验证错误: {e}")
        raise HTTPException(status_code=500, detail="Verify failed")


@router.post("/api/wecom/callback")
async def wechat_callback(request: Request, msg_signature: str, timestamp: str, nonce: str):
    """微信消息回调"""
    if not HAS_WECHATPY:
        return Response("wechatpy not installed", status_code=500)
    
    logger.info(f"收到微信回调")
    
    try:
        crypto = get_crypto()
        if not crypto:
            return Response("Config missing", status_code=500)
        
        body = await request.body()
        
        try:
            decrypted_xml = crypto.decrypt_message(
                body, msg_signature, timestamp, nonce
            )
        except InvalidSignatureException:
            raise HTTPException(status_code=403, detail="Invalid signature")
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return Response("Decryption failed", status_code=500)
        
        msg = parse_message(decrypted_xml)
        
        if msg.type != 'text':
            return Response("success")
        
        content = msg.content.strip()
        user_id = msg.source
        logger.info(f"处理用户消息: {user_id} -> {content}")
        
        async def process_message(content: str, user_id: str) -> Optional[str]:
            # 1. 处理数字选择（确认下载或确认添加歌手）
            if content.isdigit():
                idx = int(content) - 1
                session = await get_db_session(user_id)
                
                if session:
                    results = session.get('results', [])
                    if 0 <= idx < len(results):
                        target = results[idx]
                        stype = session.get('type', 'song')
                        
                        if stype == 'song':
                            asyncio.create_task(background_download(target, user_id))
                            artist = format_artist(target.get('artist', ''))
                            return f"🚀 开始下载：\n{target.get('title', '未知')} - {artist}\n下载完成后将通过推送告知。"
                        elif stype == 'artist':
                            asyncio.create_task(background_add_artist(target, user_id))
                            return f"🚀 正在添加歌手监控：\n{target.get('name', '未知')}\n添加完成后将同步最新作品。"
                        
                        await clear_db_session(user_id)
                    else:
                        return f"⚠️ 请输入有效的序号 (1-{len(results)})"
                else:
                    return "⚠️ 会话已过期或不存在，请重新搜索。"
            
            # 2. 处理意图识别
            keyword = content
            intent = "artist"  # 默认搜索歌手
            
            # 定义前缀对应的搜索意图
            song_prefixes = ["下载", "喜欢", "收藏", "搜歌", "歌曲", "/song"]
            artist_prefixes = ["监控", "歌手", "添加", "/artist"]
            
            for prefix in song_prefixes:
                if content.lower().startswith(prefix):
                    intent = "song"
                    keyword = content[len(prefix):].strip()
                    break
            
            for prefix in artist_prefixes:
                if content.lower().startswith(prefix):
                    intent = "artist"
                    keyword = content[len(prefix):].strip()
                    break
            
            if not keyword:
                return "👋 你好！发送“歌曲 关键词”搜索音乐，发送“歌手 关键词”添加监控。"
            
            # 3. 执行搜索
            if intent == "song":
                return await handle_song_search(keyword, user_id)
            else:
                return await handle_artist_search(keyword, user_id)

        reply_content = await process_message(content, user_id)
        
        if not reply_content:
            return Response("success")
        
        reply = create_reply(reply_content, msg)
        xml = crypto.encrypt_message(reply.render(), nonce, timestamp)
        return Response(content=xml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"回调异常: {e}", exc_info=True)
        return Response("Error", status_code=500)


def format_artist(artist_field) -> str:
    """格式化歌手字段"""
    if isinstance(artist_field, list):
        return "/".join(str(a) for a in artist_field)
    return str(artist_field) if artist_field else ""


async def handle_song_search(keyword: str, user_id: str) -> str:
    """搜索歌曲"""
    global search_session
    
    try:
        aggregator = MusicAggregator()
        results = await asyncio.wait_for(
            aggregator.search_song(keyword, limit=8),
            timeout=5.0
        )
        
        if not results:
            return f"😔 未找到：'{keyword}'"
        
        # 缓存搜索结果
        await set_db_session(user_id, {
            "type": "song",
            "keyword": keyword,
            "results": [r.to_dict() for r in results]
        })
        
        # 构建回复
        lines = [f"🔍 找到 {len(results)} 首歌曲：\n"]
        for i, song in enumerate(results):
            artist = format_artist(song.artist)
            lines.append(f"{i+1}. {song.title} - {artist}")
        lines.append("\n回复数字下载")
        
        return "\n".join(lines)
        
    except asyncio.TimeoutError:
        return "⚠️ 搜索超时，请稍后重试"
    except Exception as e:
        logger.error(f"搜索异常: {e}")
        return "⚠️ 搜索服务暂时不可用"


async def handle_artist_search(keyword: str, user_id: str) -> str:
    """搜索歌手"""
    global search_session
    
    try:
        aggregator = MusicAggregator()
        results = await asyncio.wait_for(
            aggregator.search_artist(keyword, limit=5),
            timeout=5.0
        )
        
        if not results:
            return f"😔 未找到歌手：'{keyword}'"
        
        # 缓存结果
        await set_db_session(user_id, {
            "type": "artist",
            "keyword": keyword,
            "results": [r.to_dict() for r in results]
        })
        
        # 构建回复
        lines = [f"🎤 找到 {len(results)} 位歌手：\n"]
        for i, artist in enumerate(results):
            lines.append(f"{i+1}. {artist.name} [{artist.source}]")
        lines.append("\n回复数字添加监控")
        
        return "\n".join(lines)
        
    except asyncio.TimeoutError:
        return "⚠️ 搜索超时"
    except Exception as e:
        logger.error(f"歌手搜索异常: {e}")
        return "⚠️ 搜索服务不可用"


async def background_download(song: dict, user_id: str):
    """后台下载歌曲"""
    title = song.get('title', '')
    artist = format_artist(song.get('artist', ''))
    
    try:
        notifier = WeComNotifier()
        
        # 使用 DownloadService 下载
        download_service = DownloadService()
        result = await download_service.download_audio(
            title=title,
            artist=artist,
            album=song.get('album', '')
        )
        
        if not result:
            await notifier.send_text(f"❌ 下载失败：{title}", [user_id])
            return
        
        # 使用 WeChatDownloadService 保存记录
        async with AsyncSessionLocal() as db:
            record_result = await WeChatDownloadService.create_or_update_record(
                db=db,
                song=song,
                download_result=result,
                cover_url=song.get('cover', '')
            )
        
        if record_result:
            await notifier.send_news_message(
                title=f"✅ 下载完成: {title}",
                description=f"🎙️ {artist}\n💾 已加入收藏",
                url=record_result.get('magic_url', ''),
                pic_url=record_result.get('cover_url', ''),
                user_ids=[user_id]
            )
        else:
            await notifier.send_text(f"⚠️ 下载成功但保存失败", [user_id])
            
    except Exception as e:
        logger.error(f"后台下载错误: {e}")
        try:
            await WeComNotifier().send_text(f"❌ 系统错误：{e}", [user_id])
        except:
            pass


async def background_add_artist(target: dict, user_id: str):
    """后台添加歌手监控"""
    name = target.get('name', '')
    
    try:
        notifier = WeComNotifier()
        await notifier.send_text(f"⏳ 正在添加 '{name}'...", [user_id])
        
        # 添加到监控
        added_sources = []
        
        if target.get('netease_id') or target.get('source') == 'netease':
            source_id = target.get('netease_id') or target.get('id', '')
            if add_monitored_user('netease', str(source_id), name, avatar=target.get('avatar')):
                added_sources.append("网易云")
        
        if target.get('qqmusic_id') or target.get('source') == 'qqmusic':
            source_id = target.get('qqmusic_id') or target.get('id', '')
            if add_monitored_user('qqmusic', str(source_id), name, avatar=target.get('avatar')):
                added_sources.append("QQ音乐")
        
        if added_sources:
            msg = f"✅ 已添加 '{name}' 到监控：\n" + " / ".join(added_sources)
            await notifier.send_text(msg, [user_id])
        else:
            await notifier.send_text(f"⚠️ 未能添加 '{name}'", [user_id])
            
    except Exception as e:
        logger.error(f"添加歌手错误: {e}")
        try:
            await WeComNotifier().send_text(f"❌ 系统错误：{e}", [user_id])
        except:
            pass

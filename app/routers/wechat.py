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
        
        reply_content = await dispatch_command(content, user_id)
        
        if not reply_content:
            return Response("success")
        
        reply = create_reply(reply_content, msg)
        xml = crypto.encrypt_message(reply.render(), nonce, timestamp)
        return Response(content=xml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"回调异常: {e}", exc_info=True)
        return Response("Error", status_code=500)


async def dispatch_command(content: str, user_id: str) -> Optional[str]:
    """命令分发器"""
    
    # 1. 帮助指令
    if content.lower() in ["帮助", "help", "/help", "菜单", "?"]:
        return (
            "🤖 Music Monitor 助手\n\n"
            "支持以下自然语言指令：\n\n"
            "🔍 搜歌与下载\n"
            "发送 `周杰伦` 或 `下载 稻香`\n"
            "-> 返回搜索结果，回复序号下载\n\n"
            "🎤 歌手监控\n"
            "发送 `歌手 周杰伦`\n"
            "-> 自动添加监控并开始补全\n\n"
            "💡 提示：直接发送文字即可搜索"
        )

    # 2. 数字选择 (上下文敏感)
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
                    return f"🚀 开始下载：\n{target.get('title', '未知')} - {artist}\n下载完成后将推送卡片通知。"
                elif stype == 'artist':
                    asyncio.create_task(background_add_artist(target, user_id))
                    return f"🚀 正在添加歌手：\n{target.get('name', '未知')}\n添加完成后将推送卡片通知。"
                
                await clear_db_session(user_id)
            else:
                return f"⚠️ 请输入有效的序号 (1-{len(results)})"
        else:
            return "⚠️ 会话已过期或不存在，请重新搜索。"
    
    # 3. 意图识别
    intent = "song" # 默认搜歌
    keyword = content
    
    # 显式指令前缀
    if content.lower().startswith(("歌手", "监控", "/artist", "添加")):
        intent = "artist"
        # 移除前缀
        for p in ["歌手", "监控", "/artist", "添加"]:
            if content.lower().startswith(p):
                keyword = content[len(p):].strip()
                break
    elif content.lower().startswith(("下载", "搜歌", "歌曲", "/song")):
        intent = "song"
        for p in ["下载", "搜歌", "歌曲", "/song"]:
            if content.lower().startswith(p):
                keyword = content[len(p):].strip()
                break
    
    if not keyword:
         return "🤔 请输入关键词，例如：'周杰伦' 或 '歌手 周杰伦'"

    # 4. 执行搜索
    if intent == "song":
        return await handle_song_search(keyword, user_id)
    else:
        return await handle_artist_search(keyword, user_id)


def format_artist(artist_field) -> str:
    """格式化歌手字段"""
    if isinstance(artist_field, list):
        return "/".join(str(a) for a in artist_field)
    return str(artist_field) if artist_field else ""


async def handle_song_search(keyword: str, user_id: str) -> str:
    """搜索歌曲"""
    try:
        aggregator = MusicAggregator()
        results = await asyncio.wait_for(
            aggregator.search_song(keyword, limit=8),
            timeout=8.0
        )
        
        if not results:
            return f"😔 未找到歌曲：'{keyword}'"
        
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
    try:
        aggregator = MusicAggregator()
        results = await asyncio.wait_for(
            aggregator.search_artist(keyword, limit=5),
            timeout=8.0
        )
        
        if not results:
            return f"😔 未找到歌手：'{keyword}'"
        
        # 缓存结果 - 这次我们缓存足够的信息以便 SubscriptionService 使用
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
    from app.services.notification import NotificationService
    
    title = song.get('title', '')
    artist = format_artist(song.get('artist', ''))
    
    try:
        # 使用 DownloadService 下载
        download_service = DownloadService()
        result = await download_service.download_audio(
            title=title,
            artist=artist,
            album=song.get('album', '')
        )
        
        if not result:
            await WeComNotifier().send_text(f"❌ 下载失败：{title}", [user_id])
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
            # 发送卡片通知
            await NotificationService.send_download_card(
                title=title,
                artist=artist,
                album=song.get('album', ''),
                cover=record_result.get('cover_url', ''),
                magic_link=record_result.get('magic_url', ''),
                quality=record_result.get('audio_quality') or 'Standard'
            )
        else:
            await WeComNotifier().send_text(f"⚠️ 下载成功但保存失败", [user_id])
            
    except Exception as e:
        logger.error(f"后台下载错误: {e}")
        try:
            await WeComNotifier().send_text(f"❌ 系统错误：{e}", [user_id])
        except:
            pass


async def background_add_artist(target: dict, user_id: str):
    """后台添加歌手监控"""
    from app.services.subscription import SubscriptionService
    from app.services.notification import NotificationService
    from app.routers.subscription import run_refresh_task # 复用路由中的所有后台任务逻辑
    
    name = target.get('name', '')
    source = target.get('source', '')
    source_id = str(target.get('id', ''))
    avatar = target.get('avatar', '')
    
    # 兼容处理：如果是 pyncm 或 qqmusic-api 返回的格式差异
    if not source_id:
        source_id = str(target.get('netease_id') or target.get('qqmusic_id') or '')
    
    logger.info(f"WeChat trigger add artist: {name} ({source}:{source_id})")
    
    try:
        async with AsyncSessionLocal() as db:
            success = await SubscriptionService.add_artist(
                db, name, source, source_id, avatar
            )
            
            if success:
                # 1. 发送成功卡片
                # 注意：此时可能还没拿到逻辑艺人ID，add_artist 返回的是bool。
                # 重新查一下DB获取ID
                from sqlalchemy import select
                from app.models.artist import Artist
                stmt = select(Artist).where(Artist.name == name)
                artist_obj = (await db.execute(stmt)).scalars().first()
                if artist_obj:
                    await NotificationService.send_artist_card(
                        artist_name=artist_obj.name,
                        artist_id=str(artist_obj.id),
                        avatar=artist_obj.avatar or avatar
                    )
                
                # 2. 触发后台任务 (智能关联 + 刷新)
                # 使用 asyncio.create_task 运行 background task，不阻塞当前流程
                # 但我们需要在新的 loop 中运行吗？FastAPI BackgroundTasks 是注入的。
                # 这里我们直接 asyncio.create_task 一个 wrapper
                asyncio.create_task(run_refresh_task(name, source, source_id))
                
            else:
                await WeComNotifier().send_text(f"⚠️ 未能添加 '{name}'", [user_id])
            
    except Exception as e:
        logger.error(f"添加歌手错误: {e}")
        try:
            await WeComNotifier().send_text(f"❌ 系统错误：{e}", [user_id])
        except:
            pass

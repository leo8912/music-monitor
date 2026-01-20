import logging
import time
import xml.etree.cElementTree as ET
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.crypto import WeChatCrypto
from wechatpy import parse_message, create_reply
from sqlalchemy.orm import Session
from datetime import datetime

from core.config import config
from core.database import SessionLocal, MediaRecord
from core.audio_downloader import AudioDownloader, AudioInfo
from app.services.favorites_service import FavoritesService

logger = logging.getLogger(__name__)
router = APIRouter()

def get_crypto():
    wecom_cfg = config.get('notify', {}).get('wecom', {})
    token = wecom_cfg.get('token')
    encoding_aes_key = wecom_cfg.get('encoding_aes_key')
    corpid = wecom_cfg.get('corpid')
    
    if not token or not encoding_aes_key or not corpid:
        return None
    return WeChatCrypto(token, encoding_aes_key, corpid)

@router.get("/api/wecom/callback")
async def wechat_verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    crypto = get_crypto()
    if not crypto:
        return Response("WeCom config missing", status_code=500)
    
    try:
        decrypted_echostr = crypto.check_signature(
            msg_signature,
            timestamp,
            nonce,
            echostr
        )
        return Response(content=decrypted_echostr)
    except InvalidSignatureException:
        raise HTTPException(status_code=403, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Verify error: {e}")
        raise HTTPException(status_code=500, detail="Verify failed")

@router.post("/api/wecom/callback")
async def wechat_callback(request: Request, msg_signature: str, timestamp: str, nonce: str):
    crypto = get_crypto()
    if not crypto:
        return Response("Config missing", status_code=500)
        
    body = await request.body()
    try:
        decrypted_xml = crypto.decrypt_message(
            body,
            msg_signature,
            timestamp,
            nonce
        )
    except InvalidSignatureException:
        raise HTTPException(status_code=403, detail="Invalid signature")
        
    # Parse message
    msg = parse_message(decrypted_xml)
    if msg.type != 'text':
        return Response("success")
        
    content = msg.content.strip()
    user_id = msg.source # WeCom UserID
    
    reply_content = ""
    
    # Session Cache (Global)
    # Global Session
    global search_session
    if 'search_session' not in globals():
        search_session = {}
        
    # 1. Handle Selection (Number)
    if content.isdigit():
        idx = int(content) - 1
        if user_id in search_session:
            session = search_session[user_id]
            # Check expiry (5 mins)
            if (datetime.now() - session['time']).total_seconds() > 300:
                reply_content = "⚠️ 搜索结果已过期，请重新搜索。"
                del search_session[user_id]
            elif 0 <= idx < len(session['results']):
                # Dispatch based on type
                stype = session.get('type', 'song')
                target = session['results'][idx]
                
                import asyncio
                if stype == 'song':
                    asyncio.create_task(background_download_and_fav(target, user_id))
                    reply_content = f"🚀 已收到，开始下载并收藏第 {idx+1} 首：\n{target['title']} - {format_artist(target['artist'])}"
                elif stype == 'artist':
                    asyncio.create_task(background_add_artist(target, user_id))
                    reply_content = f"🚀 已收到，正在添加歌手监控：\n{target['name']} ({target['source']})"
                
                del search_session[user_id]
            else:
                reply_content = f"⚠️ 请输入有效的序号 (1-{len(session['results'])})"
        else:
            # Treat number as query if no session? Or tell user no session?
            # Let's verify if it might be a song name (some songs have number names).
            # But usually it's selection.
            reply_content = "⚠️ 无待选列表，请先发送歌名或歌手名搜索。"

    # 2. Handle Commands
    else:
        # Determine intent
        # Default -> Artist Search
        # Explicit "下载/喜欢/收藏" -> Song Search
        
        intent = "artist"
        keyword = content
        
        for prefix in ["下载", "喜欢", "收藏", "搜歌", "歌曲"]:
            if content.startswith(prefix):
                intent = "song"
                keyword = content[len(prefix):].strip()
                break
        
        if not keyword:
            reply_content = "请提供关键词"
        else:
            if intent == "song":
                reply_content = await handle_song_search(keyword, user_id)
            else:
                reply_content = await handle_artist_search(keyword, user_id)

    reply = create_reply(reply_content, msg)
    encrypted_xml = crypto.encrypt_message(reply.render(), nonce, timestamp)
    return Response(content=encrypted_xml, media_type="application/xml")

def format_artist(artist_field):
    if isinstance(artist_field, list):
        return "/".join(artist_field)
    return str(artist_field)

async def handle_song_search(keyword: str, user_id: str) -> str:
    dl = AudioDownloader()
    search_results = []
    
    # Netease
    try:
        res_ne = await dl.search_songs(keyword, "", source="netease", count=5)
        if res_ne: search_results.extend(res_ne)
    except: pass
    
    # QQ
    try:
        res_qq = await dl.search_songs(keyword, "", source="qqmusic", count=5)
        if res_qq: search_results.extend(res_qq)
    except: pass
    
    if not search_results:
        return f"😔 未找到关于 '{keyword}' 的歌曲"
        
    # Cache Session
    global search_session
    if 'search_session' not in globals(): search_session = {}
    
    search_session[user_id] = {
        "type": "song",
        "keyword": keyword,
        "results": search_results[:5], # Limit total choice to 5? User said default 5.
                                       # Wait, if we fetch 5 from each, we have 10.
                                       # Let's show top 5-8 mixed.
        "time": datetime.now()
    }
    
    if len(search_results) > 8:
        search_results = search_results[:8]
    
    # Build text
    reply = f"🔎 找到以下歌曲（回复序号下载）：\n"
    for i, song in enumerate(search_session[user_id]['results']): # Use stored results
        if i >= 8: break
        src_icon = "🎵" if song['source'] == 'netease' else "🐧"
        artist = format_artist(song['artist'])
        reply += f"{i+1}. {src_icon} {song['title']} - {artist}\n"
        
    return reply

async def handle_artist_search(keyword: str, user_id: str) -> str:
    
    results = []
    
    # Netease
    try:
        ne_res = await run_in_threadpool(apis.cloudsearch.GetSearchResult, keyword, stype=100, limit=3)
        if ne_res.get('code') == 200 and ne_res.get('result', {}).get('artists'):
            for ar in ne_res['result']['artists']:
                results.append({
                    "source": "netease",
                    "id": str(ar['id']),
                    "name": ar['name'],
                    "avatar": ar.get('picUrl')
                })
    except Exception as e:
        logger.warning(f"Artist search error (NE): {e}")

    # QQ
    try:
        qq_res = await search.search_by_type(keyword=keyword, search_type=SearchType.SINGER, num=3)
        if qq_res and isinstance(qq_res, list):
            for ar in qq_res:
                mid = ar.get('singerMID') or ar.get('mid')
                name = ar.get('singerName') or ar.get('name')
                if mid and name:
                     results.append({
                        "source": "qqmusic",
                        "id": mid,
                        "name": name,
                        "avatar": f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{mid}.jpg"
                    })
    except Exception as e:
        logger.warning(f"Artist search error (QQ): {e}")
        
    if not results:
        return f"😔 未找到歌手 '{keyword}'"
        
    # Cache Session
    global search_session
    if 'search_session' not in globals(): search_session = {}
    
    search_session[user_id] = {
        "type": "artist",
        "keyword": keyword,
        "results": results[:5],
        "time": datetime.now()
    }
    
    # Build text
    reply = f"🎤 找到以下歌手（回复序号添加监控）：\n"
    for i, ar in enumerate(search_session[user_id]['results']):
        src_icon = "🎵" if ar['source'] == 'netease' else "🐧"
        reply += f"{i+1}. {src_icon} {ar['name']} (ID: {ar['id']})\n"
        
    return reply


async def background_add_artist(target, user_id):
    try:
        name = target['name']
        source = target['source']
        uid = target['id']
        
        # Add to Config
        success = add_monitored_user(source, uid, name)
        
        if success:
            await WeComNotifier().send_text(f"✅ 已添加 {name} 到 {source} 监控列表！\n正在尝试同步新歌...", [user_id])
            # Trigger Sync
            await sync_artist_immediate(name, source, target.get('avatar'), notify=True)
        else:
             await WeComNotifier().send_text(f"⚠️ 添加失败：{name} 可能已存在", [user_id])
             
    except Exception as e:
        logger.error(f"Bg add artist error: {e}")
        await WeComNotifier().send_text(f"❌ 系统错误：{e}", [user_id])

async def background_download_and_fav(song, user_id):
    title = song['title']
    artist = format_artist(song['artist'])
    
    try:
        dl = AudioDownloader()
        
        # Download
        # This might take time
        # TODO: Add progress notify if really needed? 
        # But this is "Background", users expect it to just popup when done.
        
        res = await dl.download(
            source=song['source'],
            song_id=song['id'],
            title=title,
            artist=artist,
            album=song.get('album', ''),
            quality=999
        )
        
        if not res:
            await WeComNotifier().send_text(f"❌ 下载失败：{title}\n原因：未找到有效资源", [user_id])
            return

        # Update DB & Favorite
        db = SessionLocal()
        try:
            unique_key = f"{song['source']}_{song['id']}"
            record = db.query(MediaRecord).filter_by(unique_key=unique_key).first()
            if not record:
                record = MediaRecord(
                    unique_key=unique_key,
                    source=song['source'],
                    media_type="audio",
                    media_id=song['id'],
                    title=title,
                    author=artist,
                    album=song.get('album'),
                    publish_time=datetime.now()
                )
                db.add(record)
                db.commit()
                db.refresh(record)
            
            # Update path
            record.local_audio_path = res['local_path']
            record.audio_quality = res['quality']
            
            # Move to favorites (Add to favorite list)
            # This triggers file copy inside FavoritesService
            fav_res = await FavoritesService.toggle_favorite(db, unique_key, force_state=True)
            
            db.commit()
            
            final_msg = f"✅ 下载并收藏成功！\n🎵 {title} - {artist}\n📁 已存入精选集"
            await WeComNotifier().send_text(final_msg, [user_id])
            
        except Exception as e:
            logger.error(f"DB/Fav Error: {e}")
            await WeComNotifier().send_text(f"⚠️ 下载成功但收藏失败：{e}", [user_id])
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Bg task error: {e}")
        await WeComNotifier().send_text(f"❌ 系统错误：{e}", [user_id])

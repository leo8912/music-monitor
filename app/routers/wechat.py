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
    reply_content = "收到指令"
    
    # Process Command
    if content.startswith("喜欢") or content.startswith("收藏"):
        # Format: 喜欢 SongName
        keyword = content[2:].strip()
        if keyword:
            reply_content = await handle_favorite_command(keyword)
        else:
            reply_content = "请提供歌曲名，例如：喜欢 晴天"
            
    elif content.startswith("下载"):
        keyword = content[2:].strip()
        if keyword:
            reply_content = await handle_download_command(keyword)
        else:
            reply_content = "请提供歌曲名，例如：下载 晴天"
    else:
        # Default: Download if it looks like a song name?
        # User said: "发送 歌曲名就自动下载到指定文件夹"
        # So treat as download.
        reply_content = await handle_download_command(content)

    reply = create_reply(reply_content, msg)
    encrypted_xml = crypto.encrypt_message(reply.render(), nonce, timestamp)
    return Response(content=encrypted_xml, media_type="application/xml")

async def handle_favorite_command(keyword: str) -> str:
    dl = AudioDownloader()
    # Search top 1
    # Search all sources? Or default netease?
    results = await dl.search_songs(keyword, "", source="netease", count=1)
    if not results:
        # Try QQ
        results = await dl.search_songs(keyword, "", source="qqmusic", count=1)
    
    if not results:
        return f"未找到歌曲: {keyword}"
        
    song = results[0]
    title = song['title']
    artist = " ".join(song['artist']) if isinstance(song['artist'], list) else song['artist']
    unique_key = f"{song['source']}_{song['id']}"
    
    # Create/Get Record
    db = SessionLocal()
    try:
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
                cover=None, # Need to fetch? Logic inside fetch handles it 
                publish_time=datetime.now()
             )
             db.add(record)
             db.commit()
             db.refresh(record)
             
        # Toggle Favorite (Force True)
        res = await FavoritesService.toggle_favorite(db, unique_key, force_state=True)
        if res['success']:
            return f"✅ 已收藏: {title} - {artist}"
        else:
            return f"❌ 收藏失败: {res.get('message')}"
    except Exception as e:
        logger.error(f"Fav cmd error: {e}")
        return f"处理异常: {str(e)}"
    finally:
        db.close()

async def handle_download_command(keyword: str) -> str:
    # Similar to favorite but just download
    # Logic: Search -> Download
    dl = AudioDownloader()
    results = await dl.search_songs(keyword, "", source="netease", count=1)
    if not results:
        results = await dl.search_songs(keyword, "", source="qqmusic", count=1)
        
    if not results:
        return f"未找到歌曲: {keyword}"
        
    song = results[0]
    title = song['title']
    artist = " ".join(song['artist']) if isinstance(song['artist'], list) else song['artist']
    
    # Trigger download
    # We can reuse download logic or simply call download
    # Note: AudioDownloader.download doesn't strictly depend on DB, but for consistency we should update DB.
    
    try:
         # Async download
         # Ideally background task? But user might want confirmation.
         # For responsiveness, we can await it if it's fast (search is fast, download might be slow).
         # If download is slow (>5s), WeCom might timeout (5s limit for passive reply).
         # CRITICAL: WeCom passive reply timeout is 5s.
         # So we should probably background the download and reply "Start downloading".
         # Or assume it works.
         
         # Creating a background task
         import asyncio
         asyncio.create_task(background_download(song))
         
         return f"🚀 开始下载: {title} - {artist}"
    except Exception as e:
        return f"启动下载失败: {e}"

async def background_download(song):
    try:
        dl = AudioDownloader()
        title = song['title']
        artist = " ".join(song['artist']) if isinstance(song['artist'], list) else song['artist']
        
        # Download
        res = await dl.download(
            source=song['source'],
            song_id=song['id'],
            title=title,
            artist=artist,
            album=song.get('album'),
            quality=999
        )
        
        if res:
            # Update DB
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
                
                record.local_audio_path = res['local_path']
                record.audio_quality = res['quality']
                db.commit()
             finally:
                 db.close()
            # Notify? WeCom Active Notify?
    except Exception as e:
        logger.error(f"Bg download error: {e}")

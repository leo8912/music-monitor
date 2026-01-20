import os
import logging
import yaml
import asyncio
from datetime import datetime
from urllib.parse import quote
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool

import pyncm.apis.track

# Core Imports
from core.config import config
from core.database import SessionLocal, MediaRecord
from core.audio_downloader import AudioDownloader, AUDIO_CACHE_DIR
from app.schemas import DownloadRequest, ArtistConfig
from app.services.media_service import find_artist_ids, sync_artist_immediate
from app.services.favorites_service import FavoritesService

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-memory cache for playback URLs
# Key: {source}:{id}, Value: {url, timestamp}
playback_cache = {}

@router.post("/api/download_audio")
async def download_audio_endpoint(req: DownloadRequest):
    """Download audio file and update database."""
    # cookie_str is not supported by AudioDownloader yet
    dl = AudioDownloader()
    
    logger.info(f"收到下载请求: {req.title} - {req.artist}")
    
    from core.websocket import manager

    async def progress_report(msg: str):
        try:
            await manager.broadcast({
                "type": "toast",
                "level": "info",
                "message": msg
            })
        except: pass

    try:
        result = await dl.download(
            song_id=req.song_id,
            source=req.source,
            title=req.title,
            artist=req.artist,
            album=req.album,
            pic_url=req.pic_url,
            quality=999,
            progress_callback=progress_report
        )
        
        if result:
            # 更新数据库
            db = SessionLocal()
            try:
                # 尝试找到记录，如果没有则不更新（通常应该有）
                # 这里假设前端传来的 song_id 就是 media_id
                # 注意：MediaRecord 的 unique_key 生成规则是 f"{source}_{media_id}"
                unique_key = f"{req.source}_{req.song_id}"
                record = db.query(MediaRecord).filter_by(unique_key=unique_key).first()
                if record:
                    record.local_audio_path = result.get("local_path")
                    record.audio_quality = result.get("quality")
                    
                    # Update lyric if available
                    if result.get("lyric"):
                        record.lyrics = result.get("lyric")
                        record.lyrics_updated_at = datetime.now()
                    
                    db.commit()
                    logger.info(f"数据库记录已更新: {req.title}")
            except Exception as e:
                logger.error(f"更新数据库失败: {e}")
            finally:
                db.close()
                
            return {
                "local_path": result.get("local_path"),
                "quality": result.get("quality"),
                "has_lyric": result.get("has_lyric")
            }
        else:
            await manager.broadcast({
                "type": "toast",
                "level": "error",
                "message": "😔 未找到有效音源或下载中断"
            })
            raise HTTPException(status_code=500, detail="Download failed (downloader returned None)")
            
    except Exception as e:
        logger.error(f"下载异常: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/api/audio/{filename:path}")
async def serve_audio(filename: str):
    """Serve audio file from cache with correct Content-Disposition."""
    # Check Favorites first (Priority)
    fav_dir = config.get('storage', {}).get('favorites_dir', 'favorites')
    fav_path = os.path.join(fav_dir, filename)
    
    file_path = os.path.join(AUDIO_CACHE_DIR, filename)
    
    # Logic: If exists in Favorites, serve it (safe from cache cleanup). 
    # If not, check Cache.
    
    if os.path.exists(fav_path):
        file_path = fav_path
    elif not os.path.exists(file_path):
        # -------------------------------------------------------------
        # 优化体验：如果文件不存在但数据库有记录，尝试立即重新下载
        # -------------------------------------------------------------
        from core.audio_downloader import AudioDownloader
        from core.websocket import manager
        
        db = SessionLocal()
        try:
            # 查找关联的记录
            record = db.query(MediaRecord).filter(MediaRecord.local_audio_path.like(f"%{filename}")).first()
            
            if record:
                logger.info(f"File missing for {record.title} (ID:{record.media_id}), attempting immediate re-download...")
                
                # 定义并使用 WebSocket 回调
                async def progress_report(msg: str):
                    try:
                        await manager.broadcast({
                            "type": "toast",  # 前端识别类型
                            "level": "info",
                            "message": msg
                        })
                    except: pass

                # 触发下载 (阻塞等待)
                dl = AudioDownloader()
                # download 方法需要 song_id, source 等参数
                result = await dl.download(
                    song_id=record.media_id,
                    source=record.source,
                    title=record.title,
                    artist=record.author,
                    album=record.album,
                    pic_url=record.cover,
                    quality=999,
                    progress_callback=progress_report
                )
                
                if result and result.get('local_path') and os.path.exists(result['local_path']):
                     logger.info(f"Buffered/Downloaded successfully: {filename}")
                     real_path = result['local_path']
                     real_filename = os.path.basename(real_path)
                     
                     # 检查文件名是否发生变化 (例如 .flac -> .mp3)
                     if real_filename != filename:
                         logger.info(f"File extension changed ({filename} -> {real_filename}), redirecting...")
                         return RedirectResponse(f"/api/audio/{real_filename}")
                     
                     # 同步更新 file_path 变量以便后续 FileResponse 使用
                     # 注意：外层的 file_path 是基于 filename 构造的，如果没变就不需要更新
                     pass
            else:
                 logger.warning(f"File not found and no DB record matches key: {filename}")
                 # 只有当确实找不到记录时，才考虑清理旧的错误路径？
                 # 为了防止死循环，这里可以尝试把这个路径置空
                 pass

        except Exception as e:
            logger.error(f"Auto-download failed: {e}")
        finally:
            db.close()

        # 再次检查文件是否存在
        # 如果刚才发生了重定向，这里不会执行
        
        # 重新计算 file_path (虽然如果文件名变了应该已经 redirect 了)
        # 但如果文件名没变，我们需要确保 file_path 指向的是存在的文件
        file_path = os.path.join(AUDIO_CACHE_DIR, filename)
        
        if not os.path.exists(file_path):
             # 只有努力过了还是没有，才放弃
             raise HTTPException(status_code=404, detail="Audio file not found")
         
    # Determine media type
    media_type = "audio/mpeg"
    if filename.endswith(".flac"): media_type = "audio/flac"
    elif filename.endswith(".wav"): media_type = "audio/wav"
    elif filename.endswith(".m4a"): media_type = "audio/mp4"
    elif filename.endswith(".ogg"): media_type = "audio/ogg"
    
    # URL encode filename for header
    filename_encoded = quote(filename)
    
    return FileResponse(
        file_path, 
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{filename_encoded}"}
    )

@router.get("/api/search_songs")
async def search_songs(title: str, artist: str, album: str = Query(None)):
    """Search songs across multiple sources."""
    dl = AudioDownloader()
    results = await dl.search_songs_all_sources(title, artist, album=album)
    return results

@router.post("/api/repair_audio")
async def repair_audio(req: DownloadRequest):
    """Force re-download a specific song version and update DB."""
    dl = AudioDownloader()
    logger.info(f"收到修复/重新下载请求: {req.title} - {req.artist} (Source: {req.source}, ID: {req.song_id})")
    
    try:
        # 强制下载 (忽略缓存由 AudioDownloader 内部逻辑由于我们传入了特定的 song_id 和 source 触发 fetch_audio_url)
        # 注意：为了确保它是“重新”下载，我们需要确保它不直接返回已有的本地文件。
        # 在 AudioDownloader.download 中，它会先查 cache。
        # 我们可以稍微修改 download 方法支持 force 参数，或者简单点：由调用者先删除本地文件（如果不一致）。
        # 但更稳妥的是在 download 逻辑里如果命中了 cache 就直接返回。
        # 这里我们的目标是允许用户选择“不同”的版本。
        
        result = await dl.download(
            song_id=req.song_id,
            source=req.source,
            title=req.title,
            artist=req.artist,
            album=req.album,
            pic_url=req.pic_url,
            quality=999
        )
        
        if result:
            db = SessionLocal()
            try:
                # 找到当前正在播放/需要修复的记录
                # 前端应该传回原始的 unique_key 或者我们根据标题歌手找
                # 这里我们假设前端传来的 song_id 就是我们要下载的新版本，
                # 而我们需要更新的是数据库中对应的记录。
                # 这里的逻辑稍显复杂，因为用户可能正在播放 Netease 的歌，但选择了 QQMusic 的来源修复。
                # 我们应该更新“匹配”的记录。
                
                # 尝试根据标题和歌手查找记录（跨平台修复）
                record = db.query(MediaRecord).filter(
                    MediaRecord.title == req.title,
                    MediaRecord.author == req.artist
                ).first()
                
                if record:
                    record.local_audio_path = result.get("local_path")
                    record.audio_quality = result.get("quality")
                    # 如果来源变了，是否更新 source/media_id? 
                    # 建议保留原始 source/media_id 作为跟踪，只更新音频路径。
                    db.commit()
                    logger.info(f"修复完成，数据库已更新: {req.title}")
                else:
                    logger.warning(f"未找到对应的数据库记录进行更新: {req.title}")
                    
                return result
            finally:
                db.close()
        else:
            raise HTTPException(status_code=500, detail="Repair failed")
    except Exception as e:
        logger.error(f"修复异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/favorites/toggle")
async def toggle_favorite(req: DownloadRequest):
    """Toggle favorite state. Request similar to download but uses logic to identify record."""
    # We construct unique_key from source and song_id
    unique_key = f"{req.source}_{req.song_id}"
    db = SessionLocal()
    try:
        # Check if record exists, if not, we can't favorite? 
        # Actually user might want to favorite a song from search results that isn't downloaded yet.
        # But FavoritesService logic (step 1) handles download if record exists.
        # Does record exist?
        record = db.query(MediaRecord).filter_by(unique_key=unique_key).first()
        if not record:
             # Create record on the fly if missing (similar to download)
             # But we need basic metadata. Frontend 'DownloadRequest' has it.
             # We should probably call download endpoint logic if missing?
             # For simpler logic, let's assume it exists or we create a shallow one.
             pass 
             # Actually FavoritesService logic requires record.
             # If record doesn't exist, we must create it.
             # Let's simple check if we need to 'process_media_item' logic?
             # Creating a record manually:
             record = MediaRecord(
                unique_key=unique_key,
                source=req.source,
                media_type="audio",
                media_id=req.song_id,
                title=req.title,
                author=req.artist,
                album=req.album,
                cover=req.pic_url,
                publish_time=datetime.now()
             )
             db.add(record)
             db.commit()
             db.refresh(record)
        
        result = await FavoritesService.toggle_favorite(db, unique_key)
        return result
    except Exception as e:
        logger.error(f"Favorite toggle error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/api/lyric/{source}/{song_id}")
async def get_lyric(source: str, song_id: str, title: str = Query(None), artist: str = Query(None)):
    """Get lyric from DB or fetch if missing."""
    db = SessionLocal()
    try:
        unique_key = f"{source}_{song_id}"
        record = db.query(MediaRecord).filter_by(unique_key=unique_key).first()
        
        if record and record.lyrics:
             return {"lyric": record.lyrics}
        
        # If DB has no lyric, try to fetch on-the-fly
        if title and artist:
            try:
                dl = AudioDownloader()
                # _fetch_lyric is protected but we use it here for convenience
                lyric = await dl._fetch_lyric(title, artist)
                
                if lyric:
                    # Save to DB if record exists
                    if record:
                        record.lyrics = lyric
                        record.lyrics_updated_at = datetime.now()
                        db.commit()
                    return {"lyric": lyric}
            except Exception as e:
                logger.error(f"Failed to fetch lyric on-the-fly: {e}")
                
        return {"lyric": ""}
    finally:
        db.close()

@router.get("/api/artists")
async def get_artists():
    """Get all monitored artists from config."""
    artists = []
    mon_cfg = config.get('monitor', {})
    
    # Netease
    if mon_cfg.get('netease', {}).get('enabled'):
        for u in mon_cfg['netease'].get('users', []):
            artists.append({
                "name": u.get('name', u['id']), 
                "id": str(u['id']), 
                "source": "netease",
                "avatar": u.get('avatar', 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg') # Default Netease avatar or empty
            })
            
    # QQMusic
    if mon_cfg.get('qqmusic', {}).get('enabled'):
        for u in mon_cfg['qqmusic'].get('users', []):
            # Auto-construct QQ avatar if missing
            avatar = u.get('avatar', '')
            if not avatar and u['id']:
                avatar = f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{u['id']}.jpg"
                
            artists.append({
                "name": u.get('name', u['id']), 
                "id": u['id'], 
                "source": "qqmusic",
                "avatar": avatar
            })
            
    return artists

@router.post("/api/artists")
async def add_artist(artist: ArtistConfig):
    """Add new artist. If id/source missing, perform smart search."""
    # 1. Automatic Search Mode
    if not artist.id or not artist.source:
        found = await find_artist_ids(artist.name)
        if not found:
            raise HTTPException(status_code=404, detail="Artist not found on any platform")
        
        added = []
        for item in found:
            # Add each found artist
            source_cfg = config['monitor'].get(item['source'])
            if not source_cfg: continue
            
            # Check dup
            exists = False
            for u in source_cfg['users']:
                if str(u['id']) == str(item['id']):
                    exists = True
                    # Update avatar if missing?
                    if not u.get('avatar') and item.get('avatar'):
                         u['avatar'] = item['avatar']
                    break
            
            if not exists:
                new_user = {"id": item['id'], "name": artist.name}
                if item.get('avatar'):
                    new_user['avatar'] = item['avatar']
                source_cfg['users'].append(new_user) 
                added.append(f"{item['source']}:{item['name']}")
        
        if not added:
             # Just return success if simply updated/already exists, don't error
             pass 

        # Save
        with open("config.yaml", "w", encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
            
        # Trigger Background Sync & Notify for each added artist
        for i, item in enumerate(found):
            # Only if it was actually processed/added?
            # Even if it existed, user might want to re-sync/subscribe via this action.
            # Let's trigger it.
            notify_flag = (i == 0)
            asyncio.create_task(sync_artist_immediate(item['name'], item['source'], item.get('avatar'), notify=notify_flag))
            
        return {"status": "success", "message": f"已添加 {', '.join(added)}. 正在后台同步..."}

    # 2. Manual Mode (Legacy)
    source_cfg = config['monitor'].get(artist.source)
    if not source_cfg:
        raise HTTPException(status_code=400, detail="Invalid source")
        
    # Check duplicate
    for u in source_cfg['users']:
        if u['id'] == artist.id:
            raise HTTPException(status_code=400, detail="Artist already exists")
            
    source_cfg['users'].append({"id": artist.id, "name": artist.name})
    
    # Save to file
    with open("config.yaml", "w", encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
        
    # Manual Add also triggers sync
    # Manual Add also triggers sync
    asyncio.create_task(sync_artist_immediate(artist.name, artist.source, notify=True))

    return {"status": "success", "artist": artist, "message": "添加成功，正在后台同步..."}

@router.delete("/api/artists/{source}/{id}")
def delete_artist(source: str, id: str):
    """Remove artist from config and delete their songs from database."""
    source_cfg = config['monitor'].get(source)
    if not source_cfg:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Find artist name before deletion
    artist_name = None
    for u in source_cfg['users']:
        if u['id'] == id:
            artist_name = u.get('name')
            break
    
    # Filter out from config
    original_len = len(source_cfg['users'])
    source_cfg['users'] = [u for u in source_cfg['users'] if u['id'] != id]
    
    if len(source_cfg['users']) == original_len:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Save config
    with open("config.yaml", "w", encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    # Delete songs from database
    deleted_count = 0
    if artist_name:
        db = SessionLocal()
        try:
            # Delete all records where author matches the artist name
            deleted = db.query(MediaRecord).filter(
                MediaRecord.source == source,
                MediaRecord.author.contains(artist_name)
            ).delete(synchronize_session=False)
            db.commit()
            deleted_count = deleted
            logger.info(f"删除歌手 {artist_name} ({source}) 及其 {deleted_count} 首歌曲")
        except Exception as e:
            logger.error(f"删除数据库记录失败: {e}")
            db.rollback()
        finally:
            db.close()
        
    return {"status": "success", "deleted_songs": deleted_count}

@router.get("/api/play/{source}/{id}")
async def play_proxy(source: str, id: str):
    """
    Proxy to fetch direct playback URL using internal plugins.
    Fallbacks to official page if failed.
    """
    # Check cache (valid for 20 mins)
    cache_key = f"{source}:{id}"
    if cache_key in playback_cache:
        cached = playback_cache[cache_key]
        if (datetime.now() - cached['time']).total_seconds() < 1200:
            return RedirectResponse(cached['url'])

    play_url = None
    
    try:
        if source == 'netease':
            # pyncm is synchronous
            res = await run_in_threadpool(pyncm.apis.track.GetTrackAudio, [id])
            if res.get('code') == 200 and res.get('data'):
                 play_url = res['data'][0].get('url')
                 
        elif source == 'qqmusic':
            try:
                from qqmusic_api import song
                urls = await song.get_song_urls([id])
                if urls and id in urls:
                    play_url = urls[id]
            except Exception as e:
                logger.error(f"QQMusic lib error: {e}")

    except Exception as e:
        logger.error(f"Internal lib fetch error: {e}")

    if play_url:
        # Cache successful result
        playback_cache[cache_key] = {
            'url': play_url,
            'time': datetime.now()
        }
        return RedirectResponse(play_url)

    # Fallback: finding the DB record to get the official URL
    db = SessionLocal()
    try:
        record = db.query(MediaRecord).filter_by(source=source, media_id=id).first()
        if record and record.url:
            return RedirectResponse(record.url)
            
        # Last resort fallback
        if source == 'netease':
            return RedirectResponse(f"https://music.163.com/#/song?id={id}")
        elif source == 'qqmusic':
            return RedirectResponse(f"https://y.qq.com/n/ryqq/songDetail/{id}")
            
        return JSONResponse({"error": "Playback link not found"}, status_code=404)
    finally:
        db.close()

@router.get("/api/history")
def get_history(limit: int = 100, author: Optional[str] = None):
    db = SessionLocal()
    try:
        # Get active artists from config for filtering (unless specific author requested)
        active_names = set()
        
        # Optimization: If author is specified, we don't need to load all config?
        # But we still generally only show monitored artists.
        # Let's load config to be safe/consistent.
        for source in ['netease', 'qqmusic']:
             cfg = config.get('monitor', {}).get(source, {})
             if cfg.get('enabled'):
                 for u in cfg.get('users', []):
                     active_names.add(u.get('name', ''))
        
        # Build Query
        query = db.query(MediaRecord)
        
        # If specific author requested, filter at DB level (performance)
        if author:
            # Flexible match for author
            query = query.filter(MediaRecord.author.contains(author))
            
        query = query.order_by(MediaRecord.publish_time.desc()).limit(limit * 2)
        records = query.all()
        
        filtered = []
        seen_keys = set()
        
        for r in records:
            # 1. Deduplication (Title + Author)
            norm_title = "".join(filter(str.isalnum, r.title or "")).lower()
            norm_author = "".join(filter(str.isalnum, r.author or "")).lower()
            dedup_key = f"{norm_title}_{norm_author}"
            
            if dedup_key in seen_keys:
                continue
            
            # 2. Filtering (Only show monitored artists)
            # If author was requested, we assume user knows what they want (and DB filter handled it mostly).
            # But we still double check if it's "relevant" or if the author param matches.
            
            if author:
                # If specifically filtered, just pass through (DB already filtered)
                 pass
            else:
                # General View: Filter by monitored list
                is_relevant = False
                for name in active_names:
                    if name and name in (r.author or ""):
                        is_relevant = True
                        break
                if not is_relevant:
                    continue
                
            seen_keys.add(dedup_key)
            filtered.append(r)
            
            if len(filtered) >= limit:
                break
                
        return filtered
    finally:
        db.close()

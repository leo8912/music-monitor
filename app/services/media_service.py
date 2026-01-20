import logging
import asyncio
from typing import List, Optional
from datetime import datetime
import os
from starlette.concurrency import run_in_threadpool


from sqlalchemy.orm import Session
from core.database import MediaRecord, SessionLocal
from core.event_bus import event_bus
from core.config import config
from core.plugins import PLUGINS
from domain.models import MediaInfo
from core.audio_downloader import audio_downloader

import pyncm.apis.cloudsearch
from qqmusic_api.search import search_by_type, SearchType
from core.audio_downloader import AUDIO_CACHE_DIR

logger = logging.getLogger(__name__)

async def process_media_item(media: MediaInfo, db: Session, notify: bool = True) -> bool:
    """Check if media is new, save to DB. Returns True if new record added."""
    # 1. Check exact match (same source, same ID)
    key = media.unique_key()
    existing = db.query(MediaRecord).filter_by(unique_key=key).first()
    if existing:
        # Check if we need to backfill cover OR urls
        updated = False
        if not existing.cover and media.cover_url:
             existing.cover = media.cover_url
             updated = True
             
        if not existing.url and media.url:
             existing.url = media.url
             updated = True
        
        if updated:
             db.commit()
             logger.info(f"Updated metadata for existing record: {media.title}")
        return False

    # 2. Check cross-platform duplicate (same title, same artist, same album)
    query = db.query(MediaRecord).filter(
        MediaRecord.title == media.title,
        MediaRecord.author == media.author,
        MediaRecord.media_type == media.type.value
    )
    
    if media.album:
         query = query.filter(MediaRecord.album == media.album)
         
    cross_platform_dup = query.first()

    if cross_platform_dup:
        logger.info(f"跳过重复内容 (跨平台): {media.title} (已存在于 {cross_platform_dup.source})")
        return False

    logger.info(f"发现新内容: {media.title} ({key})")
    
    # Save to DB
    record = MediaRecord(
        unique_key=key,
        source=media.source,
        media_type=media.type.value,
        media_id=media.id,
        title=media.title,
        author=media.author,
        album=media.album,
        cover=media.cover_url, 
        url=media.url,
        publish_time=media.publish_time,
        is_pushed=False
    )
    db.add(record)
    db.commit()
    
    # Notify (Unified Batch Logic in caller, or single here if notify=True)
    if notify:
        await event_bus.publish("new_content", media)
        # Mark as pushed
        record.is_pushed = True
        record.push_time = datetime.now()
        db.commit()
        
    return True

async def run_check(plugin_name: str):
    """Job to run a specific plugin check."""
    logger.info(f"开始检查任务: {plugin_name}...")
    
    # Safety check if config is not loaded
    if not config:
        logger.error("Config not loaded, skipping check")
        return
    
    cfg = config['monitor'].get(plugin_name, {})
    if not cfg.get('enabled'):
        return

    plugin_cls = PLUGINS.get(plugin_name)
    if not plugin_cls:
        logger.error(f"未找到插件: {plugin_name}")
        return

    plugin = plugin_cls()
    users = cfg.get('users', [])
    
    # Use a new DB session for this job
    db = SessionLocal()
    try:
        for user in users:
            uid = user['id']
            uname = user.get('name', uid)
            try:
                items = await plugin.get_new_content(uid, uname)
                
                # Batch Processing
                added_items = []
                for item in items:
                    if await process_media_item(item, db, notify=False):
                        added_items.append(item)
                
                # Notification Logic
                if added_items:
                    # Filter for notification (last 365 days)
                    recent_items = [
                        i for i in added_items 
                        if (datetime.now() - i.publish_time).days <= 365
                    ]
                    
                    if not recent_items:
                        logger.info(f"Found {len(added_items)} new items, but none are recent. Skipping notify.")
                        
                    elif len(recent_items) == 1:
                        # Single Item -> Single Push
                        item = recent_items[0]
                        logger.info(f"Pushing single new item: {item.title}")
                        await event_bus.publish("new_content", item)
                        
                        # Mark pushed
                        rec = db.query(MediaRecord).filter_by(unique_key=item.unique_key()).first()
                        if rec:
                            rec.is_pushed = True
                            rec.push_time = datetime.now()
                            db.commit()
                            
                    else:
                        # Multiple Items -> Batch Push
                        logger.info(f"Pushing batch summary for {len(recent_items)} items")
                        # We construct a synthetic 'media' object or specialized event for batch?
                        # Or just reuse 'new_content' but with a special flag?
                        # Simplest: Modify handle_new_content to accept a list? No.
                        # Create a summary media item.
                        
                        top_items = sorted(recent_items, key=lambda x: x.publish_time, reverse=True)[:5]
                        titles = [f"🎵 {i.title} ({i.publish_time.strftime('%Y-%m-%d')})" for i in top_items]
                        summary_text = "\n".join(titles)
                        if len(recent_items) > 5:
                            summary_text += f"\n... 以及其他 {len(recent_items)-5} 首"
                            
                        # Construct a 'Fake' MediaInfo for notification
                        # We pick the latest one as the 'Main' one but change description
                        latest = top_items[0]
                        latest.title = f"{uname} 发布了 {len(recent_items)} 首新歌"
                        # We attach a special attribute to tell handle_new_content to use our description?
                        # Actually handle_new_content uses `media.title`.
                        # We can just rely on the fact that we are passing a modified object.
                        # But wait, `process_media_item` saved the REAL object to DB.
                        # We are passing the `MediaInfo` object (memory) to event bus.
                        
                        # Let's clone it roughly
                        import copy
                        batch_media = copy.copy(latest)
                        batch_media.title = f"{uname} 新增 {len(recent_items)} 首歌曲"
                        batch_media.source = latest.source # Keep source for jump
                        # Batch doesn't have a single URL. Maybe link to artist page?
                        # Or keeping the latest song URL is fine.
                        
                        # We need a way to pass the custom description to `handle_new_content`.
                        # `handle_new_content` constructs message from fields.
                        # Refactoring `handle_new_content` to check for `custom_description` attribute is best.
                        batch_media.custom_description = summary_text
                        
                        await event_bus.publish("new_content", batch_media)
                        
                        # Mark all recent as pushed
                        for i in recent_items:
                            rec = db.query(MediaRecord).filter_by(unique_key=i.unique_key()).first()
                            if rec:
                                rec.is_pushed = True
                                rec.push_time = datetime.now()
                        db.commit()
            except Exception as e:
                logger.error(f"检查用户 {uname}({uid}) ({plugin_name}) 时出错: {e}")
    finally:
        db.close()
    
    logger.info(f"检查完成: {plugin_name}")

async def find_artist_ids(name):
    """Find artist IDs in both Netease and QQ Music."""
    results = []
    
    # Netease
    try:
        data = await run_in_threadpool(pyncm.apis.cloudsearch.GetSearchResult, name, stype=100)
        if 'result' in data and 'artists' in data['result'] and data['result']['artists']:
            first = data['result']['artists'][0]
            # Verify name match to avoid weird partial matches? 
            # For now accept the top result.
            results.append({
                "source": "netease", 
                "id": str(first['id']), 
                "name": first['name'],
                "avatar": first.get('picUrl', '')
            })
            logger.info(f"Smart Search Netease: Found {first['name']} ({first['id']})")
    except Exception as e:
        logger.error(f"Netease search failed: {e}")

    # QQ Music
    try:
        data = await search_by_type(name, SearchType.SINGER)
        if data:
            first = data[0]
            # QQ keys: mid, singerName/name
            mid = first.get('mid', first.get('singerMID'))
            param_name = first.get('name', first.get('singerName'))
            avatar = ""
            if mid:
                 avatar = f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{mid}.jpg"
            
            results.append({
                "source": "qqmusic",
                "id": mid,
                "name": param_name,
                "avatar": avatar
            })
            logger.info(f"Smart Search QQMusic: Found {param_name} ({mid})")
    except Exception as e:
        logger.error(f"QQMusic search failed: {e}")
        

    return results

async def check_file_integrity():
    """Background job: Verify existence of local audio files and clean DB if missing."""
    logger.info("开始执行后台文件完整性检查...")
    db = SessionLocal()
    try:
        # Get all records with local_audio_path
        records = db.query(MediaRecord).filter(MediaRecord.local_audio_path.isnot(None)).all()
        fixed_count = 0
        
        for r in records:
            # Handle path (could be relative or absolute, typically basename in this project)
            # Logic in AudioDownloader is: local_path = os.path.basename(local_path)
            # But let's be safe.
            
            # 1. Ignore "LIBRARY/" paths (managed manually by user)
            if r.local_audio_path.startswith("LIBRARY/"):
                continue
                
            # 2. Construct full path
            # Assuming strictly stored in AUDIO_CACHE_DIR
            full_path = os.path.join(AUDIO_CACHE_DIR, os.path.basename(r.local_audio_path))
            
            if not os.path.exists(full_path):
                logger.warning(f"完整性检查发现丢失文件: {r.local_audio_path} (ID: {r.unique_key}). 清除记录.")
                r.local_audio_path = None
                r.audio_quality = None
                fixed_count += 1
                
        if fixed_count > 0:
            db.commit()
            logger.info(f"文件完整性检查完成。修复了 {fixed_count} 个丢失的记录。")
        else:
            logger.info("文件完整性检查完成。未发现问题。")
            
    except Exception as e:
        logger.error(f"完整性检查失败: {e}")
    finally:
        db.close()

async def auto_cache_recent_songs():
    """Background job: Auto-download songs released within retention period."""
    # 检查自动补全开关
    auto_cache_enabled = config.get('storage', {}).get('auto_cache_enabled', True)
    if not auto_cache_enabled:
        logger.info("自动补全功能已关闭")
        return
    
    days = config.get('storage', {}).get('retention_days', 180)
    if days <= 0: return

    # Cleanup is based on publish time, so cache should match.
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    
    db = SessionLocal()
    try:
        # Query recent songs that are missing local file
        records = db.query(MediaRecord).filter(
            MediaRecord.local_audio_path.is_(None),
            MediaRecord.publish_time >= cutoff
        ).order_by(MediaRecord.publish_time.desc()).limit(5).all()
        
        if not records:
            return

        logger.info(f"Auto-cache start: Found {len(records)} recent songs missing local file.")
        
        for r in records:
            # Check source support
            if r.source not in ['netease', 'qqmusic']: 
                continue
            
            logger.info(f"Auto-caching recent song: {r.title} ({r.source})")
            try:
                # Re-type to ensure no invisible chars causing NameError
                res = await audio_downloader.download(
                    source=r.source,
                    song_id=r.media_id,
                    title=r.title,
                    artist=r.author,
                    album=str(r.album or ""),
                    pic_url=r.cover,
                    quality=999
                )
                
                if res:
                     r.local_audio_path = res['local_path']
                     r.audio_quality = res.get('quality')
                     db.commit()
                     logger.info(f"Auto-cache success: {r.title}")
                else:
                    logger.warning(f"Auto-cache failed (no url): {r.title}")
                    
            except Exception as e:
                logger.error(f"Auto-cache download error for {r.title}: {e}")
                
    except Exception as e:
        logger.error(f"Auto-cache job failed: {e}")
    finally:
        db.close()

async def sync_artist_immediate(artist_name: str, source: str, avatar: str = None, notify: bool = True):
    """
    Trigger immediate sync for a newly added artist.
    1. Fetch recent songs (limit 50)
    2. Save to DB
    3. Trigger Auto-Cache
    4. Send Notification (if notify=True)
    """
    logger.info(f"Executing immediate sync for new artist: {artist_name} ({source})")
    
    # 1. Notify "Subscribed" immediately
    if notify:
        from notifiers.wecom import WeComNotifier
        
        # Instantiate notifier with current config
        notify_cfg = config.get('notify', {})
        wecom_cfg = notify_cfg.get('wecom', {})
        
        if wecom_cfg.get('enabled') and wecom_cfg.get('corpid'):
            try:
                notifier = WeComNotifier(
                    corp_id=wecom_cfg.get('corpid') or wecom_cfg.get('corp_id'),
                    secret=wecom_cfg.get('corpsecret') or wecom_cfg.get('secret'),
                    agent_id=wecom_cfg.get('agentid') or wecom_cfg.get('agent_id')
                )
                
                # Deep link to artist page
                from urllib.parse import quote
                link = config.get('global', {}).get('external_url', '')
                if link:
                    link = f"{link}/?artist={quote(artist_name)}"
                    
                desc = f"已成功订阅 {artist_name}。\n正在立即同步最近 50 首歌曲并开始缓存..."
                
                await notifier.send_news_message(
                   title=f"❤️ 关注成功: {artist_name}",
                   description=desc,
                   url=link,
                   pic_url=avatar or ""
                )
            except Exception as e:
                logger.error(f"Failed to send subscription notification: {e}")

    # 2. Sync Logic
    plugin_cls = PLUGINS.get(source)
    if not plugin_cls: return
    
    plugin = plugin_cls()
    
    cfg = config['monitor'].get(source, {})
    uid = None
    for u in cfg.get('users', []):
        if u.get('name') == artist_name:
            uid = u['id']
            break
            
    if not uid: return
    
    try:
        # Fetch content
        items = await plugin.get_new_content(uid, artist_name)
        
        # Filter & Process (Limit 50)
        items = sorted(items, key=lambda x: x.publish_time, reverse=True)[:50]
        
        db = SessionLocal()
        added_count = 0
        for item in items:
            if await process_media_item(item, db, notify=False): # Don't spam notifications for history
                 added_count += 1
        db.close()
        
        logger.info(f"Immediate sync finished for {artist_name}. Added {added_count} new songs.")
        
        # 3. Trigger Cache
        if added_count > 0:
            await auto_cache_recent_songs()
            
    except Exception as e:
        logger.error(f"Immediate sync failed: {e}")


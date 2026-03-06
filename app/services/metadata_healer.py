# -*- coding: utf-8 -*-
"""
MetadataHealer - 元数据治愈者

前身: EnrichmentService
功能升级:
1. 永久治愈: 对不完整的歌曲持续重试 (无冷却期限制)
2. 强力搜索: 支持文件名搜索降级
3. 统一写入: 接管所有元数据写入 (TagService)

更新日志:
- 2026-02-10: 移除元数据补全冷却期限制，网易云和QQ音乐接口无需冷却

Author: ali
Created: 2026-02-05
"""
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.services.smart_merger import SmartMerger, SongMetadata
from app.services.metadata_service import MetadataService
from app.services.tag_service import TagService

logger = logging.getLogger(__name__)

class MetadataHealer:
    """
    元数据治愈者
    负责扫描并修复资料库中元数据缺失的歌曲
    """
    
    def __init__(self):
        self.metadata_service = MetadataService()
        
        # 配置上传路径
        if os.path.exists("/config"):
            self.upload_root = "/config/uploads"
        else:
            self.upload_root = os.path.join(os.getcwd(), "uploads")
        self.cover_dir = os.path.join(self.upload_root, "covers")
        self.avatar_dir = os.path.join(self.upload_root, "avatars")
        os.makedirs(self.cover_dir, exist_ok=True)
        os.makedirs(self.avatar_dir, exist_ok=True)
        self.api_base_url = "https://music-api.gdstudio.xyz/api.php" # Fallback if proxy fails
        
    async def heal_all(self, force: bool = False, limit: int = 50):
        """
        全库治愈任务
        
        Args:
            force: 是否强制忽略冷却期 (手动触发时用 True)
            limit: 单次批处理上限
        """
        logger.info(f"🚑 开始元数据治愈任务 (Limit={limit}, Force={force})")
        
        async with AsyncSessionLocal() as db:
            # 查找所有本地歌曲
            # 这里的 "本地" 意味着有 local_path，状态可能是 DOWNLOADED
            stmt = select(Song).options(
                selectinload(Song.sources), 
                selectinload(Song.artist)
            ).where(Song.local_path.isnot(None)).limit(limit * 2) # 取多一点供筛选
            
            songs = (await db.execute(stmt)).scalars().all()
            
            # TaskMonitor Start
            from app.services.task_monitor import task_monitor, TaskCancelledException
            task_id = await task_monitor.start_task("heal", "正在初始化元数据治愈...")
            
            total_candidates = len(songs)
            logger.info(f"🚑 找到 {total_candidates} 首待检查歌曲")
            
            healed_count = 0
            processed_so_far = 0
            
            try:
                for song in songs:
                    if healed_count >= limit:
                        break
                    
                    # Check for Pause/Cancel
                    await task_monitor.check_status(task_id)

                    processed_so_far += 1
                    
                    # Update Progress
                    pct = int((processed_so_far / total_candidates) * 100)
                    await task_monitor.update_progress(
                        task_id,
                        pct,
                        f"正在检查: {song.title}",
                        details={"healed": healed_count, "total": total_candidates}
                    )
                    
                    # 🔧 关键修复: 先检查完整性，如果已完整则直接跳过
                    if self._is_complete(song):
                        continue

                    # 🔧 关键修复: 在补全之前，先尝试从文件标签同步歌词
                    if song.local_path and os.path.exists(song.local_path):
                        try:
                            file_tags = await TagService.read_tags(song.local_path)
                            file_lyrics = file_tags.get("lyrics") if file_tags else None
                            
                            if file_lyrics:
                                has_lyrics_in_db = any(self._parse_data_json(src.data_json).get("lyrics") for src in song.sources)
                                if not has_lyrics_in_db:
                                    logger.info(f"📥 发现文件标签歌词，同步到数据库: {song.title}")
                                    if not song.sources:
                                        from app.models.song import SongSource
                                        new_src = SongSource(song_id=song.id, source="local", data_json={"lyrics": file_lyrics})
                                        db.add(new_src)
                                    else:
                                        for src in song.sources:
                                            data = self._parse_data_json(src.data_json)
                                            data["lyrics"] = file_lyrics
                                            src.data_json = data
                                            from sqlalchemy.orm.attributes import flag_modified
                                            flag_modified(src, "data_json")
                                    
                                    await db.commit()
                                    # 同步完成后重新检查，如果变完整了就跳过后续 API 调用
                                    if self._is_complete(song):
                                        healed_count += 1
                                        continue
                        except Exception as e:
                            logger.warning(f"⚠️ 同步文件标签失败 [{song.title}]: {e}")
                        
                    # 2. 执行网络补全
                    try:
                        success = await self.heal_song(song.id, force=force)
                        if success:
                            healed_count += 1
                            # Update details on success
                            await task_monitor.update_progress(
                                task_id, pct, f"已修复: {song.title}", details={"healed": healed_count}
                            )
                    except Exception as e:
                        logger.error(f"❌ 治愈失败 [{song.title}]: {e}")
                
                msg = f"治愈完成, 成功修复 {healed_count} 首"
                logger.info(f"✅ {msg}")
                
                await task_monitor.finish_task(task_id, msg, details={"healed": healed_count, "processed": processed_so_far})
                return healed_count
            
            except TaskCancelledException as e:
                logger.warning(f"Heal task cancelled: {e}")
                await task_monitor.finish_task(task_id, f"治愈已取消 (已修复: {healed_count})", details={"healed": healed_count})
                return healed_count

            except Exception as e:
                logger.error(f"Heal task failed: {e}")
                await task_monitor.error_task(task_id, str(e))
                return healed_count

    async def heal_song(self, song_id: str, force: bool = False) -> bool:
        """
        治愈单首歌曲 (核心逻辑)
        """
        async with AsyncSessionLocal() as db:
            song = await db.get(Song, song_id, options=[selectinload(Song.artist), selectinload(Song.sources)])
            if not song: 
                logger.error(f"❌ 无法找到歌曲 ID: {song_id}")
                return False

            logger.info(f"🩹 正在治愈: {song.title} (ID: {song.id})")
            
            # 记录详细的处理信息
            processing_info = {
                'song_id': song_id,
                'title': song.title,
                'artist': song.artist.name if song.artist else "未知",
                'local_path': song.local_path,
                'current_state': {
                    'has_lyrics': any(self._parse_data_json(src.data_json).get("lyrics") for src in song.sources),
                    'has_cover': bool(song.cover and song.cover.startswith("/uploads/")),
                    'has_album': bool(song.album),
                    'has_publish_time': bool(song.publish_time)
                }
            }
            
            logger.info(f"📋 处理前状态: {processing_info}")

            # --- 阶段 1: 搜索元数据 ---
            # 策略 A: 标准搜索 (Title Artist)
            # 用户要求不要调用 gdstudio 返回的元数据，我们的 metadata_service 已经默认使用网易云/QQ
            try:
                best_meta = await self.metadata_service.get_best_match_metadata(song.title, song.artist.name if song.artist else "")
                
                if not best_meta.success:
                    # 记录失败详情
                    logger.warning(f"⚠️ 元数据搜索失败: {song.title}")
                    logger.debug(f"🔍 搜索详情 - 标题: '{song.title}', 艺人: '{song.artist.name if song.artist else ''}'")
                    logger.debug(f"📊 搜索结果 - 歌词: {bool(best_meta.lyrics)}, 封面: {bool(best_meta.cover_url)}, 专辑: {best_meta.album}")
                    
                    # 策略 B: 文件名降级搜索 (如果是自动导入的乱码歌曲)
                    if song.local_path:
                        filename_clean = self._clean_filename(song.local_path)
                        if filename_clean and filename_clean != song.title:
                            logger.info(f"🔄 标准搜索失败, 尝试文件名降级搜索: '{filename_clean}'")
                            best_meta = await self.metadata_service.get_best_match_metadata(filename_clean, "")
                            
                            if not best_meta.success:
                                logger.warning(f"❌ 文件名搜索也失败: {filename_clean}")
                                logger.debug(f"📊 文件名搜索结果 - 歌词: {bool(best_meta.lyrics)}, 封面: {bool(best_meta.cover_url)}, 专辑: {best_meta.album}")
                
                if not best_meta.success:
                    logger.error(f"❌ 无法找到元数据: {song.title}")
                    # 更新重试时间
                    song.last_enrich_at = datetime.now()
                    await db.commit()
                    return False
                    
            except Exception as search_error:
                logger.error(f"💥 元数据搜索过程中发生异常: {song.title} - {str(search_error)}")
                logger.exception(search_error)  # 记录完整堆栈
                song.last_enrich_at = datetime.now()
                await db.commit()
                return False

            # --- 阶段 2: 智能合并 ---
            current_lyrics = None
            for src in song.sources:
                data = self._parse_data_json(src.data_json)
                if data.get("lyrics"):
                    current_lyrics = data["lyrics"]
                    break

            current = SongMetadata(
                title=song.title,
                artist=song.artist.name if song.artist else "",
                album=song.album,
                cover_url=song.cover,
                lyrics=current_lyrics, 
                publish_time=song.publish_time
            )
            
            new_meta = SongMetadata(
                title=best_meta.search_result.title if best_meta.search_result else song.title,
                artist=best_meta.search_result.artist if best_meta.search_result else "",
                album=best_meta.album,
                cover_url=best_meta.cover_url,
                lyrics=best_meta.lyrics,
                publish_time=self._parse_date(best_meta.publish_time)
            )

            # 相似度分级校验 (防止误关联)
            similarity = SmartMerger.check_similarity(song.title, new_meta.title)
            if similarity < 0.6:
                logger.warning(f"⚠️ 相似度过低 ({similarity:.2f}), 跳过自动治愈: '{song.title}' vs '{new_meta.title}'")
                song.last_enrich_at = datetime.now()
                await db.commit()
                return False

            updates = SmartMerger.merge(current, new_meta)
            
            if not updates and not force:
                logger.info("⏩ 元数据未发生显著变化，跳过")
                song.last_enrich_at = datetime.now()
                await db.commit()
                return True # 虽然没更，但也算处理完

            # --- 阶段 3: 执行更新 ---
            
            # 3.1 下载封面
            cover_data = None
            
            # 确定是否需要下载/处理封面
            # 逻辑：
            # 1. updates 里有新封面 (SmartMerger 决定更新)
            # 2. 当前封面是在线链接 (http开头) -> 始终本地化，以满足“全部物理嵌入”要求
            need_download_cover = "cover" in updates
            if not need_download_cover and song.cover and (song.cover.startswith("http") or song.cover.startswith("/api/discovery/cover")):
                need_download_cover = True
                # 这里不需要强制加入 updates["cover"]，下面逻辑会直接拿 song.cover
            
            if need_download_cover:
                cover_url = updates.get("cover") or song.cover
                # 处理代理 URL: /api/discovery/cover?source=xxx&id=yyy
                if cover_url.startswith("/api/discovery/cover"):
                    import urllib.parse as urlparse
                    parsed = urlparse.urlparse(cover_url)
                    qs = urlparse.parse_qs(parsed.query)
                    source = qs.get("source", [""])[0]
                    target_id = qs.get("id", [""])[0]
                    if source and target_id:
                        # 还原为 GDStudio 的真实 pic 链接 (实际上 pic 会返回 json，所以我们直接用那个 pic 接口)
                        cover_url = f"{self.api_base_url}?types=pic&source={source}&id={target_id}"

                web_url, local_path = await self._download_cover(cover_url)
                if web_url:
                     song.cover = web_url # 这一步很关键，将在线链接改为本地 /uploads 链接
                     # 读取 bytes 用于写 tag
                     if local_path and os.path.exists(local_path):
                         with open(local_path, "rb") as f:
                             cover_data = f.read()
            elif song.cover and song.cover.startswith("/uploads/"):
                 # 已经是本地封面，读取出来
                 # 修复 Windows 下的路径拼接逻辑
                 rel_path = song.cover.replace("/", os.sep).lstrip(os.sep)
                 # 如果 cover 是 /uploads/covers/xxx.jpg，rel_path 变成 uploads\covers\xxx.jpg
                 # 而 self.upload_root 可能是 D:\code\music-monitor\uploads
                 # 所以要小心拼接。 song.cover 包含 'uploads' 吗？
                 # 查看 _download_cover: web_url = f"/uploads/covers/{filename}"
                 # 所以 rel_path 包含 uploads/covers/...
                 # 我们需要的是相对于 cwd 的路径。
                 local_path = os.path.join(os.getcwd(), rel_path)
                 if os.path.exists(local_path):
                     with open(local_path, "rb") as f:
                         cover_data = f.read()

            # 3.2 更新 DB 字段
            if "title" in updates: song.title = updates["title"]
            if "album" in updates: song.album = updates["album"]
            if "publish_time" in updates: song.publish_time = updates["publish_time"]
            
            # 3.3 写入文件 (TagService)
            # 准备写入的数据
            # 确保即使这次没获取到歌词，也要尝试从数据库现有记录里拿，防止被空值覆盖
            final_lyrics = updates.get("lyrics") or new_meta.lyrics or current_lyrics
            
            tag_meta = {
                "title": song.title,
                "artist": song.artist.name if song.artist else "",
                "album": song.album,
                "date": song.publish_time,
                "lyrics": final_lyrics,
                "cover_data": cover_data
            }
            
            # 清理 None 值
            tag_meta = {k: v for k, v in tag_meta.items() if v is not None}

            if song.local_path and os.path.exists(song.local_path):
                success = await TagService.write_tags(song.local_path, tag_meta)
                if success:
                    logger.info(f"💾 文件标签回写成功: {song.local_path}")
            
            # 3.4 更新 Source 数据 (lyrics 和 cover 存这里)
            # 🔧 修复: 如果没有 source 记录，创建一个 local source
            if not song.sources:
                from app.models.song import SongSource
                logger.info(f"⚠️ 歌曲没有 source 记录，创建 local source: {song.title}")
                new_source = SongSource(
                    song_id=song.id,
                    source="local",
                    source_id=song.local_path or str(song.id),
                    data_json={"lyrics": final_lyrics} if final_lyrics else {}
                )
                db.add(new_source)
                # 立即刷新以获取新创建的 source
                await db.flush()
                song.sources.append(new_source)
            
            for src in song.sources:
                data = self._parse_data_json(src.data_json)
                changed = False
                
                # 同步歌词 - 确保歌词一定写入 data_json (修复持久化问题)
                # 不论 SmartMerger 是否决定"更新"，只要有歌词就写入
                if final_lyrics and not data.get("lyrics"):
                    data["lyrics"] = final_lyrics
                    changed = True
                elif updates.get("lyrics"):  # SmartMerger 决定升级歌词 (如 纯文本->LRC)
                    data["lyrics"] = updates["lyrics"]
                    changed = True
                
                # 同步专辑
                if "album" in updates:
                    data["album"] = updates["album"]
                    changed = True
                
                # 同步封面 (如果已本地化，强制所有来源同步)
                if song.cover and song.cover.startswith("/uploads/"):
                    if src.cover != song.cover:
                        src.cover = song.cover
                        changed = True
                    
                    # 确保 data_json 里的封面也更新
                    if isinstance(data, dict):
                        if data.get("cover") != song.cover:
                            data["cover"] = song.cover
                            changed = True
                
                if changed:
                    src.data_json = data
                    # 🔧 关键修复: SQLAlchemy 不会自动追踪 JSON 字段的内部修改
                    # 必须显式标记字段已变更，否则 commit 时不会持久化
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(src, "data_json")
                    logger.info(f"📝 已更新 source[{src.source}].data_json: lyrics={bool(data.get('lyrics'))}")
            
            # 调试: 确认最终状态
            final_check = False
            for src in song.sources:
                d = self._parse_data_json(src.data_json)
                if d.get("lyrics"):
                    final_check = True
                    break
            logger.info(f"🔍 持久化检查: {song.title} 歌词已保存={final_check}, sources数量={len(song.sources)}")
            
            await db.commit()
            return True

    async def heal_artist(self, db, artist) -> bool:
        """治愈歌手头像 (本地化)"""
        if not artist.avatar or not artist.avatar.startswith("http"):
            return False
            
        logger.info(f"🎨 正在本地化歌手头像: {artist.name}")
        web_url, local_path = await self._download_image(artist.avatar, "avatars")
        
        if web_url:
            artist.avatar = web_url
            # 同步到所有 source
            for src in artist.sources:
                src.avatar = web_url
            
            await db.commit()
            logger.info(f"✅ 歌手头像本地化成功: {artist.name} -> {web_url}")
            return True
        return False

    def _is_complete(self, song: Song) -> bool:
        """
        检查歌曲元数据是否完整 (严格模式: 6 字段全覆盖)
        
        必须同时满足:
        1. title - 歌名非空
        2. artist - 歌手非空
        3. album - 专辑名非空
        4. cover - 封面已本地化 (/uploads/ 开头)
        5. publish_time - 发布日期非空
        6. lyrics - 歌词非空 (存储在 SongSource.data_json)
        """
        # 1. 核心字段 (Song 模型)
        has_title = bool(song.title and song.title.strip())
        has_artist = bool(song.artist and song.artist.name)
        has_album = bool(song.album and song.album.strip())
        has_cover = bool(song.cover and song.cover.startswith("/uploads/"))  # 必须是本地化封面
        has_publish_time = bool(song.publish_time)
        
        # 2. 歌词 (在 SongSource.data_json 里)
        has_lyrics = False
        for src in song.sources:
            data = self._parse_data_json(src.data_json)
            if data.get("lyrics"):
                has_lyrics = True
                break
        
        # 调试日志: 显示哪些字段缺失
        is_complete = all([has_title, has_artist, has_album, has_cover, has_publish_time, has_lyrics])
        if not is_complete:
            missing = []
            if not has_title: missing.append("title")
            if not has_artist: missing.append("artist")
            if not has_album: missing.append("album")
            if not has_cover: missing.append(f"cover({song.cover})")
            if not has_publish_time: missing.append("publish_time")
            if not has_lyrics: missing.append("lyrics")
            logger.info(f"❌ 歌曲不完整 [{song.title}]: 缺少 {', '.join(missing)}")
        
        return is_complete

    def _should_skip_enrichment(self, song: Song) -> bool:
        """
        检查是否应该跳过元数据补全
        元数据获取使用网易云和QQ音乐接口，无需冷却期限制
        """
        # 元数据补全操作资源消耗很小，可随时执行
        return False

    def _clean_filename(self, path: str) -> Optional[str]:
        """清洗文件名用于搜索"""
        if not path: return None
        base = os.path.basename(path)
        name_no_ext = os.path.splitext(base)[0]
        
        # 移除常见的分隔符和数字
        # e.g. "01. Song Name" -> "Song Name"
        # "Song_Name_HQ" -> "Song Name"
        
        cleaned = re.sub(r'^\d+[\.\s\-]+', '', name_no_ext) # 去头数字
        cleaned = cleaned.replace("_", " ")
        cleaned = re.sub(r'\s*\(.*?\)', '', cleaned) # 去括号内容 (HQ) 等
        return cleaned.strip()

    def _parse_data_json(self, data_json) -> Dict:
        if isinstance(data_json, dict): return data_json
        return {}

    def _parse_date(self, val):
        """解析日期 (支持多种格式)"""
        if not val: return None
        if isinstance(val, datetime): return val
        
        if isinstance(val, str):
            val = val.strip()
            try:
                # 2023-01-01
                if "-" in val and len(val) >= 10:
                     return datetime.strptime(val[:10], "%Y-%m-%d")
                # 2023
                if len(val) == 4 and val.isdigit():
                     return datetime.strptime(val, "%Y")
                # 1672531200000 (Timestamp)
                if val.isdigit() and len(val) > 8:
                     ts = int(val)
                     if len(val) > 10: ts = ts / 1000
                     return datetime.fromtimestamp(ts)
            except:
                pass
        return None

    async def _download_cover(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """下载封面 (兼容旧调用)"""
        return await self._download_image(url, "covers")

    async def _download_image(self, url: str, folder: str = "covers") -> Tuple[Optional[str], Optional[str]]:
        """下载图片并保存到指定目录"""
        try:
            import hashlib
            import aiohttp
            ext = "png" if ".png" in url.lower() else "jpg"
            md5 = hashlib.md5(url.encode()).hexdigest()
            filename = f"{md5}.{ext}"
            
            target_dir = os.path.join(self.upload_root, folder)
            os.makedirs(target_dir, exist_ok=True)
            
            save_path = os.path.join(target_dir, filename)
            web_url = f"/uploads/{folder}/{filename}"
            
            if os.path.exists(save_path):
                return web_url, save_path
                
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        
                        # 特殊处理: GDStudio 的 pic 链接可能返回 JSON {"url": "..."}
                        if b'{"url":' in content[:100]:
                            import json
                            try:
                                data = json.loads(content.decode("utf-8"))
                                img_real_url = data.get("url")
                                if img_real_url:
                                    return await self._download_image(img_real_url, folder)
                            except:
                                pass
                        
                        with open(save_path, "wb") as f:
                            f.write(content)
                        return web_url, save_path
            return None, None
        except Exception as e:
            logger.warning(f"下载图片失败 ({url}): {e}")
            return None, None

    async def _download_cover_legacy(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            import hashlib
            import aiohttp
            ext = "png" if ".png" in url.lower() else "jpg"
            md5 = hashlib.md5(url.encode()).hexdigest()
            filename = f"{md5}.{ext}"
            save_path = os.path.join(self.cover_dir, filename)
            web_url = f"/uploads/covers/{filename}"
            
            if os.path.exists(save_path):
                return web_url, save_path
                
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        
                        # 特殊处理: GDStudio 的 pic 链接可能返回 JSON {"url": "..."}
                        # 我们的 _download_cover 如果收到的是这种 JSON，需要解析后再下载图片
                        if b'{"url":' in content[:100]:
                            import json
                            try:
                                data = json.loads(content.decode("utf-8"))
                                img_real_url = data.get("url")
                                if img_real_url:
                                    # 重新请求图片
                                    return await self._download_cover(img_real_url)
                            except:
                                pass

                        with open(save_path, "wb") as f:
                            f.write(content)
                        return web_url, save_path
            return None, None
        except Exception as e:
            logger.warning(f"封面下载失败: {e}")
            return None, None

# -*- coding: utf-8 -*-
"""
ArtistRefreshService - 歌手刷新服务

功能：
- 从在线源（QQ音乐、网易云）同步歌手歌曲列表
- 智能合并在线和本地歌曲
- 元数据治愈（修复占位符日期、缺失封面）
- 孤儿歌曲挽救（关联本地文件到在线源）

Author: google
Created: 2026-02-02 (从 LibraryService 拆分)
"""
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collections import defaultdict
from datetime import datetime
import logging
import re
import json

from app.models.artist import Artist, ArtistSource
from app.models.song import Song, SongSource
from app.repositories.artist import ArtistRepository
from app.repositories.song import SongRepository
from app.services.music_providers.aggregator import MusicAggregator
from app.services.scan_service import ScanService
from app.services.enrichment_service import EnrichmentService
from app.utils.error_handler import handle_service_errors

logger = logging.getLogger(__name__)


class ArtistRefreshService:
    """歌手刷新服务 - 负责从在线源同步歌曲列表"""
    
    def __init__(self):
        self.aggregator = MusicAggregator()
        self.scan_service = ScanService()
        self.enrichment_service = EnrichmentService()
        self._refresh_enrich_count = 0
        self._refresh_heal_count = 0
    
    @handle_service_errors(fallback_value=0)
    async def refresh(self, db: AsyncSession, artist_name: str) -> int:
        """
        全量刷新一名歌手的歌曲资料。
        
        该方法是本服务的入口点，执行以下流程：
        1. 从所有配置的音乐平台（网易云、QQ音乐）获取歌手的全量歌曲列表。
        2. 与本地数据库中的现有记录进行合并（基于标题的智能去重）。
        3. 进行“反向查找”，尝试从在线平台补全本地库中已有的原版歌曲。
        4. 挽救“孤儿歌曲”，即数据库中已存在但在线平台不再返回的旧作品。
        5. 对所有记录进行元数据“治愈”（Health Check & Repair）。
        
        Args:
            db (AsyncSession): 异步数据库会话。
            artist_name (str): 歌手的完整准确名称。
            
        Returns:
            int: 本次刷新新增进库的歌曲数量。
        """
        logger.info(f"Refreshing artist: {artist_name}")
        
        # 1. 获取歌手信息
        artist_repo = ArtistRepository(db)
        artist = await artist_repo.get_by_name(artist_name)
        if not artist:
            logger.warning(f"Artist {artist_name} not found in DB")
            return 0
        
        # 2. 预扫描本地文件
        logger.info(f"📁 [Pre-refresh] Scanning local files for {artist_name}...")
        await self.scan_service.scan_local_files(db)
        
        # 3. 广播开始状态
        from core.websocket import manager
        await manager.broadcast({
            "type": "artist_progress",
            "artistId": str(artist.id),
            "artistName": artist.name,
            "state": "scanning",
            "progress": 10,
            "message": "📥 正在拉取全网歌曲...",
            "songCount": await artist_repo.get_song_count(artist.id)
        })
        
        # 4. 获取在线歌曲
        raw_songs = await self._fetch_online_songs(db, artist, manager)
        if not raw_songs:
            return 0
        
        # 5. 反向查找缺失的原版歌曲
        raw_songs = await self._reverse_lookup_originals(
            raw_songs, artist, manager
        )
        
        # 6. 合并在线和本地歌曲
        new_count = await self._merge_with_local(
            db, artist, raw_songs, manager
        )
        
        # 7. 挽救孤儿歌曲
        await self._rescue_orphan_songs(db, artist, raw_songs, manager)
        
        # 8. 全库元数据治愈
        await self._heal_all_metadata(db, artist)
        
        # 9. 完成统计
        total_count = await artist_repo.get_song_count(artist.id)
        logger.info(
            f"Artist {artist_name} refresh complete. "
            f"Added {new_count} new songs. Total {total_count}."
        )
        
        # 10. 广播完成状态
        await manager.broadcast({
            "type": "artist_progress",
            "artistId": str(artist.id),
            "artistName": artist.name,
            "state": "complete",
            "progress": 100,
            "message": f"✅ 刷新完成 (新增 {new_count} 首, 总计 {total_count} 首)",
            "songCount": total_count
        })
        
        # 触发前端刷新
        await manager.broadcast({
            "type": "refresh_list",
            "artistId": str(artist.id),
            "artistName": artist.name
        })
        
        return new_count
    
    @handle_service_errors(fallback_value=[])
    async def _fetch_online_songs(
        self, 
        db: AsyncSession, 
        artist: Artist,
        manager
    ) -> List:
        """获取在线歌曲列表"""
        # 加载歌手源
        stmt = select(ArtistSource).where(ArtistSource.artist_id == artist.id)
        sources = (await db.execute(stmt)).scalars().all()
        artist_ids = {s.source: s.source_id for s in sources}
        
        if not artist_ids:
            logger.info("No source IDs found for artist")
            return []
        
        raw_songs = []
        
        # QQ音乐
        if 'qqmusic' in artist_ids:
            await manager.broadcast({
                "type": "artist_progress",
                "artistId": str(artist.id),
                "artistName": artist.name,
                "state": "fetching_qq",
                "progress": 20,
                "message": "📥 正在拉取 QQ 音乐歌曲列表..."
            })
            qq_songs = await self.aggregator.providers[1].get_artist_songs(
                artist_ids['qqmusic'], limit=1000
            )
            raw_songs.extend(qq_songs)
            logger.info(f"Fetched {len(qq_songs)} songs from QQ Music")
        
        # 网易云
        if 'netease' in artist_ids:
            await manager.broadcast({
                "type": "artist_progress",
                "artistId": str(artist.id),
                "artistName": artist.name,
                "state": "fetching_netease",
                "progress": 30,
                "message": "📥 正在拉取网易云音乐歌曲列表..."
            })
            netease_songs = await self.aggregator.providers[0].get_artist_songs(
                artist_ids['netease'], limit=1000
            )
            raw_songs.extend(netease_songs)
            logger.info(f"Fetched {len(netease_songs)} songs from Netease")
        
        # 过滤脏数据
        raw_songs = [s for s in raw_songs if self.aggregator._is_valid_song(s)]
        
        # 补全歌手头像
        if not artist.avatar:
            for rs in raw_songs:
                if rs.cover:
                    artist.avatar = rs.cover
                    logger.info(f"🎨 已从采集列表自动补全艺人头像: {artist.name}")
                    await db.commit()
                    break
        
        await manager.broadcast({
            "type": "artist_progress",
            "artistId": str(artist.id),
            "artistName": artist.name,
            "state": "matching",
            "progress": 40,
            "message": f"获取到 {len(raw_songs)} 首歌曲，正在聚合..."
        })
        
        return raw_songs
    
    @handle_service_errors(fallback_value=[])
    async def _reverse_lookup_originals(
        self,
        raw_songs: List,
        artist: Artist,
        manager
    ) -> List:
        """反向查找缺失的原版歌曲（针对伴奏）"""
        existing_titles_norm = {
            ScanService._normalize_cn_brackets(s.title).lower().strip() 
            for s in raw_songs
        }
        
        extra_songs = []
        checked_inst_titles = set()
        inst_keywords = ['(伴奏)', '(inst)', 'instrumental', '伴奏', 'inst.']
        
        for s in raw_songs:
            title_lower = s.title.lower()
            is_inst = False
            clean_title = s.title
            
            # 检测伴奏
            for kw in inst_keywords:
                if kw in title_lower:
                    is_inst = True
                    clean_title = s.title.lower().replace(kw, '').strip()
                    clean_title = clean_title.replace('()', '').replace('（）', '').strip()
                    break
            
            if is_inst:
                norm_clean = ScanService._normalize_cn_brackets(clean_title).lower().strip()
                
                if norm_clean not in existing_titles_norm and norm_clean not in checked_inst_titles:
                    checked_inst_titles.add(norm_clean)
                    logger.info(f"🔍 发现孤立伴奏 '{s.title}', 尝试反查原版: '{clean_title}'")
                    
                    await manager.broadcast({
                        "type": "artist_progress",
                        "artistId": str(artist.id),
                        "artistName": artist.name,
                        "state": "matching",
                        "progress": 40,
                        "message": f"正在补全原版: {clean_title}..."
                    })
                    
                    try:
                        query = f"{clean_title} {artist.name}"
                        search_res = await self.aggregator.providers[0].search_song(query, limit=3)
                        
                        found_target = None
                        for cand in search_res:
                            cand_norm = ScanService._normalize_cn_brackets(cand.title).lower().strip()
                            if cand_norm == norm_clean:
                                found_target = cand
                                break
                        
                        if found_target:
                            logger.info(f"  ✅ 成功找回原版: {found_target.title}")
                            extra_songs.append(found_target)
                            existing_titles_norm.add(norm_clean)
                    except Exception as e:
                        logger.warning(f"  ❌ 反查失败: {e}")
        
        if extra_songs:
            raw_songs.extend(extra_songs)
            logger.info(f"✨ 反向补全了 {len(extra_songs)} 首缺失的原版歌曲")
        
        return raw_songs
    
    async def _merge_with_local(
        self,
        db: AsyncSession,
        artist: Artist,
        raw_songs: List,
        manager
    ) -> int:
        """合并在线和本地歌曲"""
        await manager.broadcast({
            "type": "artist_progress",
            "artistId": str(artist.id),
            "artistName": artist.name,
            "state": "matching",
            "progress": 50,
            "message": "🔍 正在与本地库匹配..."
        })
        
        # 按标题分组
        grouped_songs = defaultdict(list)
        for s in raw_songs:
            clean_title = ScanService._normalize_cn_brackets(s.title).lower().strip()
            grouped_songs[clean_title].append(s)
        
        # 排序（按发布时间倒序）
        def get_group_date(group):
            dates = [
                str(getattr(s, 'publish_time', '0000-00-00')) 
                for s in group if getattr(s, 'publish_time', None)
            ]
            return max(dates) if dates else '0000-00-00'
        
        sorted_groups = sorted(
            grouped_songs.items(), 
            key=lambda x: get_group_date(x[1]), 
            reverse=True
        )
        
        # 获取现有歌曲及其所有的源（通过 selectinload 预加载，避免 N+1 问题）
        res = await db.execute(
            select(Song)
            .options(selectinload(Song.sources))
            .where(Song.artist_id == artist.id)
        )
        all_db_songs = res.scalars().all()
        
        db_song_map = {
            ScanService._normalize_cn_brackets(s.title).lower().strip(): s 
            for s in all_db_songs
        }
        logger.info(f"  🔍 已缓存 {len(all_db_songs)} 首现有歌曲（带源信息）用于模糊匹配")
        
        new_count = 0
        processed = 0
        total_groups = len(sorted_groups)
        
        for title_key, group in sorted_groups:
            processed += 1
            
            # 选择最佳元数据（优先QQ音乐）
            best_meta = group[0]
            qq_ver = next((x for x in group if x.source == 'qqmusic'), None)
            if qq_ver:
                best_meta = qq_ver
            
            # 噪声过滤
            noise_keywords = ["#", "巡演", "最后一站", "预告"]
            if (any(k in best_meta.title for k in noise_keywords) and 
                not best_meta.album and len(best_meta.title) > 30):
                logger.info(f"🧹 过滤噪声动态: {best_meta.title}")
                continue
            
            # 查找或创建歌曲
            norm_key = ScanService._normalize_cn_brackets(best_meta.title).lower().strip()
            existing_song = db_song_map.get(norm_key)
            
            if not existing_song:
                existing_song = Song(
                    artist_id=artist.id,
                    title=best_meta.title,
                    album=best_meta.album,
                    created_at=datetime.now(),
                    status="PENDING"
                )
                db.add(existing_song)
                await db.flush()
                new_count += 1
                db_song_map[norm_key] = existing_song
            
            # 智能合并元数据
            await self._smart_merge_metadata(
                db, existing_song, group, db_song_map, norm_key
            )
            
            # 获取此歌曲的所有源
            existing_sources = getattr(existing_song, 'sources', [])
            if not existing_sources:
                # 如果没有加载关系，则手动查一下（或确保之前 prefetch 了）
                # 这里为了简单，先用 map
                pass
            
            src_map = {(src.source, str(src.source_id)) for src in existing_sources}
            
            # 更新源
            for s in group:
                s_id_str = str(s.id)
                if (s.source, s_id_str) not in src_map:
                    src_ent = SongSource(
                        song_id=existing_song.id,
                        source=s.source,
                        source_id=s_id_str,
                        cover=s.cover_url or getattr(s, 'pic_url', None),
                        duration=s.duration,
                        url=getattr(s, 'url', None),
                        data_json={'quality': getattr(s, 'quality', 'unknown')}
                    )
                    db.add(src_ent)
                    src_map.add((s.source, s_id_str)) # 避免同一批次重复添加
            
            # 进度广播
            if processed % 20 == 0 or processed == total_groups:
                await manager.broadcast({
                    "type": "artist_progress",
                    "artistId": str(artist.id),
                    "artistName": artist.name,
                    "state": "matching",
                    "progress": int(40 + (processed / total_groups) * 35),
                    "message": f"⏳ 匹配进度 ({processed}/{total_groups})"
                })
        
        await db.commit()
        return new_count
    
    async def _smart_merge_metadata(
        self,
        db: AsyncSession,
        existing_song: Song,
        group: List,
        db_song_map: Dict,
        norm_key: str
    ):
        """智能合并元数据"""
        candidate_covers = []
        candidate_dates = []
        candidate_albums = []
        
        for s in group:
            c_url = getattr(s, 'cover_url', None) or getattr(s, 'pic_url', None)
            if c_url:
                candidate_covers.append(c_url)
            
            p_raw = getattr(s, 'publish_time', None)
            if p_raw:
                p_parsed = self.enrichment_service._parse_date(str(p_raw))
                if p_parsed:
                    candidate_dates.append(p_parsed.strftime("%Y-%m-%d"))
            
            alb = getattr(s, 'album', None)
            if alb:
                candidate_albums.append(alb)
        
        # 判断是否需要治愈
        needs_healing = False
        if not existing_song.cover or 'gtimg.cn' in str(existing_song.cover):
            needs_healing = True
        if (not existing_song.publish_time or 
            existing_song.publish_time.year >= 2026 or 
            existing_song.publish_time.year <= 1970):
            needs_healing = True
        if not existing_song.album:
            needs_healing = True
        
        # 全网补全
        if needs_healing and (not candidate_covers or not candidate_dates):
            if self._refresh_enrich_count < 15:
                logger.info(f"  🔍 正在为 [旧曲] 尝试全网补全元数据: {existing_song.title}")
                try:
                    enriched = await self.aggregator.get_song_metadata_from_best_source(
                        existing_song.title, 
                        existing_song.artist.name
                    )
                    if enriched:
                        if enriched.get('cover_url'):
                            candidate_covers.insert(0, enriched['cover_url'])
                        if enriched.get('publish_time'):
                            p_enrich = self.enrichment_service._parse_date(
                                str(enriched['publish_time'])
                            )
                            if p_enrich:
                                candidate_dates.insert(0, p_enrich.strftime("%Y-%m-%d"))
                        if enriched.get('album') and not candidate_albums:
                            candidate_albums.append(enriched['album'])
                        self._refresh_enrich_count += 1
                except Exception as e:
                    logger.warning(f"Metadata healing failed: {e}")
        
        # 应用更新
        if candidate_covers:
            if not existing_song.cover or 'gtimg.cn' in str(existing_song.cover):
                existing_song.cover = candidate_covers[0]
        
        if candidate_albums and not existing_song.album:
            existing_song.album = candidate_albums[0]
        
        # 更新日期
        new_date = None
        if candidate_dates:
            new_date = self.enrichment_service._parse_date(candidate_dates[0])
        
        # 伴奏版本回退策略
        if not new_date and "_inst" in norm_key:
            orig_key = norm_key.replace("_inst", "")
            if orig_key in db_song_map:
                orig_song = db_song_map[orig_key]
                if orig_song.publish_time and 1970 < orig_song.publish_time.year < 2026:
                    new_date = orig_song.publish_time
                    logger.info(
                        f"    🎹 伴奏日期回退: {existing_song.title} -> "
                        f"继承原版 ({new_date.strftime('%Y-%m-%d')})"
                    )
        
        if new_date:
            curr_date = existing_song.publish_time
            if not curr_date or curr_date.year >= 2026 or curr_date.year <= 1970:
                existing_song.publish_time = new_date
                logger.info(
                    f"    📅 日期修正: {existing_song.title} -> "
                    f"{new_date.strftime('%Y-%m-%d')}"
                )
            elif abs((curr_date - new_date).days) > 1:
                existing_song.publish_time = new_date
    
    @handle_service_errors(raise_on_critical=False)
    async def _rescue_orphan_songs(
        self,
        db: AsyncSession,
        artist: Artist,
        raw_songs: List,
        manager
    ):
        """挽救孤儿歌曲（本地文件关联到在线源）"""
        try:
            stmt = select(Song).options(selectinload(Song.sources)).where(
                Song.artist_id == artist.id,
                Song.local_path != None
            )
            local_songs = (await db.execute(stmt)).scalars().all()
            
            logger.info(f"🚑 [挽救模式] 开始检查 {len(local_songs)} 首本地歌曲...")
            
            await manager.broadcast({
                "type": "artist_progress",
                "artistId": str(artist.id),
                "artistName": artist.name,
                "state": "rescue",
                "progress": 80,
                "message": f"正在检查 {len(local_songs)} 首本地孤儿歌曲..."
            })
            
            rescue_count = 0
            
            for song in local_songs:
                # 检查是否已有在线源
                has_online = any(s.source in ['qqmusic', 'netease'] for s in song.sources)
                if has_online and song.publish_time:
                    continue
                
                logger.info(f"  👉 正在尝试挽救: {song.title}")
                
                # 尝试从内嵌标签获取标题
                if song.local_path:
                    try:
                        from tinytag import TinyTag
                        import os
                        if os.path.exists(song.local_path):
                            tag = TinyTag.get(song.local_path)
                            if tag and tag.title:
                                t_clean = ScanService._normalize_cn_brackets(
                                    tag.title
                                ).lower().strip()
                                match_title = ScanService._normalize_cn_brackets(
                                    song.title
                                ).lower().strip()
                                if t_clean and t_clean != match_title:
                                    logger.info(f"    🏷️ 使用内嵌标签标题: {tag.title}")
                                    song.title = tag.title
                    except:
                        pass
                
                # 查找匹配
                best_match = self._find_match(raw_songs, song)
                
                if not best_match:
                    search_key = f"{song.title} {artist.name}"
                    search_results = await self.aggregator.search_song(search_key, limit=5)
                    best_match = self._find_match(search_results, song)
                
                # 尝试去括号搜索
                if not best_match:
                    clean_title = re.sub(r"[\(\[【（].*?[\)\]】）]", "", song.title).strip()
                    if clean_title and clean_title != song.title:
                        logger.info(f"    ⚠️ 未命中，尝试去括号搜索: '{clean_title}'")
                        clean_key = f"{clean_title} {artist.name}"
                        relaxed_results = await self.aggregator.search_song(clean_key, limit=5)
                        best_match = self._find_match(relaxed_results, song)
                
                if best_match:
                    # 检查源是否已存在
                    chk = select(SongSource).where(
                        SongSource.song_id == song.id,
                        SongSource.source == best_match.source,
                        SongSource.source_id == str(best_match.id)
                    )
                    existing_src = (await db.execute(chk)).scalars().first()
                    
                    if not existing_src:
                        new_source = SongSource(
                            song_id=song.id,
                            source=best_match.source,
                            source_id=best_match.id,
                            cover=best_match.cover_url,
                            duration=best_match.duration,
                            url="",
                            data_json=json.dumps(best_match.__dict__, default=str)
                        )
                        db.add(new_source)
                        logger.info(f"    🔗 关联成功! 源: {best_match.source}")
                    
                    # 补全元数据
                    if not song.cover and best_match.cover_url:
                        song.cover = best_match.cover_url
                        logger.info(f"    🖼️ 补全封面")
                    
                    if not song.album and best_match.album:
                        song.album = best_match.album
                        logger.info(f"    💽 补全专辑: {song.album}")
                    
                    if not song.publish_time and best_match.publish_time:
                        try:
                            pt_str = str(best_match.publish_time).strip()
                            from datetime import datetime as dt
                            if pt_str.replace('-', '').isdigit() and len(pt_str) >= 10:
                                ts = int(pt_str)
                                if len(pt_str) == 13:
                                    ts = ts / 1000
                                if ts > 0:
                                    song.publish_time = dt.fromtimestamp(ts)
                            elif len(pt_str) == 4 and pt_str.isdigit():
                                song.publish_time = dt.strptime(pt_str, "%Y")
                            elif len(pt_str) >= 10:
                                dt_obj = dt.strptime(pt_str[:10], "%Y-%m-%d")
                                if dt_obj.year > 1970:
                                    song.publish_time = dt_obj
                            if song.publish_time:
                                logger.info(f"    📅 补全日期: {song.publish_time}")
                        except Exception as e:
                            logger.warning(f"Date parse failed: {e}")
                    
                    rescue_count += 1
            
            if rescue_count > 0:
                await db.commit()
                logger.info(f"✨ 挽救行动结束: 成功修复 {rescue_count} 首歌曲")
        
        except Exception as e:
            logger.error(f"❌ 挽救模式发生意外错误: {e}", exc_info=True)
    
    def _find_match(self, candidates: List, local_song: Song):
        """查找匹配的歌曲"""
        norm_local = ScanService._normalize_cn_brackets(local_song.title).lower().strip()
        
        variant_keywords = [
            "(伴奏)", " 伴奏", "inst.", "instrumental", 
            "demo", "(live)", " live", "（伴奏）"
        ]
        is_local_variant = any(k in local_song.title.lower() for k in variant_keywords)
        
        for res in candidates:
            norm_res = ScanService._normalize_cn_brackets(res.title).lower().strip()
            is_remote_variant = any(k in res.title.lower() for k in variant_keywords)
            
            # 精确匹配
            if norm_local == norm_res:
                logger.info(f"      -> ✅ 精确匹配成功: '{res.title}'")
                return res
            
            # 模糊匹配（Remote在Local中）
            if norm_res in norm_local:
                if is_local_variant and not is_remote_variant:
                    logger.info(
                        f"      ⛔ 拒绝模糊匹配: 本地是变体但远程是原版"
                    )
                    continue
                logger.info(f"      -> ⚠️ 模糊匹配成功(Remote在Local中)")
                return res
            
            # 反向模糊匹配（Local在Remote中）
            if len(norm_local) > 1 and norm_local in norm_res:
                if not is_local_variant and is_remote_variant:
                    logger.info(f"      ⚠️ 允许反向模糊匹配(可能是Live版)")
                    return res
                logger.info(f"      -> ⚠️ 模糊匹配成功(Local在Remote中)")
                return res
        
        return None
    
    @handle_service_errors(raise_on_critical=False)
    async def _heal_all_metadata(self, db: AsyncSession, artist: Artist):
        """
        对歌手的所有歌曲执行元数据并行治愈。
        
        通过并发（受限）请求各个平台，尝试自动修复以下问题：
        - 缺失的高清封面图。
        - 缺失或格式不规范的专辑名称。
        - 缺失或明显的占位符发布日期（如 1970-01-01）。
        
        优化特性:
        - 使用 asyncio.gather 实现并行处理。
        - 使用 asyncio.Semaphore(5) 限制并发数，防止触发 API 风暴或被封禁。
        - 增量提交：仅在实际有更新时操作数据库。
        
        Args:
            db (AsyncSession): 异步数据库会话。
            artist (Artist): 目标歌手的模型对象。
        """
        logger.info("🏥 启动全库元数据治愈...")
        
        # 获取所有歌曲
        res = await db.execute(select(Song).where(Song.artist_id == artist.id))
        all_db_songs = res.scalars().all()
        
        # 建立标题映射（用于伴奏回退）
        title_map = {s.title: s for s in all_db_songs}
        
        import asyncio
        semaphore = asyncio.Semaphore(5)  # 限制并发数为 5，防止被 API 封禁
        
        async def heal_with_semaphore(song):
            async with semaphore:
                return await self._heal_single_song(db, song, artist, title_map)
        
        # 创建任务列表
        tasks = [heal_with_semaphore(s) for s in all_db_songs]
        
        # 批量执行
        results = await asyncio.gather(*tasks)
        heal_count = sum(1 for r in results if r)
        
        if heal_count > 0:
            await db.commit()
            logger.info(f"✨ 全库治愈完成: 并行修复了 {heal_count} 首歌曲的元数据")
        else:
            logger.info("✨ 全库治愈完成: 所有歌曲状态良好")

    async def _heal_single_song(self, db: AsyncSession, s: Song, artist: Artist, title_map: Dict) -> bool:
        """
        治愈单首歌曲的元数据。（供 _heal_all_metadata 调用）
        
        Args:
            db (AsyncSession): 数据库会话。
            s (Song): 待检查的歌曲对象。
            artist (Artist): 所属歌手。
            title_map (Dict): 歌手所有歌曲的标题到歌曲对象的映射，用于伴奏回退。
            
        Returns:
            bool: 如果该歌曲有任何字段被更新，返回 True。
        """
        needs_update = False
        
        # 检查日期有效性
        is_invalid_date = False
        if not s.publish_time:
            is_invalid_date = True
        else:
            y = s.publish_time.year
            if y > datetime.now().year + 1 or y <= 1970:
                is_invalid_date = True
        
        # 检查封面
        is_missing_cover = False
        if not s.cover:
            is_missing_cover = True
        else:
            cover_str = str(s.cover)
            if 'placeholder' in cover_str or 'T002R300x300M000.jpg' in cover_str:
                is_missing_cover = True
        
        # 伴奏版回退策略
        if is_invalid_date and ("伴奏" in s.title or "Inst" in s.title):
            orig_title = re.sub(
                r"[\(\[【（].*?(伴奏|Inst|Backing).*?[\)\]】）]", 
                "", 
                s.title, 
                flags=re.IGNORECASE
            ).strip()
            if orig_title in title_map:
                orig = title_map[orig_title]
                if (orig.publish_time and 
                    1970 < orig.publish_time.year <= datetime.now().year + 1):
                    s.publish_time = orig.publish_time
                    needs_update = True
                    is_invalid_date = False
        
        # 全网补全
        if is_invalid_date or is_missing_cover:
            # TODO: 这里需要一个跨请求的计数器或限制
            # 暂时保持现有逻辑，但要注意并发时的计数
            if self._refresh_heal_count < 100:
                try:
                    meta = await self.aggregator.get_song_metadata_from_best_source(
                        s.title, artist.name
                    )
                    if meta:
                        if is_invalid_date and meta.get('publish_time'):
                            p_parsed = self.enrichment_service._parse_date(str(meta['publish_time']))
                            if p_parsed:
                                s.publish_time = p_parsed
                                needs_update = True
                        
                        if is_missing_cover and meta.get('cover_url'):
                            s.cover = meta['cover_url']
                            needs_update = True
                        
                        if not s.album and meta.get('album'):
                            s.album = meta['album']
                            needs_update = True
                        
                        self._refresh_heal_count += 1
                except Exception as e:
                    pass # 这里的异常由 gather 处理或抑制
        
        return needs_update

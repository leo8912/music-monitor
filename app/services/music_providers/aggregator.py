"""
音乐源聚合器

核心功能:
1. 并发调用多个音乐源(网易云 + QQ音乐)
2. 结果去重合并
3. 智能打分排序

Author: google
Created: 2026-01-23
"""

from typing import List, Dict, Tuple, Optional
from .base import MusicProvider, ArtistInfo, SongInfo
from .netease_provider import NeteaseProvider
from .qqmusic_provider import QQMusicProvider
import asyncio
import logging
import math
from collections import defaultdict

from app.utils.cache import persistent_cache

logger = logging.getLogger(__name__)


class MusicAggregator:
    """
    音乐源聚合器
    
    核心功能:
    1. 并发调用多个音乐源
    2. 结果去重合并  
    3. 智能打分排序
    """
    
    def __init__(self):
        self.providers: List[MusicProvider] = [
            NeteaseProvider(),
            QQMusicProvider()
        ]

    def get_provider(self, source_name: str) -> Optional[MusicProvider]:
        """获取指定源的提供者"""
        for provider in self.providers:
            if provider.source_name == source_name:
                return provider
        return None

    async def search_artist(self, keyword: str, limit: int = 10) -> List[ArtistInfo]:
        """
        并发搜索所有源,合并去重结果
        """
        logger.info(f"🔍 全网搜索歌手: {keyword}")



        
        # 并发调用所有提供者
        tasks = [provider.search_artist(keyword, limit) for provider in self.providers]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_results = []
        for i, results in enumerate(results_list):
            if isinstance(results, Exception):
                logger.error(f"❌ 音乐源 {self.providers[i].source_name} 失败: {results}")
                continue
            all_results.extend(results)
        
        logger.info(f"✅ 初步搜索到 {len(all_results)} 条结果 (未去重)")
        
        # 去重并打分
        deduplicated = self._deduplicate_and_score_artists(all_results, keyword)
        
        logger.info(f"📊 去重后返回 {len(deduplicated[:limit])} 条结果")
        
        return deduplicated[:limit]

    async def search_song(self, keyword: str, limit: int = 10) -> List[SongInfo]:
        """
        并发搜索歌曲
        """
        logger.info(f"🔍 全网搜索歌曲: {keyword}")
        
        all_results = []
        # Retry up to 2 times
        for attempt in range(2):
            if attempt > 0:
                logger.info(f"⚠️ 初次搜索无结果，正在重试 ({attempt}/1): {keyword}")
                await asyncio.sleep(1) # Wait a bit before retry
                
            tasks = [provider.search_song(keyword, limit) for provider in self.providers]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            current_results = []
            for i, results in enumerate(results_list):
                if isinstance(results, Exception):
                    logger.error(f"❌ 音乐源 {self.providers[i].source_name} 失败: {results}")
                    continue
                if results:
                    current_results.extend(results)
            
            if current_results:
                all_results = current_results
                break
        
        # 简单排序: 优先 QQ (为了更容易命中高音质/更全信息的源)
        all_results.sort(key=lambda x: 1 if x.source == 'qqmusic' else 0, reverse=True)
        
        logger.info(f"✅ 全网聚合搜索找到 {len(all_results)} 首歌曲: '{keyword}'")
        return all_results
    
    def _deduplicate_and_score_artists(
        self, 
        artists: List[ArtistInfo], 
        keyword: str
    ) -> List[ArtistInfo]:
        """
        去重并打分
        
        打分规则:
        1. 完全匹配: +100分
        2. 包含关键词: +50分
        3. 歌曲数量: +log(songCount)分
        4. 有头像: +10分
        
        去重策略:
        - 按名称(小写)分组
        - 同名歌手保留所有源的信息
        - 优先选择有头像和歌曲数多的
        """
        # 按名称分组
        groups = defaultdict(list)
        for artist in artists:
            key = artist.name.lower().strip()
            groups[key].append(artist)
        
        # 合并同名歌手的多个源
        merged: List[Tuple[ArtistInfo, float]] = []
        for name, group in groups.items():
            # 确定基础条目: 优先选择QQ音乐,否则取第一个
            base = group[0]
            qq_item = next((item for item in group if item.source == 'qqmusic'), None)
            if qq_item:
                base = qq_item
            
            # 初始化 extra_ids (保留自己的)
            if not base.extra_ids:
                base.extra_ids = {base.source: base.id}
            
            # 如果有多个源,合并信息(取最大歌曲数,补全头像,收集ID)
            for item in group:
                # 总是收集 ID
                base.extra_ids[item.source] = item.id
                
                if item == base:
                    continue
                # 补全头像
                if item.avatar and not base.avatar:
                    base.avatar = item.avatar
                # 取最大歌曲数
                if item.song_count > base.song_count:
                    base.song_count = item.song_count
            
            # 计算分数 (基础客观分)
            score = 0.0
            
            # 1. 名称匹配度
            if base.name.lower() == keyword.lower():
                score += 100  # 完全匹配
            elif keyword.lower() in base.name.lower():
                score += 50   # 包含关键词
            
            # 2. 歌曲数量 (使用对数平滑)
            if base.song_count > 0:
                score += math.log(base.song_count + 1)
            
            # 3. 信息完整度
            if base.avatar:
                score += 10
            
            merged.append((base, score))
        
        # 按分数排序
        # 第一关键字: 分数 (降序)
        # 第二关键字: 来源优先级 (QQ音乐 > 其他)
        merged.sort(key=lambda x: (x[1], 1 if x[0].source == 'qqmusic' else 0), reverse=True)
        
        return [artist for artist, score in merged]
    
    async def get_artist_songs_from_all_sources(
        self, 
        artist_name: str, 
        artist_ids: Dict[str, str],  # {'netease': 'id1', 'qqmusic': 'id2'}
        limit: int = 1000
    ) -> List[SongInfo]:
        """
        从所有源获取歌手歌曲
        
        Args:
            artist_name: 歌手名称
            artist_ids: 各源的歌手ID映射
            limit: 每个源的限制数量 (默认1000全量)
            
        Returns:
            List[SongInfo]: 所有源的歌曲列表 (未去重, 由 Service 层处理合并)
        """
        logger.info(f"📥 正在拉取歌手 {artist_name} 的全网歌曲...")
        
        tasks = []
        for provider in self.providers:
            if provider.source_name in artist_ids:
                tasks.append(
                    provider.get_artist_songs(artist_ids[provider.source_name], limit=limit)
                )
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_songs = []
        for i, results in enumerate(results_list):
            if isinstance(results, Exception):
                logger.error(f"Failed to get songs: {results}")
                continue
            all_songs.extend(results)
            
        # 智能过滤 (Smart Filter)
        cleaned_songs = []
        for song in all_songs:
            if self._is_valid_song(song):
                cleaned_songs.append(song)
            else:
                logger.debug(f"Filtered out dirty song: {song.title} ({song.source})")
        
        logger.info(f"Found {len(all_songs)} raw songs -> {len(cleaned_songs)} valid songs (returning raw list)")
        
        return cleaned_songs

    def _is_valid_song(self, song: SongInfo) -> bool:
        """
        Check if song is valid (not cover, not generic noise).
        """
        if not song.title: return False
        
        # Check basic keywords
        # 移除了 "伴奏"，允许伴奏版通过过滤
        garbage_keywords = ["片段", "铃声", "试听", "DJ版", "Remix", "Cover", "翻唱"]
        for kw in garbage_keywords:
            if kw in song.title:
                return False
                
        # Check if title starts with # (common noise)
        if song.title.startswith("#"):
            return False
            
        return True

    def _generate_dedup_key(self, title: str, artist: str) -> str:
        """生成去重键"""
        # 1. 统一转小写
        t = title.lower().strip()
        a = artist.lower().strip()
        
        # 2. 统一括号 (全角转半角)
        t = t.replace('（', '(').replace('）', ')')
        t = t.replace('【', '[').replace('】', ']')
        
        # 3. 移除括号前的空格 " (" -> "("
        t = t.replace(' (', '(').replace(' [', '[')
        
        # 4. 移除多余空格
        t = ' '.join(t.split())
        a = ' '.join(a.split())
        
        # 5. 提取版本标识 (伴奏/演奏/Instrumental)
        # 防止 "我不要原谅你" 和 "我不要原谅你 (伴奏)" 被合并
        version_tag = ""
        instrumental_keywords = ["伴奏", "演奏", "inst", "instrumental", "karaoke", "卡拉ok", "backing"]
        if any(kw in t for kw in instrumental_keywords):
            version_tag = "_inst"
            
        return f"{t}{version_tag}_{a}"
    
    @persistent_cache(namespace="aggregator_metadata")
    async def get_song_metadata_from_best_source(
        self, 
        song_title: str, 
        artist: str
    ) -> Optional[Dict]:
        """
        从最佳源获取歌曲元数据
        
        策略: 
        1. 并发调用所有源的 search_song
        2. 找到匹配度最高的结果(标题和歌手都要匹配)
        3. 返回合并后的元数据
        """
        keyword = f"{song_title} {artist}"
        logger.info(f"Getting metadata for: {keyword}")
        
        # 并发搜索
        tasks = [provider.search_song(keyword, limit=3) for provider in self.providers]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        best_match = None
        best_score = 0
        
        for i, results in enumerate(results_list):
            if isinstance(results, Exception):
                logger.error(f"Provider {self.providers[i].source_name} search_song failed: {results}")
                continue
                
            if isinstance(results, list):
                for song in results:
                    # 计算匹配分
                    score = 0
                    if song.title.lower() == song_title.lower():
                        score += 50
                    if song.artist.lower() == artist.lower():
                        score += 50
                    # 包含匹配
                    if song_title.lower() in song.title.lower():
                        score += 10
                    if artist.lower() in song.artist.lower():
                        score += 10
                        
                    # 优先选择有封面的
                    if song.cover_url:
                        score += 5
                    
                    if score > best_score:
                        best_score = score
                        best_match = song
        
        if best_match:
            logger.info(f"Found best match from {best_match.source}: {best_match.title} (Score: {best_score})")
            
            # 初始化结果
            final_meta = {
                'lyrics': '',
                'cover_url': best_match.cover_url,
                'album': best_match.album,
                'publish_time': best_match.publish_time,
                'source': best_match.source,
                'song_id': best_match.id
            }

            # 找到匹配的 provider
            provider = next((p for p in self.providers if p.source_name == best_match.source), None)
            if provider:
                # 获取完整元数据 (包括歌词)
                full_metadata = await provider.get_song_metadata(best_match.id)
                if full_metadata:
                    # 合并详情
                    if full_metadata.get('lyrics'): final_meta['lyrics'] = full_metadata['lyrics']
                    if not final_meta['cover_url']: final_meta['cover_url'] = full_metadata.get('cover_url', '')
                    if not final_meta['album']: final_meta['album'] = full_metadata.get('album', '')
                    if not final_meta['publish_time']: final_meta['publish_time'] = full_metadata.get('publish_time', '')

            # --- [New] 跨平台字段补全 ---
            # 如果核心字段（封面或专辑）仍然缺失，从搜索结果的其他候选项中补全
            if not final_meta['cover_url'] or not final_meta['album']:
                for i, results in enumerate(results_list):
                    if isinstance(results, list):
                        for s in results:
                            # 只要是同名同歌手（模糊匹配），就可以作为补全来源
                            # 强化匹配: 支持归一化标题匹配 (允许 Live 借用原版封面)
                            norm_s = self._normalize_title_for_healing(s.title)
                            norm_target = self._normalize_title_for_healing(song_title)

                            if norm_s == norm_target and s.artist.lower() == artist.lower():
                                if not final_meta['cover_url'] and s.cover_url:
                                    final_meta['cover_url'] = s.cover_url
                                    logger.info(f"      🖼️ 从备选源 {s.source} 补全了封面 (基于归一化匹配: {s.title})")
                                if not final_meta['album'] and s.album:
                                    final_meta['album'] = s.album
                                    logger.info(f"      💽 从备选源 {s.source} 补全了专辑名")
                                if not final_meta['publish_time'] and s.publish_time:
                                    final_meta['publish_time'] = s.publish_time
                            
                            if final_meta['cover_url'] and final_meta['album']:
                                break
            
            return final_meta
            
        logger.warning(f"No metadata found for {keyword}")
        return None

    def _normalize_title_for_healing(self, title: str) -> str:
        """为治愈流程准备的归一化标题 (移除括号和常见版本标识)"""
        import re
        t = title.lower().strip()
        # 移除 (Live), [伴奏], (Instrumental) 等
        t = re.sub(r"[\(\[【（].*?(live|伴奏|inst|instrumental|demo|acoustic|remix|version).*?[\)\]】）]", "", t, flags=re.IGNORECASE)
        # 移除多余空格
        return ' '.join(t.split())

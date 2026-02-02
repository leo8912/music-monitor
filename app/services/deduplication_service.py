from typing import List, Dict, Any, Optional
from datetime import datetime

class DeduplicationService:
    """
    负责多源歌曲去重与合并
    """
    
    @staticmethod
    def _normalize_title(title: str) -> str:
        """归一化标题用于去重建议：转小写、去空格、移除括号内的备注"""
        if not title: return ""
        import re
        # 1. 转小写并去空格
        t = title.lower().strip()
        
        # [Crucial Fix] Detect Instrumental BEFORE removing brackets
        # If it's a known instrumental/karaoke tag, we MUST preserve it or map to a distinct suffix
        # Otherwise "Song (Instrumental)" becomes "Song" == "Song" (Original) -> Bad Dedup
        
        inst_markers = ['test', 'instrumental', 'inst.', '伴奏', 'karaoke', 'off vocal']
        is_inst = False
        for m in inst_markers:
            # Check if marker exists (even inside brackets)
            if m in t:
                is_inst = True
                break
        
        # 2. 移除常见的后缀备注 (现场版), (remix), [2023...] 
        # 以及 | 之后的内容, - 之后的部分内容
        # [Adjusted] If it's instrumental, we still want to remove OTHER junk, but keep the distinction.
        # Strategy: Clean as usual, but append "_inst" if it was instrumental.
        
        t_clean = re.sub(r'[\(\[\{（【].*?[\)\]\}）】]', '', t)
        t_clean = re.sub(r'[\||－|-].*$', '', t_clean)
        t_clean = t_clean.strip()
        
        if is_inst:
            return f"{t_clean}_inst"
            
        return t_clean

    @staticmethod
    def deduplicate_songs(songs: List[Any]) -> List[Dict[str, Any]]:
        """
        对歌曲列表进行去重。
        """
        if not songs:
            return []
            
        grouped_songs = {}
        
        for song in songs:
            # [Security] 使用 getattr 防止在异步模式下触发懒加载报错 (MissingGreenlet)
            title = getattr(song, 'title', None) or (song.get('title', '') if isinstance(song, dict) else '')
            artist_val = getattr(song, 'artist', None)
            
            artist_name = ""
            if artist_val:
                # 安全获取关联对象的属性
                artist_name = getattr(artist_val, 'name', "")
            elif isinstance(song, dict):
                artist_name = song.get('artist', '')
                
            if not title:
                continue
                
            # 使用归一化后的标题作为粗略 Key
            norm_title = DeduplicationService._normalize_title(title)
            
            # 改进: 尝试模糊匹配 Artist (解决 "Artist A" vs "Artist A feat. B" 无法合并的问题)
            # 这里我们先只用 Title 分组，然后在组内再拆分? 
            # 为了性能和简单，我们保持 Key 结构，但在生成 Key 之前做一次 Artist 归一化
            
            # Simple normalization for artist: Use the first part of the artist name (before & / feat)
            import re
            norm_artist = artist_name.lower().strip()
            # 移除常见的合作标识之后的内容，为了更大概率合并
            # 注意: 这可能会导致翻唱歌曲被合并，但通常 title 决定了一切
            # 如果是翻唱，Title 通常会有 (Cover xxx) -> 被 _normalize_title 移除了 -> 冲突风险
            # 但用户更想要的是 "合并"，所以我们激进一点
            
            # 仅仅保留第一位歌手的名称用于分组 Key
            # 仅仅保留第一位歌手的名称用于分组 Key
            
            # Stage 1: Split by separators that require spaces (protects AC/DC, Earth, Wind & Fire)
            space_split_chars = [' & ', ' / '] 
            for char in space_split_chars:
                 if char in norm_artist:
                      norm_artist = norm_artist.split(char)[0].strip()

            # Stage 2: Split by separators that act as clear delimiters (feat, ft., vs, comma)
            # Comma usually implies list, so strict split is safer for "Artist A, Artist B"
            strict_split_chars = [',', 'feat', 'ft.', 'vs']
            for char in strict_split_chars:
                 if char in norm_artist:
                      norm_artist = norm_artist.split(char)[0].strip()
            
            key = f"{norm_title}_{norm_artist}"
            
            if key not in grouped_songs:
                grouped_songs[key] = []
            grouped_songs[key].append(song)
            
        # 2. 组内优选与合并
        result = []
        for key, group in grouped_songs.items():
            best_song = DeduplicationService._pick_best_song(group)
            if best_song:
                result.append(best_song)
                
        # 3. 排序逻辑：
        # 优先按发布日期 (从新到旧)，如果发布日期一致或缺失，按创建时间 (最新入库在前)
        def sort_key(s):
            pt = s.get('publishTime')
            # 尝试处理各种格式的发布时间
            if not pt or pt == "" or pt == "今天":
                pt_val = "0000-00-00" 
            else:
                pt_val = str(pt)
                
            ct = s.get('createdAt')
            if isinstance(ct, datetime):
                ct_val = ct.isoformat()
            else:
                ct_val = str(ct or "0000-00-00")
                
            return (pt_val, ct_val)

        result.sort(key=sort_key, reverse=True)
        
        return result

    @staticmethod
    def _pick_best_song(group: List[Any]) -> Dict[str, Any]:
        """从一组重复歌曲中选出最佳版本，并尝试合并额外信息"""
        if not group:
            return None
            
        # 评分函数
        def get_score(s):
            score = 0
            
            # 检查是否已本地化 (有 local_path 说明后端已确认存在物理文件)
            local_path = getattr(s, 'local_path', None)
            status = getattr(s, 'status', '')
            
            # 检查来源集合
            sources_list = getattr(s, 'sources', [])
            source_names = [src.source for src in sources_list] if sources_list else []
            
            if local_path:
                score += 1000
            if 'local' in source_names:
                score += 800
            if status == 'DOWNLOADED':
                score += 500
            
            # QQ 音乐数据作为主元数据通常更准确
            if 'qqmusic' in source_names:
                score += 100
                
            return score

        # 按分数选出 Best
        sorted_group = sorted(group, key=get_score, reverse=True)
        best_obj = sorted_group[0]
        
        # 提取歌手名 (安全访问)
        artist_val = getattr(best_obj, 'artist', None)
        artist_name = ""
        if artist_val:
            artist_name = getattr(artist_val, 'name', "")
        elif isinstance(best_obj, dict):
            artist_name = best_obj.get('artist', '')

        # 确定主 Source
        main_source = 'local' if getattr(best_obj, 'local_path', None) else None
        if not main_source and getattr(best_obj, 'sources', None):
            # 优先选择在线平台作为主来源，除非本地已下载
            platforms = [src.source for src in best_obj.sources if src.source != 'local']
            if platforms:
                main_source = platforms[0]
            else:
                main_source = best_obj.sources[0].source

        # 基础字典定义
        final_dict = {
            "id": getattr(best_obj, 'id', None),
            "title": getattr(best_obj, 'title', ''),
            "artist": artist_name,
            "album": getattr(best_obj, 'album', ''),
            "source": main_source or 'unknown',
            "source_id": "", # Will fill from sources
            "cover": getattr(best_obj, 'cover', None),
            "local_path": getattr(best_obj, 'local_path', None),
            "is_favorite": getattr(best_obj, 'is_favorite', False),
            "status": getattr(best_obj, 'status', 'PENDING'),
            "publishTime": getattr(best_obj, 'publish_time', None),
            "createdAt": getattr(best_obj, 'created_at', None),
            "availableSources": []
        }
        
        # 合并来源和发布时间
        sources_set = set()
        best_publish_time = final_dict['publishTime']
        
        for item in group:
            # 添加所有来源
            item_sources = getattr(item, 'sources', [])
            for src_obj in item_sources:
                sources_set.add(src_obj.source)
                # 如果主 source_id 还没填，拿第一个看到的 source_id
                if not final_dict['source_id']:
                    final_dict['source_id'] = src_obj.source_id
            
            # 如果是本地下载状态，添加一个标识（供前端显示绿点等）
            if getattr(item, 'status', '') == 'DOWNLOADED' or getattr(item, 'local_path', None):
                sources_set.add('downloaded')

            # 补全封面
            if not final_dict['cover']:
                final_dict['cover'] = getattr(item, 'cover', None)
                
            # 发布时间补全 (QQ 优先逻辑)
            pt = getattr(item, 'publish_time', None)
            if pt:
                item_source_names = [s.source for s in item_sources]
                if 'qqmusic' in item_source_names:
                    best_publish_time = pt # QQ 覆盖
                elif not best_publish_time:
                    best_publish_time = pt
        
        final_dict['publishTime'] = best_publish_time
        
        # 提取音质信息
        best_quality = None
        # 优先从主来源取
        if main_source:
             # Find source obj
             for item in group:
                  for src in getattr(item, 'sources', []):
                       if src.source == main_source:
                            data = src.data_json or {}
                            if isinstance(data, dict):
                                 q = data.get('quality')
                                 if q: best_quality = q
                       if best_quality: break
                  if best_quality: break
        
        # 如果主来源没取到，尝试取任何一个
        if not best_quality:
             for item in group:
                  for src in getattr(item, 'sources', []):
                       data = src.data_json or {}
                       if isinstance(data, dict):
                            q = data.get('quality')
                            if q: 
                                 best_quality = q
                                 break
                  if best_quality: break
                  
        final_dict['quality'] = best_quality
                    
        # 标签排序
        def source_sort_key(s):
            keys = {'local': 0, 'downloaded': 1, 'netease': 2, 'qqmusic': 3}
            return keys.get(s, 99)
            
        if 'local' in sources_set and 'downloaded' in sources_set:
            sources_set.remove('downloaded')

        final_dict['availableSources'] = sorted(list(sources_set), key=source_sort_key)

        return final_dict

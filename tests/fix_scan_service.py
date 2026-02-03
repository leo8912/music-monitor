
import os

file_path = "app/services/scan_service.py"

# The header line we know exists exactly as is
target_header = '    async def _extract_metadata(self, file_path: str, filename: str) -> Dict[str, any]:'

# The next method header, to define the end of the block
end_header = '    def _analyze_quality(self, audio_file) -> str:'

new_method = """    async def _extract_metadata(self, file_path: str, filename: str) -> Dict[str, any]:
        \"\"\"
        从音频文件中提取元数据
        (包含针对损坏 MP3 的 ID3 降级处理)
        \"\"\"
        from mutagen import File as MutagenFile
        from datetime import datetime
        import hashlib
        
        title = None
        artist_name = "Unknown"
        album = None
        publish_time = None
        cover_url = None
        quality_info = "HQ" 
        
        audio_file = None
        
        # 1. 尝试使用 mutagen.File 自动探测
        try:
            audio_file = MutagenFile(file_path, easy=False)
        except Exception:
            pass
        
        # 2. [Fix] 如果自动探测失败，且是 MP3，尝试强制读取 ID3 标签
        # 这可以解决 "can't sync to MPEG frame" 导致整个文件读取失败的问题
        if not audio_file and filename.lower().endswith('.mp3'):
             from mutagen.id3 import ID3
             try:
                 audio_file = ID3(file_path)
             except Exception:
                 pass

        if audio_file:
            # --- 封面提取 ---
            try:
                cover_data = None
                if hasattr(audio_file, 'tags') and audio_file.tags:
                    tags = audio_file.tags
                    # ID3 (MP3) or MP3 object with tags
                    if hasattr(tags, 'get') and (tags.get("APIC:") or tags.get("APIC")):
                        apic = tags.get("APIC:") or tags.get("APIC")
                        cover_data = apic.data
                    # FLAC or Vorbis
                    elif hasattr(audio_file, 'pictures') and audio_file.pictures:
                        cover_data = audio_file.pictures[0].data
                    # Fallback for ID3 dict iteration
                    elif isinstance(tags, dict): 
                         for key in tags.keys():
                            if key.startswith('APIC'):
                                cover_data = tags[key].data
                                break
                
                # M4A / MP4
                if not cover_data and hasattr(audio_file, 'tags') and 'covr' in audio_file.tags:
                    covrs = audio_file.tags['covr']
                    if covrs: cover_data = covrs[0]

                if cover_data:
                    # 计算封面 MD5
                    md5 = hashlib.md5(cover_data).hexdigest()
                    
                    upload_root = "uploads"
                    if os.path.exists("/config"): # Docker env
                         upload_root = "/config/uploads"
                    
                    cover_dir = os.path.join(upload_root, "covers")
                    os.makedirs(cover_dir, exist_ok=True)
                    
                    cover_filename = f"{md5}.jpg"
                    if cover_data.startswith(b'\\x89PNG'): cover_filename = f"{md5}.png"
                    
                    save_path = os.path.join(cover_dir, cover_filename)
                    if not os.path.exists(save_path):
                        with open(save_path, "wb") as f:
                            f.write(cover_data)
                    
                    cover_url = f"/uploads/covers/{cover_filename}"
                    
            except Exception as e:
                pass # Squelch cover errors

            # --- 基本信息提取 ---
            def get_tag(obj, keys):
                for k in keys:
                    # Case 1: Dict-like (EasyID3/dict)
                    if hasattr(obj, 'get'):
                        val = obj.get(k)
                        if val:
                            if isinstance(val, list): return val[0]
                            return str(val)
                    # Case 2: ID3 Object with tags attr
                    if hasattr(obj, 'tags') and obj.tags and k in obj.tags:
                        val = obj.tags[k]
                        if hasattr(val, 'text'): return val.text[0]
                        return str(val)
                    # Case 3: obj IS tags (ID3 Object)
                    if k in obj:
                         val = obj[k]
                         if hasattr(val, 'text'): return val.text[0]
                         return str(val)
                return None

            # 尝试从 tags 或 audio_file 本身获取
            target = audio_file
            if hasattr(audio_file, 'tags') and audio_file.tags:
                target = audio_file.tags

            # Title
            t = get_tag(target, ['title', 'TIT2'])
            if t: title = t
            
            # Artist
            a = get_tag(target, ['artist', 'TPE1'])
            if a: artist_name = a
            
            # Album
            al = get_tag(target, ['album', 'TALB'])
            if al: album = al
            
            # Date
            d = get_tag(target, ['date', 'TDRC', 'TYER'])
            if d:
                date_str = str(d)
                try:
                    year_str = str(date_str)[:4]
                    if year_str.isdigit():
                        publish_time = datetime.strptime(year_str, "%Y")
                except:
                    pass
    
        # 文件名回退策略
        clean_name = os.path.splitext(filename)[0]
        if not title:
            if " - " in clean_name:
                parts = clean_name.split(" - ", 1)
                artist_name = parts[0].strip()
                title = parts[1].strip()
            else:
                title = clean_name.strip()
        
        # Quality Analysis
        quality_info = "HQ"
        if audio_file:
             try:
                # Assuming _analyze_quality is available in self
                quality_info = self._analyze_quality(audio_file)
             except:
                quality_info = "HQ"
            
        return {
            "title": title,
            "artist_name": artist_name,
            "album": album,
            "publish_time": publish_time,
            "cover_url": cover_url,
            "quality": quality_info
        }

"""

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find(target_header)
end_idx = content.find(end_header)

if start_idx != -1 and end_idx != -1:
    print(f"Found block: {start_idx} to {end_idx}")
    new_content = content[:start_idx] + new_method + content[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully patched _extract_metadata")
else:
    print("String match failed.")
    print(f"Start found: {start_idx}")
    print(f"End found: {end_idx}")

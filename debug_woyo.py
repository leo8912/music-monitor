#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查"我要你"的文件标签和数据库状态"""

import sqlite3
import json
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
import os

db_path = "config/music_monitor.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

output = []
output.append("=" * 60)
output.append("检查'我要你'的完整状态")
output.append("=" * 60)

# 1. 查询数据库中的信息
query = """
SELECT 
    s.id, s.title, s.local_path,
    ss.id as source_id, ss.source, ss.data_json
FROM songs s
LEFT JOIN song_sources ss ON s.id = ss.song_id
WHERE s.title = '我要你'
ORDER BY ss.source;
"""

cursor.execute(query)
rows = cursor.fetchall()

if not rows:
    output.append("❌ 数据库中没有找到'我要你'")
else:
    song_id, title, local_path = rows[0][:3]
    output.append(f"\n📀 歌曲: {title} (ID: {song_id})")
    output.append(f"文件路径: {local_path}")
    
    # 2. 检查文件标签
    if local_path and os.path.exists(local_path):
        output.append(f"\n✅ 文件存在")
        try:
            if local_path.endswith('.flac'):
                audio = FLAC(local_path)
                lyrics = audio.get('lyrics', [None])[0]
            elif local_path.endswith('.mp3'):
                audio = MP3(local_path, ID3=ID3)
                lyrics = str(audio.get('USLT::XXX', None)) if audio.get('USLT::XXX') else None
            else:
                lyrics = None
            
            if lyrics:
                output.append(f"📝 文件标签中的歌词: 有 ({len(lyrics)} 字符)")
                output.append(f"歌词预览: {lyrics[:100]}...")
            else:
                output.append(f"❌ 文件标签中没有歌词")
        except Exception as e:
            output.append(f"❌ 读取文件标签失败: {e}")
    else:
        output.append(f"❌ 文件不存在: {local_path}")
    
    # 3. 检查数据库中的 data_json
    output.append(f"\n📊 数据库中的 source 记录:")
    for row in rows:
        _, _, _, source_id, source, data_json = row
        output.append(f"\n  Source: {source} (ID: {source_id})")
        if data_json:
            try:
                data = json.loads(data_json) if isinstance(data_json, str) else data_json
                has_lyrics = bool(data.get("lyrics"))
                output.append(f"    包含歌词: {has_lyrics}")
                if has_lyrics:
                    lyrics_len = len(data.get("lyrics", ""))
                    output.append(f"    歌词长度: {lyrics_len} 字符")
                    output.append(f"    歌词预览: {str(data.get('lyrics', ''))[:100]}...")
                output.append(f"    其他字段: {list(data.keys())}")
            except Exception as e:
                output.append(f"    ❌ 解析 data_json 失败: {e}")
        else:
            output.append(f"    ⚠️ data_json 为空")

conn.close()
output.append("\n" + "=" * 60)

# 写入文件
with open("debug_woyo.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("✅ 输出已保存到 debug_woyo.txt")

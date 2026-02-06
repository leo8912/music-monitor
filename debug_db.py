#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""临时调试脚本：检查 song_sources.data_json 内容"""

import sqlite3
import json

db_path = "config/music_monitor.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

output = []
output.append("=" * 60)
output.append("检查 song_sources 表中的 data_json 字段")
output.append("=" * 60)

# 查询最近修改的几首歌
query = """
SELECT 
    ss.id,
    ss.song_id,
    s.title,
    ss.source,
    ss.data_json
FROM song_sources ss
JOIN songs s ON ss.song_id = s.id
WHERE s.title IN ('我可以', '姑娘', '一生所爱', '屋顶', '我要你')
ORDER BY ss.song_id, ss.source
LIMIT 20;
"""

cursor.execute(query)
rows = cursor.fetchall()

for row in rows:
    source_id, song_id, title, source, data_json = row
    output.append(f"\n歌曲: {title} (ID: {song_id})")
    output.append(f"  Source ID: {source_id}, Source: {source}")
    output.append(f"  data_json 类型: {type(data_json).__name__}")
    
    if data_json:
        try:
            data = json.loads(data_json) if isinstance(data_json, str) else data_json
            has_lyrics = bool(data.get("lyrics")) if isinstance(data, dict) else False
            lyrics_preview = str(data.get("lyrics", ""))[:100] if has_lyrics else "N/A"
            output.append(f"  包含歌词: {has_lyrics}")
            output.append(f"  歌词预览: {lyrics_preview}...")
            output.append(f"  其他字段: {list(data.keys())}")
        except Exception as e:
            output.append(f"  ❌ 解析失败: {e}")
    else:
        output.append(f"  ⚠️ data_json 为空")

conn.close()
output.append("\n" + "=" * 60)

# 写入文件
with open("debug_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("✅ 输出已保存到 debug_output.txt")

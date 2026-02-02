# -*- coding: utf-8 -*-
"""
自动重构脚本:从 LibraryService 中移除已迁移的方法

移除的方法:
- scan_local_files (已迁移到 ScanService)
- enrich_local_files (已迁移到 EnrichmentService)
- refresh_library_metadata (已迁移到 EnrichmentService)
- _embed_cover_data (已迁移到 EnrichmentService)
- _embed_lyrics_to_file (已迁移到 EnrichmentService)
- _parse_date (已迁移到 EnrichmentService)
- _embed_publish_time_to_file (已迁移到 EnrichmentService)
- _embed_basic_metadata (已迁移到 EnrichmentService)
- _normalize_cn_brackets (已迁移到 ScanService)

保留的方法:
- toggle_favorite
- delete_song
- refresh_artist
- delete_artist
- apply_metadata_match
- reset_database
- redownload_song

Author: google
Created: 2026-01-30
"""

def find_method_range(lines, method_name, start_line):
    """查找方法的起始和结束行"""
    # 查找方法开始
    method_start = None
    for i in range(start_line - 1, len(lines)):
        if f'def {method_name}(' in lines[i]:
            method_start = i
            break
    
    if method_start is None:
        return None, None
    
    # 查找方法结束 (下一个同级或更高级的 def)
    indent_level = len(lines[method_start]) - len(lines[method_start].lstrip())
    
    for i in range(method_start + 1, len(lines)):
        line = lines[i]
        if line.strip() and not line.strip().startswith('#'):
            current_indent = len(line) - len(line.lstrip())
            # 如果遇到同级或更高级的定义,说明方法结束
            if current_indent <= indent_level and ('def ' in line or 'class ' in line):
                return method_start, i - 1
    
    # 如果没找到下一个方法,返回到文件末尾
    return method_start, len(lines) - 1

# 读取原文件
with open('app/services/library.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"原文件总行数: {len(lines)}")

# 需要删除的方法及其大致起始行号
methods_to_remove = {
    '_normalize_cn_brackets': 37,
    'scan_local_files': 128,
    'enrich_local_files': 318,
    'refresh_library_metadata': 473,
    '_embed_cover_data': 557,
    '_embed_lyrics_to_file': 627,
    '_parse_date': 670,
    '_embed_publish_time_to_file': 704,
    '_embed_basic_metadata': 775
}

# 收集要删除的行范围
ranges_to_remove = []
for method_name, approx_line in methods_to_remove.items():
    start, end = find_method_range(lines, method_name, approx_line)
    if start is not None:
        ranges_to_remove.append((start, end, method_name))
        print(f"找到方法 {method_name}: 行 {start+1} 到 {end+1} (共 {end-start+1} 行)")

# 按起始行排序并合并重叠范围
ranges_to_remove.sort()

# 创建新文件内容
new_lines = []
skip_until = -1

for i, line in enumerate(lines):
    # 检查是否在删除范围内
    should_skip = False
    for start, end, method_name in ranges_to_remove:
        if start <= i <= end:
            should_skip = True
            if i == start:
                print(f"删除方法 {method_name} (行 {start+1} 到 {end+1})")
            break
    
    if not should_skip:
        new_lines.append(line)

print(f"\n新文件总行数: {len(new_lines)}")
print(f"删除了 {len(lines) - len(new_lines)} 行")

# 写入新文件
with open('app/services/library.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("\n✅ LibraryService 精简完成!")

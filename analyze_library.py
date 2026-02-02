# -*- coding: utf-8 -*-
"""
临时脚本:提取 LibraryService 中需要保留的方法并创建精简版

Author: google
Created: 2026-01-30
"""

# 读取原文件
with open('app/services/library.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找需要保留的方法的起始和结束位置
methods_to_keep = [
    'toggle_favorite',
    'delete_song',
    'refresh_artist',
    'delete_artist',
    'apply_metadata_match',
    'reset_database',
    'redownload_song'  # 如果存在
]

# 打印文件信息
lines = content.split('\n')
print(f"原文件总行数: {len(lines)}")

# 查找各方法的行号
for method in methods_to_keep:
    for i, line in enumerate(lines, 1):
        if f'async def {method}(' in line or f'def {method}(' in line:
            print(f"{method}: 第 {i} 行")
            break

import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.services.music_providers import MusicAggregator
from app.services.library import LibraryService

async def analyze_artist():
    artist_name = "宿羽阳"
    artist_ids = {'qqmusic': '000GBnpV1IcEfl', 'netease': '12459252'}
    
    aggregator = MusicAggregator()
    lib_service = LibraryService()
    
    print(f"--- 正在从全网拉取 {artist_name} 的歌曲 ---")
    
    # 1. Fetch
    qq_songs = await aggregator.providers[1].get_artist_songs(artist_ids['qqmusic'], limit=100)
    netease_songs = await aggregator.providers[0].get_artist_songs(artist_ids['netease'], limit=100)
    all_raw = qq_songs + netease_songs
    
    target_title = "我不要原谅你"
    print(f"\n--- 目标歌曲: '{target_title}' 原始数据 ---")
    
    for s in all_raw:
        if target_title in s.title:
            is_valid = aggregator._is_valid_song(s)
            print(f"[{s.source}] Title: {s.title} | Valid: {is_valid} | Date: {s.publish_time} | ID: {s.id}")

    # Check for screenshot items
    screenshot_items = ["潮汐锁定", "请允许我成为你的夏季", "踏破风的少年", "暗恋是一个人的事"]
    print("\n--- 截图中的歌曲元数据核查 ---")
    for title in screenshot_items:
        found = False
        for s in all_raw:
            if title in s.title:
                found = True
                parsed_date = lib_service._parse_date(s.publish_time)
                print(f"[{s.source}] {s.title} | RawDate: {s.publish_time} | Parsed: {parsed_date} | Cover: {bool(s.cover_url)}")
        if not found:
            print(f"X NOT FOUND: {title}")

    # Simulate Grouping
    from collections import defaultdict
    grouped = defaultdict(list)
    for s in all_raw:
        if not aggregator._is_valid_song(s): continue
        key = aggregator._generate_dedup_key(s.title, s.artist)
        grouped[key].append(s)
        
    print("\n--- 最终分组结果 (伴奏相关) ---")
    for key in grouped:
        if target_title.lower() in key:
            print(f"Key: {key} (Count: {len(grouped[key])})")
            for s in grouped[key]:
                print(f"  - [{s.source}] {s.title}")

if __name__ == "__main__":
    asyncio.run(analyze_artist())

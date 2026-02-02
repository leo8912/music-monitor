"""
调试脚本 - 用于测试不同音乐源的可用性

此脚本用于测试不同音乐源（netease、tencent、kugou、kuwo等）的搜索和下载链接获取功能，
帮助识别哪些源可以获取到特定歌曲的音频文件。

Author: music-monitor development team

更新日志:
2026-01-23 - 创建脚本用于测试多源音频可用性 - ali
"""

import asyncio
import aiohttp
import logging
import json
import re

logging.basicConfig(level=logging.INFO)

async def check_source(session, source, keyword):
    print(f" Checking {source}...")
    url = f"https://music-api.gdstudio.xyz/api.php?types=search&count=5&source={source}&pages=1&name={keyword}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if not data:
                print(f"   ❌ No results on {source}")
                return None
                
            first = data[0]
            sid = first.get('id')
            url_api = f"https://music-api.gdstudio.xyz/api.php?types=url&source={source}&id={sid}&br=320"
            
            async with session.get(url_api, headers=headers) as u_resp:
                u_data = await u_resp.json()
                if u_data.get('url'):
                    print(f"   ✅ Found Valid URL on {source}! (ID: {sid})")
                    return sid
                else:
                    print(f"   ❌ Found match but NO URL on {source} (ID: {sid})")
    except Exception as e:
        print(f"   Error: {e}")
    return None

async def main():
    # Failed songs
    songs = [
        ("我偏要吻你破碎", "宿羽阳"),
        ("折桨", "宿羽阳")
    ]
    
    sources = ["netease", "tencent", "kugou", "kuwo"]
    
    print("--- Checking Cross-Source Availability ---")
    async with aiohttp.ClientSession() as session:
        for title, artist in songs:
            print(f"\nSong: {title} - {artist}")
            
            # Clean keyword like logic
            clean_title = re.sub(r'[<>:"/\\|?*]', ' ', title).strip()
            clean_artist = re.sub(r'[<>:"/\\|?*]', ' ', artist).strip()
            keyword = f"{clean_title} {clean_artist}"
            
            found = False
            for s in sources:
                if await check_source(session, s, keyword):
                    found = True
                    break
            
            if not found:
                print("   ⚠️ Not found on ANY source (netease/tencent/kugou/kuwo)")

if __name__ == "__main__":
    asyncio.run(main())

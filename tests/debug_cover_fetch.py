import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.music_providers.qqmusic_provider import QQMusicProvider

async def test_cover_fetch():
    provider = QQMusicProvider()
    
    # Test songs from the user's screenshot (Instrumental versions)
    test_songs = [
        {"keyword": "Purple Girl (伴奏) 宿羽阳", "expected_title": "Purple Girl"},
        {"keyword": "无用浪漫 (伴奏) 宿羽阳", "expected_title": "无用浪漫"},
        {"keyword": "心想事成歌舞厅 (伴奏) 宿羽阳", "expected_title": "心想事成"}
    ]

    output_lines = []
    output_lines.append("--- Starting Cover Fetch Test ---")

    for item in test_songs:
        keyword = item['keyword']
        output_lines.append(f"\n🔍 Searching for: {keyword}")
        
        # 1. Search
        results = await provider.search_song(keyword)
        
        found_song = None
        for res in results:
            output_lines.append(f"   Found: {res.title} - {res.artist} (Album: {res.album})")
            output_lines.append(f"   Cover URL: {res.cover_url}")
            if item['expected_title'] in res.title:
                found_song = res
                break
        
        if found_song:
            output_lines.append(f"\n   ✅ Selected Target: {found_song.title} (ID: {found_song.id})")
            
            # 2. Get Metadata (Simulate Scraper flow)
            output_lines.append("   ⬇️ Fetching details via get_song_metadata...")
            meta = await provider.get_song_metadata(found_song.id)
            if meta:
                output_lines.append(f"   [Metadata] Album: {meta.get('album')}")
                output_lines.append(f"   [Metadata] Cover: {meta.get('cover_url')}")
                output_lines.append(f"   [Metadata] Date: {meta.get('publish_time')}")
                
                if meta.get('cover_url') == found_song.cover_url:
                    output_lines.append("   ℹ️ Detail cover matches search cover.")
                else:
                    output_lines.append("   ✨ Detail cover is DIFFERENT from search cover!")
                    output_lines.append(f"   Wait, Search Cover: {found_song.cover_url}")
                    output_lines.append(f"   Detail Cover: {meta.get('cover_url')}")
            else:
                output_lines.append("   ❌ Failed to get metadata.")
        else:
            output_lines.append("   ❌ Song not found in search results.")
        
        output_lines.append("-" * 30)

    # Write to file
    with open("debug_scan_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("Verification complete. Results written to debug_scan_results.txt")

if __name__ == "__main__":
    # Windows loop policy fix
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_cover_fetch())

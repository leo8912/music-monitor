import asyncio
import sys
import os
import sqlite3

# Adapt path for imports
sys.path.append(os.getcwd())

from app.services.music_providers.qqmusic_provider import QQMusicProvider
from app.services.music_providers.netease_provider import NeteaseProvider

DB_PATH = "music_monitor.db"

def check_db():
    print(f"\n[Database Check] Checking '{DB_PATH}'...")
    if not os.path.exists(DB_PATH):
        print("Database file NOT found.")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check specific song (removed 'artist' column, joining is too complex for simple debug, just check title)
        cursor.execute("SELECT title, source, cover, publish_time, metadata_json FROM songs WHERE title LIKE '%我不要原谅你%'")
        rows = cursor.fetchall()
        
        if not rows:
            print("No record found in DB for '我不要原谅你'")
        else:
            print(f"Found {len(rows)} records:")
            for row in rows:
                print(f"  Title: {row[0]}\n  Source: {row[1]}\n  Cover: {row[2]}\n  Time: {row[3]}\n  Meta: {row[4]}")
        
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

async def test_apis():
    keyword = "我不要原谅你 宿羽阳"
    artist_name = "宿羽阳"
    print(f"\n[API Check] Searching for: {keyword}")
    
    # 1. Test QQ
    print("\n--- QQ Music ---")
    qq = QQMusicProvider()
    try:
        # A. Search Song
        print("A. Testing search_song...")
        songs = await qq.search_song(keyword, limit=1)
        if songs:
            s = songs[0]
            print(f"  Found: {s.title} (ID: {s.id})")
            print(f"  Cover: {s.cover_url}")
            
            # B. Get Metadata
            print("B. Testing get_song_metadata...")
            meta = await qq.get_song_metadata(s.id)
            print(f"  Metadata Cover: {meta.get('cover_url') if meta else 'None'}")
        else:
            print("  Not found on QQ Search")

        # C. Test Get Artist Songs (This is what Add Artist uses!)
        print("C. Testing get_artist_songs...")
        # First find artist ID
        artists = await qq.search_artist(artist_name, limit=1)
        if artists:
            aid = artists[0].id
            print(f"  Artist ID: {aid}")
            osongs = await qq.get_artist_songs(aid, limit=10)
            target = next((x for x in osongs if "我不要原谅你" in x.title), None)
            if target:
                print(f"  Found in Artist List!")
                print(f"  List Cover: {target.cover_url}")
                print(f"  List Album: {target.album}")
            else:
                print(f"  Not found in Artist's first 10 songs.")
        else:
            print("  Artist not found.")
            
    except Exception as e:
        print(f"QQ Error: {e}")
        import traceback
        traceback.print_exc()

    # 2. Test Netease
    print("\n--- Netease ---")
    ne = NeteaseProvider()
    try:
        # A. Search
        print("A. Testing search_song...")
        songs = await ne.search_song(keyword, limit=1)
        if songs:
            s = songs[0]
            print(f"  Found: {s.title} (ID: {s.id})")
            print(f"  Cover: {s.cover_url}")
        else:
            print("  Not found on Netease Search")
            
        # B. Get Artist Songs
        print("B. Testing search_artist & get_artist_songs...")
        artists = await ne.search_artist(artist_name, limit=1)
        if artists:
            aid = artists[0].id
            print(f"  Artist ID: {aid}")
            osongs = await ne.get_artist_songs(aid, limit=10)
            target = next((x for x in osongs if "我不要原谅你" in x.title), None)
            if target:
                print(f"  Found in Artist List!")
                print(f"  List Cover: {target.cover_url}")
            else:
                print(f"  Not found in Artist's first 10 songs.")
    except Exception as e:
        print(f"Netease Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_db()
    asyncio.run(test_apis())

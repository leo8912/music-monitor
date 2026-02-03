
import sqlite3
import os

db_path = "music_monitor.db"
if not os.path.exists(db_path):
    print(f"Cannot find {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

filename = "周杰伦 - 屋顶.flac"

print(f"--- Searching for Source: {filename} ---")
cursor.execute("SELECT * FROM song_sources WHERE source_id = ?", (filename,))
sources = cursor.fetchall()

if not sources:
    print("❌ No SongSource found for this filename.")
else:
    for src in sources:
        print(f"✅ Found Source: ID={src['id']}, SongID={src['song_id']}, Source={src['source']}")
        print(f"   Data: {src['data_json']}")
        
        # Get Song Info
        cursor.execute("SELECT * FROM songs WHERE id = ?", (src['song_id'],))
        song = cursor.fetchone()
        if song:
            print(f"   🔗 Song Info: ID={song['id']}, Title='{song['title']}', ArtistID={song['artist_id']}, Status='{song['status']}'")
            print(f"      PublishTime={song['publish_time']}, CreatedAt={song['created_at']}")
            
            # Get Artist Info
            cursor.execute("SELECT * FROM artists WHERE id = ?", (song['artist_id'],))
            artist = cursor.fetchone()
            if artist:
                 print(f"      🎤 Artist: {artist['name']}")
        else:
            print("   ❌ Song ID not found in songs table (Orphaned Source?)")

conn.close()

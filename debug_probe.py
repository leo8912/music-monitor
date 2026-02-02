import asyncio
import os
from mutagen import File as MutagenFile
from app.services.music_providers.qqmusic_provider import QQMusicProvider
from app.services.music_providers.netease_provider import NeteaseProvider

async def main():
    print("=== 1. Probing Local File Metadata ===")
    # Target one of the files seen in logs
    target_files = [
        "audio_cache/李剑青 - 平凡故事.flac", 
        "audio_cache/宿羽阳 - 我不要原谅你.flac"
    ]
    
    for fpath in target_files:
        if os.path.exists(fpath):
            print(f"\nFile: {fpath}")
            try:
                audio = MutagenFile(fpath)
                if audio:
                    print(f"  Type: {type(audio)}")
                    print(f"  Keys: {audio.keys()}")
                    for k in ['date', 'year', 'TDRC', 'TYER', 'ORIGINALDATE']:
                        if k in audio:
                            print(f"  Found '{k}': {audio[k]}")
                else:
                    print("  Mutagen failed to open (None)")
            except Exception as e:
                print(f"  Error reading: {e}")
        else:
            print(f"\nFile not found: {fpath}")

    print("\n=== 2. Testing Online Search (Auto-Enrich Source) ===")
    qq = QQMusicProvider()
    net = NeteaseProvider()
    
    keywords = ["宿羽阳 踏破风的少年", "宿羽阳 我不要原谅你"]
    
    for kw in keywords:
        print(f"\nSearching '{kw}' on QQ:")
        try:
            res = await qq.search_song(kw, limit=1)
            if res:
                s = res[0]
                print(f"  Title: {s.title}")
                print(f"  Time: {s.publish_time} (Raw)")
                if hasattr(s, 'get'):
                    print(f"  Full: {s.__dict__}")
                
                # Test get_song_metadata
                print("  Fetching Detail...")
                meta = await qq.get_song_metadata(s.id)
                print(f"  Detail Time: {meta.get('publish_time') if meta else 'None'}")
            else:
                print("  No results.")
        except Exception as e:
            print(f"  QQ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

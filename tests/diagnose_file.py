
import os
import sys
from mutagen import File as MutagenFile

file_paths = [
    r"d:\code\music-monitor\audio_cache\周杰伦 - 屋顶.flac",
    r"d:\code\music-monitor\library\姑娘 - 陈楚生.flac"
]

for path in file_paths:
    print(f"--- Testing: {path} ---")
    if not os.path.exists(path):
        print("❌ File does not exist")
        continue
        
    try:
        audio = MutagenFile(path, easy=False)
        if audio is None:
            print("❌ Mutagen returned None (Unknown format or corrupted)")
        else:
            print(f"✅ Mutagen parsed successfully. Type: {type(audio)}")
            print(f"   Info: {audio.info}")
            if hasattr(audio, 'tags'):
                print(f"   Tags keys: {audio.tags.keys() if audio.tags else 'None'}")
    except Exception as e:
        print(f"❌ Mutagen crashed: {e}")

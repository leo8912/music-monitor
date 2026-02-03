
import os
import sys
from mutagen import File as MutagenFile

# List of potential collision pairs based on listing
check_patterns = [
    ("d:\\code\\music-monitor\\audio_cache\\宿羽阳 - 我不要原谅你.flac", "d:\\code\\music-monitor\\audio_cache\\宿羽阳 - 我不要原谅你（伴奏）.flac"),
    ("d:\\code\\music-monitor\\audio_cache\\宿羽阳 - 剜心一刀.flac", "d:\\code\\music-monitor\\audio_cache\\宿羽阳 - 剜心一刀(伴奏).flac"),
    ("d:\\code\\music-monitor\\audio_cache\\李剑青 - 匆匆.flac", "d:\\code\\music-monitor\\audio_cache\\李剑青 - 匆匆 (瓦塔西老楠专属) (木吉他).flac")
]

def get_title(path):
    if not os.path.exists(path):
        return f"MISSING FILE: {path}"
    try:
        audio = MutagenFile(path, easy=False)
        if hasattr(audio, 'tags'):
            # VORBIS (FLAC)
            if hasattr(audio.tags, 'get'):
                t = audio.tags.get('title')
                if t: return t[0]
            # ID3
            if hasattr(audio.tags, 'getall'):
                t = audio.tags.getall('TIT2')
                if t: return t[0].text[0]
        # M4A, etc.. keeping simple for now as they are FLACs
        return "No Title Tag"
    except Exception as e:
        return f"Error: {e}"

print("Checking Metadata Titles for Collisions...")
for path1, path2 in check_patterns:
    print(f"\nComparing:")
    print(f"  1. {os.path.basename(path1)}")
    print(f"  2. {os.path.basename(path2)}")
    
    t1 = get_title(path1)
    t2 = get_title(path2)
    
    print(f"  Title 1: '{t1}'")
    print(f"  Title 2: '{t2}'")
    
    if t1 == t2:
        print("  ⚠️  COLLISION DETECTED: Identical Title Tags!")
    else:
        print("  ✅ Titles differ.")

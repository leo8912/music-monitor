
import os
from mutagen import File as MutagenFile

directories = [
    r"d:\code\music-monitor\audio_cache",
    r"d:\code\music-monitor\favorites",
    r"d:\code\music-monitor\library"
]
extensions = ('.mp3', '.flac', '.m4a', '.wav')

print("🔍 Finding Broken File...")
for d in directories:
    if not os.path.exists(d): continue
    for f in os.listdir(d):
        if not f.lower().endswith(extensions): continue
        path = os.path.join(d, f)
        try:
            audio = MutagenFile(path, easy=False)
            if audio is None:
                print(f"❌ FAIL (None): {f} in {d}")
        except Exception as e:
            print(f"❌ CRASH: {f} in {d}")
            print(f"   Error: {e}")
print("Done.")

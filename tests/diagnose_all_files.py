
import os
import time
import glob
from mutagen import File as MutagenFile

directories = [
    r"d:\code\music-monitor\audio_cache",
    r"d:\code\music-monitor\favorites",
    r"d:\code\music-monitor\library"
]

extensions = ('.mp3', '.flac', '.m4a', '.wav')

print("🔍 Starting Comprehensive File Diagnosis...")
print(f"{'Filename':<50} | {'Status':<10} | {'Time(ms)':<8} | {'Title':<30}")
print("-" * 110)

success_count = 0
fail_count = 0
slow_count = 0

for d in directories:
    if not os.path.exists(d):
        continue
        
    for f in os.listdir(d):
        if not f.lower().endswith(extensions):
            continue
            
        path = os.path.join(d, f)
        start = time.time()
        
        try:
            audio = MutagenFile(path, easy=False)
            duration_ms = (time.time() - start) * 1000
            
            status = "OK"
            if audio is None:
                status = "NONE"
                fail_count += 1
            else:
                success_count += 1
                
            title = "N/A"
            if audio:
                if hasattr(audio, 'tags'):
                    # VORBIS
                    if hasattr(audio.tags, 'get'):
                        t = audio.tags.get('title')
                        if t: title = t[0]
                    # ID3
                    if title == "N/A" and hasattr(audio.tags, 'getall'):
                        t = audio.tags.getall('TIT2')
                        if t: title = t[0].text[0]
            
            # Highlight slow files (> 500ms)
            time_str = f"{duration_ms:.1f}"
            if duration_ms > 500:
                time_str += " ⚠️"
                slow_count += 1
                
            print(f"{f[:48]:<50} | {status:<10} | {time_str:<8} | {str(title)[:30]}")
            
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            print(f"{f[:48]:<50} | CRASH      | {duration_ms:.1f}     | {e}")
            fail_count += 1

print("-" * 110)
print(f"Summary: Success={success_count}, Fail={fail_count}, Slow={slow_count}")

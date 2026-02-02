
import os
import sys
from mutagen.flac import FLAC
from mutagen.id3 import ID3

def inspect_file(path):
    print(f"Inspecting: {path}")
    if not os.path.exists(path):
        print("File not found!")
        return

    ext = os.path.splitext(path)[1].lower()
    if ext == '.flac':
        try:
            audio = FLAC(path)
            print("--- FLAC Tags ---")
            for k, v in audio.items():
                if k == 'cover': continue # Don't print binary
                print(f"{k}: {v}")
            
            if audio.pictures:
                print(f"Pictures: {len(audio.pictures)} embedded")
                for p in audio.pictures:
                    print(f"  - Type: {p.type}, Mime: {p.mime}, Desc: {p.desc}, Size: {len(p.data)} bytes")
            else:
                 print("Pictures: None")
                 
        except Exception as e:
            print(f"Error reading FLAC: {e}")
            
    elif ext == '.mp3':
        try:
            audio = ID3(path)
            print("--- ID3 Tags ---")
            for k, v in audio.items():
                if k.startswith('APIC'):
                     print(f"{k}: Type={v.type}, Mime={v.mime}, Desc={v.desc}, Size={len(v.data)}")
                else:
                     print(f"{k}: {v}")
        except Exception as e:
            print(f"Error reading MP3: {e}")

if __name__ == "__main__":
    # Hardcoded path for the specific file user is asking about
    target_path = "audio_cache/周杰伦 - 稻香.flac"
    inspect_file(target_path)

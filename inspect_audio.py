
import os
import sys
from mutagen import File

def inspect_flac_metadata(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        audio = File(file_path)
        if audio:
            print(f"--- Metadata for {os.path.basename(file_path)} ---")
            print(f"Type: {type(audio)}")
            if hasattr(audio, 'info'):
                info = audio.info
                print(f"Bitrate: {getattr(info, 'bitrate', 'N/A')}")
                print(f"Sample Rate: {getattr(info, 'sample_rate', 'N/A')}")
                print(f"Bits Per Sample: {getattr(info, 'bits_per_sample', 'N/A')}")
            
            # Pictures check
            if hasattr(audio, 'pictures'):
               print(f"FLAC Pictures: {len(audio.pictures)}")
            elif hasattr(audio, 'tags'):
               # ID3 APIC check
               apic = [t for t in audio.tags.keys() if 'APIC' in t]
               print(f"ID3 Pictures: {len(apic)}")
        else:
            print("Mutagen could not parse file")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Explicitly set the file path we want to check
    scan_dir = "audio_cache"
    target_file = None
    
    # Try to find "行走的鱼" in audio_cache
    if os.path.exists(scan_dir):
        for f in os.listdir(scan_dir):
            if "行走的鱼" in f and f.endswith(".flac"):
                target_file = os.path.join(scan_dir, f)
                break
    
    if target_file:
        inspect_flac_metadata(target_file)
    else:
        print("Target file '行走的鱼' not found in audio_cache")


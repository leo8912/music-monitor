import asyncio
import os
import sys
from mutagen.flac import FLAC

async def inspect_audio_quality():
    file_path = r"d:\code\music-monitor\audio_cache\宿羽阳 - 爱人呢.flac"
    
    print(f"🔍 Inspecting: {file_path}")
    
    if not os.path.exists(file_path):
        print("❌ File not found!")
        return

    try:
        audio = FLAC(file_path)
        print(f"Sample Rate: {audio.info.sample_rate} Hz")
        print(f"Bits Per Sample: {audio.info.bits_per_sample} bit")
        print(f"Channels: {audio.info.channels}")
        print(f"Bitrate: {audio.info.bitrate} bps") # FLAC bitrate is roughly calculated often
        
        # Classification logic simulation
        quality = "PQ"
        if audio.info.bits_per_sample > 16 or audio.info.sample_rate > 48000:
            quality = "HR"
        elif audio.info.bits_per_sample == 16 and audio.info.sample_rate >= 44100:
            quality = "SQ"
        elif audio.info.bitrate >= 320000: # Approximate for non-flac, but here it is flac
             quality = "HQ" 
        
        print(f" --> Calculated Quality Tier: {quality}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_audio_quality())

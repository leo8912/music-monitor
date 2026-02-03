
import os

log_path = r"d:\code\music-monitor\refresh_debug.log"

try:
    with open(log_path, 'r', encoding='utf-16le') as f:
        # Read last 2KB to identify recent errors
        f.seek(0, os.SEEK_END)
        size = f.tell()
        read_len = min(size, 4000)
        f.seek(size - read_len)
        content = f.read()
        print(content)
except Exception as e:
    print(f"Error reading log: {e}")

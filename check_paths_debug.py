
import sqlite3
import os
import sys

def check_paths():
    print(f"CWD: {os.getcwd()}")
    
    # Check default config path
    rel_path = 'config/music_monitor.db'
    abs_path = os.path.abspath(rel_path)
    
    print(f"Relative Path Strategy: {rel_path}")
    print(f"Absolute Path Strategy: {abs_path}")
    print(f"File Exists at Abs Path? {os.path.exists(abs_path)}")
    
    if os.path.exists(abs_path):
        conn = sqlite3.connect(abs_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, data_json FROM song_sources WHERE source='local' LIMIT 3")
        rows = cursor.fetchall()
        print("--- DB Content Check ---")
        for row in rows:
            print(f"ID {row[0]}: {row[1]}")
        conn.close()
    else:
        print("!!! DB File Missing at Expected Location !!!")
        
    # Check if there is another DB in root?
    root_db = 'music_monitor.db'
    if os.path.exists(root_db):
        print(f"!!! FOUND DB AT ROOT: {os.path.abspath(root_db)}")

if __name__ == "__main__":
    check_paths()

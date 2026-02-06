
import sqlite3
import os
import json

def fix_direct():
    db_path = 'config/music_monitor.db'
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Connected to DB.")
    
    # Get all local sources
    cursor.execute("SELECT id, url, data_json FROM song_sources WHERE source='local'")
    rows = cursor.fetchall()
    
    updated = 0
    for row in rows:
        src_id, url, data_json_str = row
        
        if not url: continue
        
        # Determine target quality
        ext = os.path.splitext(url)[1].lower()
        target_q = 'PQ'
        if ext in ['.flac', '.wav', '.ape', '.alac', '.aiff']:
            target_q = 'SQ'
        # elif ext in ['.mp3', 'm4a'] ... assume PQ/HQ logic, but let's strictly fix FLAC first.
        
        if target_q == 'SQ':
            # Parse JSON
            try:
                data = json.loads(data_json_str) if data_json_str else {}
            except:
                data = {}
                
            current_q = data.get('quality')
            
            if current_q != 'SQ':
                print(f"Updating ID {src_id} ({os.path.basename(url)}) : {current_q} -> SQ")
                data['quality'] = 'SQ'
                data['format'] = ext.replace('.', '').upper()
                data['quality_details'] = f"{data['format']} | SQ"
                
                new_json = json.dumps(data, ensure_ascii=False)
                
                cursor.execute("UPDATE song_sources SET data_json=? WHERE id=?", (new_json, src_id))
                updated += 1
    
    if updated > 0:
        conn.commit()
        print(f"Committed {updated} changes.")
    else:
        print("No changes needed.")
        
    conn.close()

if __name__ == "__main__":
    fix_direct()

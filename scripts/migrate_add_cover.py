import sqlite3
import os

DB_PATH = "music_monitor.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(download_history)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "cover_url" not in columns:
            print("Adding cover_url column to download_history table...")
            cursor.execute("ALTER TABLE download_history ADD COLUMN cover_url VARCHAR")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column cover_url already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

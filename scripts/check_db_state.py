import asyncio
import sys
import os
import sqlite3
from sqlalchemy import text, inspect, create_engine

# No need for app imports, just raw inspection
DB_PATH = "/config/music_monitor.db"
DB_URL = f"sqlite:///{DB_PATH}"

def check_permissions():
    print(f"🔍 Checking Permissions for {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("❌ DB File NOT FOUND")
        return
    
    stat = os.stat(DB_PATH)
    print(f"   - Owner UID: {stat.st_uid}")
    print(f"   - Owner GID: {stat.st_gid}")
    print(f"   - Permissions: {oct(stat.st_mode)[-3:]}")
    
    # Check if writable by current user
    if os.access(DB_PATH, os.W_OK):
        print("✅ Writable by current user")
    else:
        print("❌ NOT Writable by current user")

def inspect_schema():
    print(f"\n📋 Inspecting Schema in {DB_PATH}")
    
    engine = create_engine(DB_URL)
    inspector = inspect(engine)
    
    tables = inspector.get_table_names()
    print(f"   Found Tables: {tables}")
    
    required_tables = ['songs', 'artists', 'song_sources', 'system_settings']
    for t in required_tables:
        if t not in tables:
            print(f"   ❌ MISSING TABLE: {t}")
        else:
            print(f"   ✅ Table '{t}' exists.")
            # Check cols
            cols = [c['name'] for c in inspector.get_columns(t)]
            print(f"      Columns: {cols}")
            if t == 'songs' and 'cover' not in cols:
                print("      ❌ MISSING COLUMN 'cover' in 'songs'")

if __name__ == "__main__":
    try:
        check_permissions()
        if os.path.exists(DB_PATH):
            inspect_schema()
    except Exception as e:
        print(f"❌ Error: {e}")

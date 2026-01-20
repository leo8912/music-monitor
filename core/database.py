from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Index, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Use a local SQLite database by default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///music_monitor.db")

Base = declarative_base()

class MediaRecord(Base):
    """
    Stores the history of found media to prevent duplicate notifications.
    """
    __tablename__ = 'media_records'

    id = Column(Integer, primary_key=True)
    unique_key = Column(String, unique=True, index=True, nullable=False) # e.g., "netease:album:123456"
    
    source = Column(String, nullable=False)
    media_type = Column(String, nullable=False)
    media_id = Column(String, nullable=False)
    
    title = Column(String)
    author = Column(String)
    cover = Column(String, nullable=True) # Added for frontend display
    url = Column(String, nullable=True) # Added for playback
    album = Column(String, nullable=True) # Added for better dedup
    publish_time = Column(DateTime)
    
    # Audio & Lyrics extensions
    local_audio_path = Column(String, nullable=True) # Path relative to workspace or absolute
    audio_quality = Column(Integer, nullable=True)   # kbps, e.g. 320, 999
    lyrics = Column(Text, nullable=True)             # LRC content
    lyrics_source = Column(String, nullable=True)
    lyrics_updated_at = Column(DateTime, nullable=True)
    
    found_at = Column(DateTime, default=datetime.now)
    is_pushed = Column(Boolean, default=False)
    push_time = Column(DateTime, nullable=True)
    is_favorite = Column(Boolean, default=False) # Added for user favorites

    def __repr__(self):
        return f"<MediaRecord(key={self.unique_key}, title={self.title})>"

# Database initialization
if DATABASE_URL.startswith("sqlite:///"):
    # Extract path
    # sqlite:///foo.db -> foo.db
    # sqlite:////abs/foo.db -> /abs/foo.db
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            print(f"Created database directory: {db_dir}")
        except OSError as e:
            print(f"Failed to create database directory {db_dir}: {e}")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_db():
    """Simple migration to add missing columns."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('media_records')]
    
    with engine.connect() as conn:
        if 'is_favorite' not in columns:
            conn.execute(text("ALTER TABLE media_records ADD COLUMN is_favorite BOOLEAN DEFAULT 0"))
            conn.commit()
            print("Migrated: Added is_favorite column")

def init_db():
    Base.metadata.create_all(bind=engine)
    # Run migration after create_all (for existing DBs)
    try:
        migrate_db()
    except Exception as e:
        print(f"Migration check failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

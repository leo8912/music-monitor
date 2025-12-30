from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Index
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
    trial_url = Column(String, nullable=True) # Added for playback
    album = Column(String, nullable=True) # Added for better dedup
    publish_time = Column(DateTime)
    
    found_at = Column(DateTime, default=datetime.now)
    is_pushed = Column(Boolean, default=False)
    push_time = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<MediaRecord(key={self.unique_key}, title={self.title})>"

# Database initialization
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

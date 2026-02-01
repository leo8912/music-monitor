import pytest
from app.services.smart_merger import SmartMerger, SongMetadata

def test_smart_merge_decision_logic():
    merger = SmartMerger()
    
    # Case 1: Overwrite empty fields (补全空字段)
    local = SongMetadata(title="Song", artist="Artist", album=None)
    online = SongMetadata(title="Song", artist="Artist", album="New Album")
    result = merger.merge(local, online)
    assert result.album == "New Album"
    
    # Case 2: Overwrite garbage data (修复垃圾数据)
    local = SongMetadata(title="Song", artist="Artist", album="Unknown Album")
    online = SongMetadata(title="Song", artist="Artist", album="Real Album")
    result = merger.merge(local, online)
    assert result.album == "Real Album"
    
    # Case 3: Cover image logic (封面逻辑)
    # 假设本地没有封面，应当接受在线封面
    local = SongMetadata(title="Song", artist="Artist", cover_url=None)
    online = SongMetadata(title="Song", artist="Artist", cover_url="http://example.com/cover.jpg")
    result = merger.merge(local, online)
    assert result.cover_url == "http://example.com/cover.jpg"

    # Case 4: Keep existing valid data (保留现有有效数据)
    local = SongMetadata(title="Song", artist="Artist", album="Existing Valid Album")
    online = SongMetadata(title="Song", artist="Artist", album="Different Online Album")
    result = merger.merge(local, online)
    assert result.album == "Existing Valid Album"  # Default to conservative unless rule matches

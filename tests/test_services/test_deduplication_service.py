import pytest
from app.services.deduplication_service import DeduplicationService

def test_normalize_title():
    # Basic
    assert DeduplicationService._normalize_title("Song Name") == "song name"
    # Brackets removal
    assert DeduplicationService._normalize_title("Song (Live)") == "song"
    assert DeduplicationService._normalize_title("Another [2023 Remix]") == "another"
    # Suffix removal
    assert DeduplicationService._normalize_title("Title | Subtitle") == "title"
    assert DeduplicationService._normalize_title("Title - CD1") == "title"
    # Instrumental preservation
    assert DeduplicationService._normalize_title("Track (Instrumental)") == "track_inst"
    assert DeduplicationService._normalize_title("Song (伴奏)") == "song_inst"

def test_pick_best_song_logic():
    class MockSong:
        def __init__(self, id, title, local_path=None, status='PENDING', sources=None):
            self.id = id
            self.title = title
            self.local_path = local_path
            self.status = status
            self.sources = sources or []
            self.artist = None
            self.album = "Album"
            self.publish_time = None
            self.created_at = None

    class MockSource:
        def __init__(self, source, source_id):
            self.id = 1
            self.source = source
            self.source_id = source_id
            self.url = f"http://{source}/{source_id}"
            self.data_json = {}

    s1 = MockSong(1, "Song", sources=[MockSource("netease", "123")])
    s2 = MockSong(2, "Song", local_path="/path/to/file", status="DOWNLOADED", sources=[MockSource("local", "xxx")])
    
    group = [s1, s2]
    best = DeduplicationService._pick_best_song(group)
    
    assert best["id"] == 2
    assert "local" in best["available_sources"]
    assert "netease" in best["available_sources"]
    assert best["status"] == "DOWNLOADED"

def test_deduplicate_songs_merging():
    class MockArtist:
        def __init__(self, name):
            self.name = name

    class MockSong:
        def __init__(self, id, title, artist_name):
            self.id = id
            self.title = title
            self.artist = MockArtist(artist_name)
            self.sources = []
            self.local_path = None
            self.status = "PENDING"
            self.album = "Album"
            self.publish_time = "2024-01-01"
            self.created_at = None

    songs = [
        MockSong(1, "Hello", "Adele"),
        MockSong(2, "Hello (Live)", "Adele"),
        MockSong(3, "Rolling in the Deep", "Adele")
    ]
    
    result = DeduplicationService.deduplicate_songs(songs)
    # Hello and Hello (Live) should merge
    assert len(result) == 2
    titles = [s["title"] for s in result]
    assert "Hello" in titles
    assert "Rolling in the Deep" in titles

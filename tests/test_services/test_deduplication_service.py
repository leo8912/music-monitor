from app.services.deduplication_service import DeduplicationService

def test_normalize_title():
    # Basic
    assert DeduplicationService._normalize_title("Song Name") == "song name"
    # Brackets removal
    assert DeduplicationService._normalize_title("Song (Live)") == "song"
    assert DeduplicationService._normalize_title("Another [2023 Remix]") == "another"
    # Suffix removal
    assert DeduplicationService._normalize_title("Title | Subtitle") == "title"
    # [D-3 修复] ASCII 连字符不再被当作截断分隔符，否则 "A-Ha"/"Jay-Z"/"Rock-n-Roll"
    # 会被截成 "a"/"jay"/"rock" 并被错误合并。结尾的 " - CD1" / " - Disc 2" 分碟后缀
    # 已由单独的精确规则（\s+-\s+(cd|disc)\s*\d+$）补回剥离（见下方用例）。
    assert DeduplicationService._normalize_title("Title - CD1") == "title"
    # Instrumental preservation
    assert DeduplicationService._normalize_title("Track (Instrumental)") == "track_inst"
    assert DeduplicationService._normalize_title("Song (伴奏)") == "song_inst"


def test_disc_suffix_should_be_stripped():
    """回归守卫：D-3 修复后，结尾的 " - CD1" / " - Disc 2" 分碟后缀仍应被剥离，
    同时 "A-Ha"/"Jay-Z" 这类含连字符的合法歌名不受影响。"""
    assert DeduplicationService._normalize_title("Title - CD1") == "title"
    assert DeduplicationService._normalize_title("专辑名 - Disc 2") == "专辑名"
    # 连字符歌名不受影响
    assert DeduplicationService._normalize_title("A-Ha") == "a-ha"
    assert DeduplicationService._normalize_title("Jay-Z") == "jay-z"

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

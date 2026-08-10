# -*- coding: utf-8 -*-
"""
去重服务缺陷修复回归测试 (D-2 / D-3 / D-4)

本文件断言的是**修复后**的正确行为，用于验证本轮代码修复是否到位，
并作为长期回归防线，防止同类缺陷复发。

覆盖的三个缺陷
==============
D-2  伴奏误判
     `inst_markers` 里混入了裸字符串 `'test'`，导致任何标题里含 "test" 子串的歌
     （Protest / Contest / Greatest / Latest ...）都被打上 `_inst` 后缀，
     与真正的伴奏版归为两组，正片反而和自己的伴奏分家。

D-3  连字符截断
     归一化正则 `[\\||－|-].*$` 把 ASCII 连字符也当成分隔符，
     "A-Ha" -> "a"、"Jay-Z" -> "jay"。结果所有以同一字母开头的连字符歌名/艺名
     被塞进同一组，出现大面积错误合并。

D-4  QQ 发布时间优先失效
     "QQ 优先"的补全逻辑写在了 `for item in group` 循环**之外**，
     复用了循环结束后残留的 `item` / `item_sources` 变量，
     等价于"只看组内最后一个元素"。QQ 源不在末位时优先级完全失效。

每条用例都经过"在修复前必红、修复后必绿"的甄别，不是摆设。

Author: music-monitor QA
"""
import pytest

from app.services.deduplication_service import DeduplicationService


# ===========================================================================
# 测试替身 (Test Doubles)
# ===========================================================================
class FakeArtist:
    def __init__(self, name: str):
        self.name = name


class FakeSource:
    """模拟 SongSource ORM 对象，只暴露被测代码真正访问的字段。"""

    def __init__(self, source, source_id="sid", url=None, data_json=None, pk=1):
        self.id = pk
        self.source = source
        self.source_id = source_id
        self.url = url if url is not None else f"http://{source}/{source_id}"
        self.data_json = data_json if data_json is not None else {}


class FakeSong:
    """模拟 Song ORM 对象。刻意用普通对象，避免触发懒加载/需要 DB。"""

    def __init__(
        self,
        song_id,
        title,
        artist="测试歌手",
        sources=None,
        publish_time=None,
        local_path=None,
        status="PENDING",
        album="专辑",
        created_at=None,
        cover=None,
    ):
        self.id = song_id
        self.title = title
        self.artist = FakeArtist(artist) if artist else None
        self.sources = list(sources or [])
        self.publish_time = publish_time
        self.local_path = local_path
        self.status = status
        self.album = album
        self.created_at = created_at
        self.cover = cover
        self.is_favorite = False


@pytest.fixture(autouse=True)
def _clear_normalize_cache():
    """`_normalize_title` 带 lru_cache，参数化用例之间清一下更干净。"""
    DeduplicationService._normalize_title.cache_clear()
    yield
    DeduplicationService._normalize_title.cache_clear()


# ===========================================================================
# D-2：含 "test" 子串的标题不得被误判为伴奏
# ===========================================================================
class TestD2InstrumentalFalsePositive:

    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Protest Song", "protest song"),
            ("Contest", "contest"),
            ("Greatest Hits", "greatest hits"),
            ("Latest News", "latest news"),
            ("Attest", "attest"),
            ("最伟大的作品 Greatest Works", "最伟大的作品 greatest works"),
        ],
    )
    def test_test_substring_is_not_instrumental(self, title, expected):
        """标题里出现 test 子串纯属巧合，不能当成伴奏标记。"""
        norm = DeduplicationService._normalize_title(title)
        assert not norm.endswith("_inst"), (
            f"{title!r} 被误判为伴奏，归一化结果 = {norm!r}"
        )
        assert norm == expected

    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Track (Instrumental)", "track_inst"),
            ("Song (伴奏)", "song_inst"),
            ("Foo (Karaoke)", "foo_inst"),
            ("Bar (Off Vocal)", "bar_inst"),
            ("Baz (Inst.)", "baz_inst"),
        ],
    )
    def test_real_instrumental_still_detected(self, title, expected):
        """修掉误判的同时，真伴奏必须照常识别（防止矫枉过正）。"""
        assert DeduplicationService._normalize_title(title) == expected

    def test_original_and_instrumental_not_merged(self):
        """原唱与伴奏必须分成两条，这是 _inst 后缀存在的意义。"""
        songs = [
            FakeSong(1, "Hello", artist="Adele"),
            FakeSong(2, "Hello (Instrumental)", artist="Adele"),
        ]
        result = DeduplicationService.deduplicate_songs(songs)
        assert len(result) == 2


# ===========================================================================
# D-3：ASCII 连字符是歌名/艺名的合法字符，不得截断
# ===========================================================================
class TestD3HyphenPreserved:

    @pytest.mark.parametrize(
        "title, expected",
        [
            ("A-Ha", "a-ha"),
            ("Jay-Z", "jay-z"),
            ("Rock-n-Roll", "rock-n-roll"),
            ("Spider-Man Theme", "spider-man theme"),
            ("K-Pop Star", "k-pop star"),
        ],
    )
    def test_hyphen_is_kept(self, title, expected):
        """连字符必须原样保留在归一化结果里。"""
        norm = DeduplicationService._normalize_title(title)
        assert "-" in norm, f"{title!r} 的连字符被吃掉了，结果 = {norm!r}"
        assert norm == expected

    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Title | Subtitle", "title"),
            ("标题｜副标题", "标题"),
            ("标题－副标题", "标题"),
        ],
    )
    def test_pipe_and_fullwidth_dash_still_truncate(self, title, expected):
        """管道符 / 全角破折号仍应作为分隔符截断（这部分行为不变）。"""
        assert DeduplicationService._normalize_title(title) == expected

    def test_distinct_hyphen_titles_not_merged(self):
        """截断 bug 会让所有 'X-...' 归到同一组，这里守住不合并。"""
        songs = [
            FakeSong(1, "A-Ha", artist="Various"),
            FakeSong(2, "A-Team", artist="Various"),
        ]
        result = DeduplicationService.deduplicate_songs(songs)
        assert len(result) == 2, (
            f"不同歌曲被错误合并，结果 = {[s['title'] for s in result]}"
        )


# ===========================================================================
# D-4：组内合并发布时间时，QQ 音乐来源优先
# ===========================================================================
class TestD4QQPublishTimePriority:

    def test_qq_publish_time_wins_even_when_not_last(self):
        """
        QQ 源排在组内**首位**、最佳版本是本地文件时，
        合并结果的 publish_time 仍必须取 QQ 的值。

        旧实现只看组内最后一个元素，此处会拿到本地文件那个明显错误的 1999-01-01。
        """
        qq_song = FakeSong(
            1, "晴天",
            sources=[FakeSource("qqmusic", "q_001")],
            publish_time="2003-07-31",
        )
        local_song = FakeSong(
            2, "晴天",
            sources=[FakeSource("local", "l_001")],
            local_path="/library/晴天.flac",
            status="DOWNLOADED",
            publish_time="1999-01-01",   # 本地文件标签里的错误日期
        )

        result = DeduplicationService.deduplicate_songs([qq_song, local_song])

        assert len(result) == 1
        assert result[0]["publish_time"] == "2003-07-31"

    def test_non_last_item_fills_missing_publish_time(self):
        """最佳版本没有发布时间时，应从组内**任意**元素补全，而不只是最后一个。"""
        netease_song = FakeSong(
            1, "稻香",
            sources=[FakeSource("netease", "n_001")],
            publish_time="2008-10-15",
        )
        local_song = FakeSong(
            2, "稻香",
            sources=[FakeSource("local", "l_002")],
            local_path="/library/稻香.flac",
            publish_time=None,
        )

        result = DeduplicationService.deduplicate_songs([netease_song, local_song])

        assert len(result) == 1
        assert result[0]["publish_time"] == "2008-10-15"

    def test_qq_overrides_other_source_publish_time(self):
        """非 QQ 源先填了值，之后遇到 QQ 源仍应被覆盖。"""
        netease_song = FakeSong(
            1, "七里香",
            sources=[FakeSource("netease", "n_002")],
            publish_time="2010-01-01",
        )
        qq_song = FakeSong(
            2, "七里香",
            sources=[FakeSource("qqmusic", "q_002")],
            publish_time="2004-08-03",
        )

        result = DeduplicationService.deduplicate_songs([netease_song, qq_song])

        assert len(result) == 1
        assert result[0]["publish_time"] == "2004-08-03"

    def test_all_sources_collected_after_merge(self):
        """顺带守一下合并本身：两个来源都应出现在 available_sources 里。"""
        qq_song = FakeSong(3, "夜曲", sources=[FakeSource("qqmusic", "q_003")])
        netease_song = FakeSong(4, "夜曲", sources=[FakeSource("netease", "n_003")])

        result = DeduplicationService.deduplicate_songs([qq_song, netease_song])

        assert len(result) == 1
        assert set(result[0]["available_sources"]) == {"qqmusic", "netease"}


# ===========================================================================
# 回归护栏：原有 happy path 不能被上面的修复带崩
# ===========================================================================
class TestDeduplicationHappyPathRegression:

    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Song Name", "song name"),
            ("Song (Live)", "song"),
            ("Song (Remastered)", "song"),
            ("Another [2023 Remix]", "another"),
            ("歌名（现场版）", "歌名"),
            ("歌名【官方版】", "歌名"),
        ],
    )
    def test_bracket_annotations_removed(self, title, expected):
        assert DeduplicationService._normalize_title(title) == expected

    def test_empty_title_returns_empty(self):
        assert DeduplicationService._normalize_title("") == ""

    def test_live_version_merges_into_original(self):
        """(Live) 属于同一首歌的不同版本，应当合并。"""
        songs = [
            FakeSong(1, "Hello", artist="Adele"),
            FakeSong(2, "Hello (Live)", artist="Adele"),
            FakeSong(3, "Rolling in the Deep", artist="Adele"),
        ]
        result = DeduplicationService.deduplicate_songs(songs)

        assert len(result) == 2
        titles = [s["title"] for s in result]
        assert "Hello" in titles
        assert "Rolling in the Deep" in titles

    def test_local_downloaded_version_wins(self):
        """已下载到本地的版本得分最高，应被选为最佳版本。"""
        online = FakeSong(1, "Song", sources=[FakeSource("netease", "123")])
        local = FakeSong(
            2, "Song",
            sources=[FakeSource("local", "xxx")],
            local_path="/path/to/file",
            status="DOWNLOADED",
        )

        best = DeduplicationService._pick_best_song([online, local])

        assert best["id"] == 2
        assert best["status"] == "DOWNLOADED"
        assert "local" in best["available_sources"]
        assert "netease" in best["available_sources"]

    def test_empty_input_returns_empty_list(self):
        assert DeduplicationService.deduplicate_songs([]) == []

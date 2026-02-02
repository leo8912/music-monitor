# -*- coding: utf-8 -*-
"""
SmartMerger 单元测试

测试智能元数据合并决策逻辑（纯逻辑，不依赖网络）

Author: google
Created: 2026-02-02
"""
import pytest
from datetime import datetime
from app.services.smart_merger import SmartMerger, SongMetadata


class TestSmartMergerGarbageDetection:
    """垃圾数据检测测试"""
    
    def test_empty_string_is_garbage(self):
        """空字符串应判定为垃圾"""
        assert SmartMerger.is_garbage_value("") is True
        assert SmartMerger.is_garbage_value("   ") is True
        assert SmartMerger.is_garbage_value(None) is True
    
    def test_garbage_keywords_detected(self):
        """垃圾关键词应被检测"""
        assert SmartMerger.is_garbage_value("Unknown") is True
        assert SmartMerger.is_garbage_value("unknown artist") is True
        assert SmartMerger.is_garbage_value("Test Album") is True
        assert SmartMerger.is_garbage_value("未知歌手") is True
        assert SmartMerger.is_garbage_value("测试专辑") is True
    
    def test_valid_values_pass(self):
        """有效值应通过"""
        assert SmartMerger.is_garbage_value("周杰伦") is False
        assert SmartMerger.is_garbage_value("晴天") is False
        assert SmartMerger.is_garbage_value("Jay Chou") is False


class TestSmartMergerDateValidation:
    """日期验证测试"""
    
    def test_none_is_invalid(self):
        """空值应判定为无效"""
        assert SmartMerger.is_invalid_date(None) is True
    
    def test_unix_epoch_is_invalid(self):
        """1970年应判定为无效"""
        dt = datetime(1970, 1, 1)
        assert SmartMerger.is_invalid_date(dt) is True
    
    def test_valid_date_passes(self):
        """正常日期应通过"""
        dt = datetime(2024, 6, 15)
        assert SmartMerger.is_invalid_date(dt) is False
    
    def test_future_default_date_is_invalid(self):
        """未来年份的默认日期应判定为无效"""
        # 假设当前是 2026 年，2028-01-01 00:00:00 可能是无效的默认值
        dt = datetime(2028, 1, 1, 0, 0, 0)
        assert SmartMerger.is_invalid_date(dt) is True


class TestSmartMergerLyricsDetection:
    """歌词时间轴检测测试"""
    
    def test_empty_lyrics_no_time(self):
        """空歌词无时间轴"""
        assert SmartMerger.has_timed_lyrics(None) is False
        assert SmartMerger.has_timed_lyrics("") is False
    
    def test_plain_text_no_time(self):
        """纯文本歌词无时间轴"""
        lyrics = "第一行歌词\n第二行歌词\n第三行歌词"
        assert SmartMerger.has_timed_lyrics(lyrics) is False
    
    def test_lrc_format_has_time(self):
        """LRC格式歌词有时间轴"""
        lyrics = "[00:00.00]歌曲开始\n[00:05.20]第一行歌词\n[00:10.50]第二行歌词"
        assert SmartMerger.has_timed_lyrics(lyrics) is True
    
    def test_alternative_lrc_format(self):
        """另一种LRC格式"""
        lyrics = "[00:00:00]歌曲开始\n[00:05:20]第一行歌词"
        assert SmartMerger.has_timed_lyrics(lyrics) is True


class TestSmartMergerUpdateDecisions:
    """更新决策测试"""
    
    def test_should_update_album_from_garbage(self):
        """垃圾专辑 -> 有效专辑：应更新"""
        assert SmartMerger.should_update_album("Unknown", "叶惠美") is True
    
    def test_should_not_update_valid_album(self):
        """有效专辑 -> 另一个有效专辑：不更新"""
        assert SmartMerger.should_update_album("叶惠美", "范特西") is False
    
    def test_should_update_cover_when_empty(self):
        """无封面 -> 有封面：应更新"""
        assert SmartMerger.should_update_cover(None, 0, "http://example.com/cover.jpg", 0) is True
    
    def test_should_update_cover_quality_upgrade(self):
        """低画质 -> 高画质：应更新"""
        # 当前 40KB，新封面 300KB
        assert SmartMerger.should_update_cover(
            "http://example.com/small.jpg", 40 * 1024,
            "http://example.com/large.jpg", 300 * 1024
        ) is True
    
    def test_should_not_update_similar_quality_cover(self):
        """相近画质：不更新"""
        # 当前 100KB，新封面 150KB
        assert SmartMerger.should_update_cover(
            "http://example.com/current.jpg", 100 * 1024,
            "http://example.com/new.jpg", 150 * 1024
        ) is False
    
    def test_should_update_lyrics_plain_to_timed(self):
        """纯文本 -> 时间轴歌词：应更新"""
        plain = "第一行歌词\n第二行歌词"
        timed = "[00:00.00]歌曲开始\n[00:05.20]第一行歌词"
        assert SmartMerger.should_update_lyrics(plain, timed) is True
    
    def test_should_not_update_timed_to_plain(self):
        """时间轴歌词 -> 纯文本：不更新"""
        timed = "[00:00.00]歌曲开始\n[00:05.20]第一行歌词"
        plain = "第一行歌词\n第二行歌词"
        assert SmartMerger.should_update_lyrics(timed, plain) is False
    
    def test_should_update_publish_time_from_invalid(self):
        """无效日期 -> 有效日期：应更新"""
        invalid = datetime(1970, 1, 1)
        valid = datetime(2024, 6, 15)
        assert SmartMerger.should_update_publish_time(invalid, valid) is True
    
    def test_should_not_update_valid_date(self):
        """有效日期 -> 另一个有效日期：不更新"""
        date1 = datetime(2024, 6, 15)
        date2 = datetime(2024, 7, 20)
        assert SmartMerger.should_update_publish_time(date1, date2) is False


class TestSmartMergerMerge:
    """合并逻辑测试"""
    
    def test_merge_empty_to_full(self):
        """空元数据 + 完整元数据 = 全部更新"""
        current = SongMetadata(
            title="晴天",
            album=None,
            cover_url=None,
            lyrics=None,
            publish_time=None
        )
        new = SongMetadata(
            title="晴天",
            album="叶惠美",
            cover_url="http://example.com/cover.jpg",
            cover_size_bytes=300 * 1024,
            lyrics="[00:00.00]故事的小黄花",
            publish_time=datetime(2003, 7, 31)
        )
        
        updates = SmartMerger.merge(current, new)
        
        assert "album" in updates
        assert "cover" in updates
        assert "lyrics" in updates
        assert "publish_time" in updates
    
    def test_merge_full_to_full_no_update(self):
        """完整元数据 + 完整元数据 = 不更新（保留现有）"""
        current = SongMetadata(
            title="晴天",
            album="叶惠美",
            cover_url="http://example.com/cover.jpg",
            cover_size_bytes=300 * 1024,
            lyrics="[00:00.00]故事的小黄花",
            publish_time=datetime(2003, 7, 31)
        )
        new = SongMetadata(
            title="晴天",
            album="叶惠美 (新版)",
            cover_url="http://example.com/cover2.jpg",
            cover_size_bytes=200 * 1024,
            lyrics="[00:00.00]故事的小黄花 (新版)",
            publish_time=datetime(2003, 7, 31)
        )
        
        updates = SmartMerger.merge(current, new)
        
        # 由于现有数据已完整，不应更新
        assert "album" not in updates
        assert "cover" not in updates
        assert "lyrics" not in updates


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

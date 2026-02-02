# -*- coding: utf-8 -*-
"""
ArtistRefreshService 单元测试

测试歌手刷新服务的核心功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.artist_refresh_service import ArtistRefreshService
from app.models.artist import Artist, ArtistSource
from app.models.song import Song


@pytest.fixture
def artist_refresh_service():
    """创建 ArtistRefreshService 实例"""
    return ArtistRefreshService()


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_artist():
    """创建示例歌手"""
    artist = Artist(
        id=1,
        name="周杰伦",
        avatar="http://example.com/avatar.jpg"
    )
    return artist


@pytest.fixture
def sample_online_songs():
    """创建示例在线歌曲"""
    class MockSong:
        def __init__(self, title, source, song_id, album=None, publish_time=None):
            self.title = title
            self.source = source
            self.id = song_id
            self.album = album
            self.publish_time = publish_time
            self.cover_url = f"http://example.com/{title}.jpg"
            self.duration = 240
    
    return [
        MockSong("七里香", "qqmusic", "001", "七里香", "2004-08-03"),
        MockSong("稻香", "netease", "002", "魔杰座", "2008-10-15"),
        MockSong("晴天", "qqmusic", "003", "叶惠美", "2003-07-31"),
    ]


class TestArtistRefreshService:
    """ArtistRefreshService 基础测试"""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, artist_refresh_service):
        """测试：服务初始化"""
        assert artist_refresh_service is not None
        assert hasattr(artist_refresh_service, 'aggregator')
        assert hasattr(artist_refresh_service, 'scan_service')
        assert hasattr(artist_refresh_service, 'enrichment_service')
    
    @pytest.mark.asyncio
    async def test_refresh_artist_not_found(
        self, 
        artist_refresh_service, 
        mock_db
    ):
        """测试：歌手不存在"""
        # 准备
        with patch('app.repositories.artist.ArtistRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_name = AsyncMock(return_value=None)
            
            # 执行
            result = await artist_refresh_service.refresh(mock_db, "不存在的歌手")
        
        # 验证
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_find_match_exact(self, artist_refresh_service):
        """测试：精确匹配"""
        # 准备
        class MockCandidate:
            def __init__(self, title):
                self.title = title
        
        candidates = [
            MockCandidate("七里香"),
            MockCandidate("稻香"),
        ]
        
        local_song = Song(title="七里香")
        
        # 执行
        match = artist_refresh_service._find_match(candidates, local_song)
        
        # 验证
        assert match is not None
        assert match.title == "七里香"
    
    @pytest.mark.asyncio
    async def test_find_match_fuzzy(self, artist_refresh_service):
        """测试：模糊匹配"""
        # 准备
        class MockCandidate:
            def __init__(self, title):
                self.title = title
        
        candidates = [
            MockCandidate("七里香 (Live版)"),
        ]
        
        local_song = Song(title="七里香")
        
        # 执行
        match = artist_refresh_service._find_match(candidates, local_song)
        
        # 验证
        assert match is not None
    
    @pytest.mark.asyncio
    async def test_find_match_no_match(self, artist_refresh_service):
        """测试：无匹配"""
        # 准备
        class MockCandidate:
            def __init__(self, title):
                self.title = title
        
        candidates = [
            MockCandidate("稻香"),
        ]
        
        local_song = Song(title="七里香")
        
        # 执行
        match = artist_refresh_service._find_match(candidates, local_song)
        
        # 验证
        assert match is None


class TestMetadataHealing:
    """元数据治愈测试"""
    
    @pytest.mark.asyncio
    async def test_heal_all_metadata_no_songs(
        self, 
        artist_refresh_service, 
        mock_db, 
        sample_artist
    ):
        """测试：无歌曲时的治愈"""
        # 准备
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # 执行（不应该抛出异常）
        await artist_refresh_service._heal_all_metadata(mock_db, sample_artist)
        
        # 验证：应该正常完成
        assert True
    
    @pytest.mark.asyncio
    async def test_heal_invalid_date(
        self, 
        artist_refresh_service, 
        mock_db, 
        sample_artist
    ):
        """测试：修复无效日期"""
        # 准备
        song_with_bad_date = Song(
            id=1,
            title="测试歌曲",
            artist_id=1,
            publish_time=datetime(1970, 1, 1),  # 无效日期
            cover="http://example.com/cover.jpg"
        )
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [song_with_bad_date]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(
            artist_refresh_service.aggregator,
            'get_song_metadata_from_best_source',
            new=AsyncMock(return_value={
                'publish_time': '2020-01-01',
                'cover_url': 'http://example.com/new_cover.jpg'
            })
        ):
            # 执行
            await artist_refresh_service._heal_all_metadata(mock_db, sample_artist)
        
        # 验证：日期应该被更新
        assert song_with_bad_date.publish_time.year != 1970


class TestReverseLoopup:
    """反向查找测试"""
    
    @pytest.mark.asyncio
    async def test_reverse_lookup_originals(
        self, 
        artist_refresh_service, 
        sample_artist
    ):
        """测试：反向查找原版歌曲"""
        # 准备
        class MockSong:
            def __init__(self, title):
                self.title = title
        
        raw_songs = [
            MockSong("七里香（伴奏）"),
        ]
        
        with patch.object(
            artist_refresh_service.aggregator.providers[0],
            'search_song',
            new=AsyncMock(return_value=[MockSong("七里香")])
        ):
            with patch('core.websocket.manager') as mock_manager:
                mock_manager.broadcast = AsyncMock()
                
                # 执行
                result = await artist_refresh_service._reverse_lookup_originals(
                    raw_songs, sample_artist, mock_manager
                )
        
        # 验证：应该找到原版
        assert len(result) > len(raw_songs)


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_empty_online_songs(
        self, 
        artist_refresh_service, 
        mock_db, 
        sample_artist
    ):
        """测试：在线歌曲为空"""
        # 准备
        with patch('app.repositories.artist.ArtistRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_name = AsyncMock(return_value=sample_artist)
            
            # 模拟空的源列表
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            with patch.object(
                artist_refresh_service.scan_service,
                'scan_local_files',
                new=AsyncMock()
            ):
                with patch('core.websocket.manager') as mock_manager:
                    mock_manager.broadcast = AsyncMock()
                    
                    with patch('app.repositories.artist.ArtistRepository') as MockArtistRepo:
                        mock_artist_repo = MockArtistRepo.return_value
                        mock_artist_repo.get_song_count = AsyncMock(return_value=0)
                        
                        # 执行
                        result = await artist_refresh_service.refresh(mock_db, "周杰伦")
        
        # 验证
        assert result == 0

# -*- coding: utf-8 -*-
"""
SongManagementService 单元测试

测试歌曲管理服务的核心功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.song_management_service import SongManagementService
from app.models.song import Song
from app.models.artist import Artist


@pytest.fixture
def song_service():
    """创建 SongManagementService 实例"""
    return SongManagementService()


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def sample_song():
    """创建示例歌曲"""
    artist = Artist(id=1, name="测试歌手")
    song = Song(
        id=1,
        title="测试歌曲",
        artist_id=1,
        artist=artist,
        local_path="audio_cache/test.mp3",
        status="DOWNLOADED"
    )
    return song


class TestServiceInitialization:
    """服务初始化测试"""
    
    def test_service_init(self, song_service):
        """测试：服务初始化"""
        assert song_service is not None
        assert hasattr(song_service, 'aggregator')
        assert hasattr(song_service, 'metadata_service')


class TestDeleteSong:
    """删除歌曲测试"""
    
    @pytest.mark.asyncio
    async def test_delete_song_success(self, song_service, mock_db, sample_song):
        """测试：成功删除歌曲"""
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=sample_song)
            mock_repo.delete = AsyncMock(return_value=True)
            
            with patch('anyio.to_thread.run_sync', new_callable=AsyncMock) as mock_sync:
                mock_sync.side_effect = [True, None]  # exists, remove
                
                result = await song_service.delete_song(mock_db, 1)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_song_not_found(self, song_service, mock_db):
        """测试：歌曲不存在"""
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=None)
            
            result = await song_service.delete_song(mock_db, 999)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_song_no_local_file(self, song_service, mock_db):
        """测试：删除无本地文件的歌曲"""
        song_no_file = Song(id=2, title="无文件", local_path=None)
        
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=song_no_file)
            mock_repo.delete = AsyncMock(return_value=True)
            
            result = await song_service.delete_song(mock_db, 2)
        
        assert result is True


class TestDeleteArtist:
    """删除歌手测试"""
    
    @pytest.mark.asyncio
    async def test_delete_artist_by_id(self, song_service, mock_db):
        """测试：通过ID删除歌手"""
        with patch('app.repositories.artist.ArtistRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete = AsyncMock(return_value=True)
            
            result = await song_service.delete_artist(mock_db, artist_id=1)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_artist_by_name(self, song_service, mock_db):
        """测试：通过名称删除歌手"""
        artist = Artist(id=1, name="测试歌手")
        
        with patch('app.repositories.artist.ArtistRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_name = AsyncMock(return_value=artist)
            mock_repo.delete = AsyncMock(return_value=True)
            
            result = await song_service.delete_artist(mock_db, artist_name="测试歌手")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_artist_not_found(self, song_service, mock_db):
        """测试：歌手不存在"""
        with patch('app.repositories.artist.ArtistRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_name = AsyncMock(return_value=None)
            
            result = await song_service.delete_artist(mock_db, artist_name="不存在")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_artist_no_params(self, song_service, mock_db):
        """测试：无参数"""
        result = await song_service.delete_artist(mock_db)
        assert result is False


class TestResetDatabase:
    """重置数据库测试"""
    
    @pytest.mark.asyncio
    async def test_reset_database_success(self, song_service, mock_db):
        """测试：成功重置数据库"""
        mock_db.execute = AsyncMock()
        
        result = await song_service.reset_database(mock_db)
        
        assert result is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_database_failure(self, song_service, mock_db):
        """测试：重置数据库失败"""
        mock_db.execute = AsyncMock(side_effect=Exception("数据库错误"))
        
        result = await song_service.reset_database(mock_db)
        
        assert result is False
        mock_db.rollback.assert_called_once()


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_delete_song_file_not_exist(self, song_service, mock_db, sample_song):
        """测试：本地文件不存在时删除"""
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=sample_song)
            mock_repo.delete = AsyncMock(return_value=True)
            
            with patch('anyio.to_thread.run_sync', new_callable=AsyncMock) as mock_sync:
                mock_sync.return_value = False  # file doesn't exist
                
                result = await song_service.delete_song(mock_db, 1)
        
        assert result is True

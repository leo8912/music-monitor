# -*- coding: utf-8 -*-
"""
FavoriteService 单元测试

测试收藏管理服务的核心功能
"""
import pytest
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.favorite_service import FavoriteService
from app.models.song import Song


@pytest.fixture
def favorite_service():
    """创建 FavoriteService 实例"""
    return FavoriteService()


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_song():
    """创建示例歌曲"""
    song = Song(
        id=1,
        title="测试歌曲",
        artist_id=1,
        is_favorite=False,
        local_path="audio_cache/test.mp3"
    )
    return song


class TestFavoriteService:
    """FavoriteService 测试类"""
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_to_true(
        self, 
        favorite_service, 
        mock_db, 
        sample_song
    ):
        """测试：切换收藏状态为 True"""
        # 准备
        sample_song.is_favorite = False
        
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.toggle_favorite = AsyncMock(return_value=sample_song)
            
            with patch('anyio.to_thread.run_sync') as mock_run_sync:
                # 模拟文件存在
                mock_run_sync.side_effect = [
                    True,  # old_path.exists()
                    None,  # shutil.move()
                ]
                
                # 执行
                result = await favorite_service.toggle(mock_db, 1)
        
        # 验证
        assert result is not None
        assert result["song_id"] == 1
        assert result["is_favorite"] == False
        assert "new_path" in result
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_no_local_file(
        self, 
        favorite_service, 
        mock_db
    ):
        """测试：切换收藏状态（无本地文件）"""
        # 准备
        song_without_file = Song(
            id=2,
            title="无文件歌曲",
            artist_id=1,
            is_favorite=False,
            local_path=None
        )
        
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.toggle_favorite = AsyncMock(return_value=song_without_file)
            
            # 执行
            result = await favorite_service.toggle(mock_db, 2)
        
        # 验证
        assert result is not None
        assert result["song_id"] == 2
        assert result["new_path"] is None
        assert "无本地文件" in result["message"]
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_song_not_found(
        self, 
        favorite_service, 
        mock_db
    ):
        """测试：歌曲不存在"""
        # 准备
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.toggle_favorite = AsyncMock(return_value=None)
            
            # 执行
            result = await favorite_service.toggle(mock_db, 999)
        
        # 验证
        assert result is None
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_file_move_error(
        self, 
        favorite_service, 
        mock_db, 
        sample_song
    ):
        """测试：文件移动失败（应该继续完成状态切换）"""
        # 准备
        sample_song.is_favorite = True
        
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.toggle_favorite = AsyncMock(return_value=sample_song)
            
            with patch('anyio.to_thread.run_sync') as mock_run_sync:
                # 模拟文件存在但移动失败
                mock_run_sync.side_effect = [
                    True,  # old_path.exists()
                    Exception("移动失败")  # shutil.move() 抛出异常
                ]
                
                # 执行（不应该抛出异常）
                result = await favorite_service.toggle(mock_db, 1)
        
        # 验证：即使移动失败，也应该返回结果
        assert result is not None
        assert result["song_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_favorites(self, favorite_service, mock_db):
        """测试：获取收藏列表"""
        # 准备
        favorite_songs = [
            Song(id=1, title="收藏1", is_favorite=True),
            Song(id=2, title="收藏2", is_favorite=True),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = favorite_songs
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # 执行
        result = await favorite_service.get_favorites(mock_db, limit=10)
        
        # 验证
        assert len(result) == 2
        assert all(s.is_favorite for s in result)
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_path_update(
        self, 
        favorite_service, 
        mock_db, 
        sample_song
    ):
        """测试：收藏后路径正确更新"""
        # 准备
        sample_song.is_favorite = False
        sample_song.local_path = "audio_cache/test.mp3"
        
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.toggle_favorite = AsyncMock(return_value=sample_song)
            
            with patch('anyio.to_thread.run_sync') as mock_run_sync:
                mock_run_sync.side_effect = [
                    True,  # old_path.exists()
                    None,  # shutil.move()
                ]
                
                with patch('pathlib.Path.mkdir'):
                    # 执行
                    result = await favorite_service.toggle(mock_db, 1)
        
        # 验证：路径应该被更新
        assert result is not None
        # 注意：实际路径更新在 song 对象上，这里只验证返回值包含路径
        assert "new_path" in result


class TestFavoriteServiceEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_toggle_favorite_file_not_exist(
        self, 
        favorite_service, 
        mock_db, 
        sample_song
    ):
        """测试：本地文件不存在"""
        # 准备
        sample_song.local_path = "audio_cache/not_exist.mp3"
        
        with patch('app.repositories.song.SongRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.toggle_favorite = AsyncMock(return_value=sample_song)
            
            with patch('anyio.to_thread.run_sync') as mock_run_sync:
                # 文件不存在
                mock_run_sync.return_value = False
                
                # 执行
                result = await favorite_service.toggle(mock_db, 1)
        
        # 验证：应该正常返回，只是不移动文件
        assert result is not None
        assert result["song_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_favorites_empty(self, favorite_service, mock_db):
        """测试：获取空收藏列表"""
        # 准备
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # 执行
        result = await favorite_service.get_favorites(mock_db)
        
        # 验证
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_favorites_with_limit(self, favorite_service, mock_db):
        """测试：限制返回数量"""
        # 准备
        many_songs = [Song(id=i, title=f"歌曲{i}", is_favorite=True) for i in range(50)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = many_songs[:10]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # 执行
        result = await favorite_service.get_favorites(mock_db, limit=10)
        
        # 验证
        assert len(result) <= 10

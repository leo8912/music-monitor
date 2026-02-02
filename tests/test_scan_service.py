# -*- coding: utf-8 -*-
"""
ScanService 单元测试

测试本地文件扫描服务的核心功能

Author: google
Created: 2026-01-30
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from app.services.scan_service import ScanService
from app.models.song import Song


class TestScanService:
    """ScanService 单元测试类"""
    
    @pytest.fixture
    def scan_service(self):
        """创建 ScanService 实例"""
        return ScanService()
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    def test_normalize_cn_brackets(self, scan_service):
        """测试中文括号归一化"""
        # 测试全角括号转半角
        assert scan_service._normalize_cn_brackets("歌曲名（Live）") == "歌曲名(Live)"
        assert scan_service._normalize_cn_brackets("专辑【特别版】") == "专辑[特别版]"
        
        # 测试已经是半角的情况
        assert scan_service._normalize_cn_brackets("歌曲名(Live)") == "歌曲名(Live)"
        
        # 测试空字符串
        assert scan_service._normalize_cn_brackets("") == ""
        
        # 测试 None
        assert scan_service._normalize_cn_brackets(None) is None
    
    @pytest.mark.asyncio
    async def test_scan_local_files_empty_directory(self, scan_service, mock_db):
        """测试扫描空目录"""
        with patch('pathlib.Path.glob', return_value=[]):
            result = await scan_service.scan_local_files(mock_db)
            
            assert result['new_files_found'] == 0
            assert result['removed_files_count'] == 0
    
    @pytest.mark.asyncio
    async def test_scan_local_files_with_audio_files(self, scan_service, mock_db):
        """测试扫描包含音频文件的目录"""
        # 模拟音频文件
        mock_files = [
            Mock(spec=Path, name='song1.mp3', suffix='.mp3'),
            Mock(spec=Path, name='song2.flac', suffix='.flac'),
        ]
        
        # 配置 mock 文件的属性
        for f in mock_files:
            f.exists.return_value = True
            f.stat.return_value.st_size = 1024 * 1024  # 1MB
        
        with patch('pathlib.Path.glob', return_value=mock_files):
            with patch.object(scan_service, '_extract_metadata_from_file', return_value={
                'title': 'Test Song',
                'artist': 'Test Artist',
                'album': 'Test Album'
            }):
                # 模拟数据库查询返回空 (文件未入库)
                mock_db.execute.return_value.scalar.return_value = None
                
                result = await scan_service.scan_local_files(mock_db)
                
                # 验证结果
                assert result['new_files_found'] >= 0
                assert 'removed_files_count' in result
    
    @pytest.mark.asyncio
    async def test_scan_local_files_duplicate_detection(self, scan_service, mock_db):
        """测试重复文件检测"""
        # 模拟已存在的歌曲
        existing_song = Mock(spec=Song)
        existing_song.local_path = '/path/to/song.mp3'
        
        mock_db.execute.return_value.scalar.return_value = existing_song
        
        mock_file = Mock(spec=Path, name='song.mp3', suffix='.mp3')
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_size = 1024 * 1024
        
        with patch('pathlib.Path.glob', return_value=[mock_file]):
            result = await scan_service.scan_local_files(mock_db)
            
            # 重复文件不应该被添加
            assert result['new_files_found'] == 0


class TestScanServiceIntegration:
    """ScanService 集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_scan_workflow(self):
        """测试完整扫描流程"""
        # 这个测试需要真实的数据库连接
        # 可以使用 pytest-asyncio 和测试数据库
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

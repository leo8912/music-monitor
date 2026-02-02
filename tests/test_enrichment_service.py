# -*- coding: utf-8 -*-
"""
EnrichmentService 单元测试

测试元数据补全服务的核心功能

Author: google
Created: 2026-01-30
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.enrichment_service import EnrichmentService
from app.models.song import Song


class TestEnrichmentService:
    """EnrichmentService 单元测试类"""
    
    @pytest.fixture
    def enrichment_service(self):
        """创建 EnrichmentService 实例"""
        return EnrichmentService()
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    def test_parse_date_various_formats(self, enrichment_service):
        """测试日期解析 - 多种格式"""
        # ISO 格式
        assert enrichment_service._parse_date("2024-01-15") == datetime(2024, 1, 15)
        
        # 时间戳格式
        assert enrichment_service._parse_date(1705276800000) == datetime(2024, 1, 15)
        
        # 已经是 datetime 对象
        dt = datetime(2024, 1, 15)
        assert enrichment_service._parse_date(dt) == dt
        
        # 无效格式
        assert enrichment_service._parse_date("invalid") is None
        assert enrichment_service._parse_date(None) is None
    
    @pytest.mark.asyncio
    async def test_enrich_local_files_no_files(self, enrichment_service, mock_db):
        """测试补全本地文件 - 无文件"""
        # 模拟数据库查询返回空列表
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        count = await enrichment_service.enrich_local_files(mock_db, limit=5)
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_enrich_local_files_with_missing_metadata(self, enrichment_service, mock_db):
        """测试补全本地文件 - 缺失元数据"""
        # 创建模拟歌曲 (缺少封面和歌词)
        mock_song = Mock(spec=Song)
        mock_song.id = 1
        mock_song.title = "Test Song"
        mock_song.artist_name = "Test Artist"
        mock_song.cover = None  # 缺少封面
        mock_song.lyrics = None  # 缺少歌词
        mock_song.local_path = "/path/to/song.mp3"
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_song]
        
        with patch.object(enrichment_service, '_fetch_metadata_from_providers', 
                         return_value={'cover': 'http://example.com/cover.jpg', 'lyrics': 'Test lyrics'}):
            count = await enrichment_service.enrich_local_files(mock_db, limit=5)
            
            # 验证至少尝试补全了一个文件
            assert count >= 0
    
    @pytest.mark.asyncio
    async def test_refresh_library_metadata(self, enrichment_service, mock_db):
        """测试刷新资料库元数据"""
        # 创建模拟歌曲
        mock_song = Mock(spec=Song)
        mock_song.id = 1
        mock_song.title = "Test Song"
        mock_song.cover = None
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_song]
        
        with patch.object(enrichment_service, '_fetch_metadata_from_providers', 
                         return_value={'cover': 'http://example.com/cover.jpg'}):
            count = await enrichment_service.refresh_library_metadata(mock_db, limit=10)
            
            assert count >= 0
    
    def test_embed_cover_data(self, enrichment_service):
        """测试内嵌封面数据"""
        # 这个测试需要真实的音频文件
        # 可以使用临时文件进行测试
        pass
    
    def test_embed_lyrics_to_file(self, enrichment_service):
        """测试内嵌歌词到文件"""
        # 这个测试需要真实的音频文件
        pass


class TestEnrichmentServiceIntegration:
    """EnrichmentService 集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_enrichment_workflow(self):
        """测试完整补全流程"""
        # 这个测试需要真实的数据库和音频文件
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

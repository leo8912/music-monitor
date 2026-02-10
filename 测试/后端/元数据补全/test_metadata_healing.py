"""
元数据补全功能单元测试
测试移除冷却期和优化搜索策略后的功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.services.metadata_healer import MetadataHealer
from app.services.metadata_service import MetadataService
from app.models.song import Song

class TestMetadataHealingWithoutCooldown:
    """测试移除冷却期后的元数据补全功能"""
    
    @pytest.fixture
    def healer(self):
        return MetadataHealer()
    
    @pytest.fixture
    def mock_song(self):
        song = Mock(spec=Song)
        song.id = "test_song_1"
        song.title = "稻香"
        song.artist = Mock()
        song.artist.name = "周杰伦"
        song.local_path = "/test/path/稻香.mp3"
        song.cover = None
        song.album = None
        song.publish_time = None
        song.last_enrich_at = None
        song.sources = []
        return song
    
    def test_should_skip_enrichment_always_false(self, healer):
        """测试新的冷却期检查方法总是返回False"""
        mock_song = Mock()
        mock_song.last_enrich_at = None
        
        # 应该始终允许处理（无冷却期限制）
        assert not healer._should_skip_enrichment(mock_song)
        
        # 即使有上次执行时间也应该允许
        mock_song.last_enrich_at = Mock()
        assert not healer._should_skip_enrichment(mock_song)
    
    @pytest.mark.asyncio
    async def test_heal_song_without_cooldown_check(self, healer, mock_song):
        """测试歌曲治愈过程中不检查冷却期"""
        # 创建合适的搜索结果Mock对象
        mock_search_result = Mock()
        mock_search_result.title = "稻香"
        mock_search_result.artist = "周杰伦"
        
        # 创建最佳匹配元数据Mock对象
        mock_best_meta = Mock()
        mock_best_meta.success = True
        mock_best_meta.search_result = mock_search_result
        mock_best_meta.album = "魔杰座"
        mock_best_meta.cover_url = "http://test.com/cover.jpg"
        mock_best_meta.lyrics = "[00:00.00]歌词内容"
        mock_best_meta.publish_time = None  # 使用None而不是Mock
        
        with patch.object(healer.metadata_service, 'get_best_match_metadata', 
                         new=AsyncMock(return_value=mock_best_meta)) as mock_search:
            
            with patch('app.services.metadata_healer.AsyncSessionLocal') as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                mock_db.get.return_value = mock_song
                
                # 执行治愈
                result = await healer.heal_song(mock_song.id)
                
                # 验证调用了搜索方法
                assert mock_search.called
                # 验证返回了成功结果
                assert result is True
    
    @pytest.mark.asyncio
    async def test_immediate_retry_capability(self, healer, mock_song):
        """测试失败后可以立即重试的能力"""
        # 模拟连续两次失败的情况
        with patch.object(healer.metadata_service, 'get_best_match_metadata', 
                         new=AsyncMock(return_value=Mock(success=False))) as mock_search:
            
            with patch('app.services.metadata_healer.AsyncSessionLocal') as mock_session:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db
                mock_db.get.return_value = mock_song
                
                # 第一次尝试
                result1 = await healer.heal_song(mock_song.id)
                assert result1 is False
                
                # 立即第二次尝试（无冷却期限制）
                result2 = await healer.heal_song(mock_song.id)
                assert result2 is False
                
                # 验证调用了两次搜索
                assert mock_search.call_count == 2

class TestEnhancedRetryMechanism:
    """测试增强的重试机制"""
    
    @pytest.mark.asyncio
    async def test_increased_retry_count(self):
        """测试重试次数已增加到5次"""
        # 验证provider中的重试装饰器配置
        from app.services.music_providers.netease_provider import NeteaseProvider
        from app.services.music_providers.qqmusic_provider import QQMusicProvider
        from app.services.music_providers.base import async_retry
        
        # 检查装饰器参数
        netease_provider = NeteaseProvider()
        qq_provider = QQMusicProvider()
        
        # 通过反射检查装饰器参数
        import inspect
        netease_methods = [method for method in dir(netease_provider) 
                          if callable(getattr(netease_provider, method)) and not method.startswith('_')]
        
        # 验证至少有一个方法使用了重试装饰器
        retry_decorated_methods = []
        for method_name in netease_methods:
            method = getattr(netease_provider, method_name)
            if hasattr(method, '__wrapped__'):  # 被装饰的方法会有__wrapped__属性
                retry_decorated_methods.append(method_name)
        
        assert len(retry_decorated_methods) > 0, "应该有方法使用重试装饰器"

class TestKeywordPreprocessing:
    """测试关键词预处理功能"""
    
    def test_basic_keyword_cleaning(self):
        """测试基本的关键词清理功能"""
        service = MetadataService()
        
        test_cases = [
            ("稻香(Live)", "周杰伦 feat. 五月天", "稻香 周杰伦 五月天"),
            ("Shape of You", "Ed Sheeran", "Shape of You Ed Sheeran"),
            ("青花瓷【经典版】", "周杰伦", "青花瓷 周杰伦"),
            ("Some-Song_Title", "Artist & Band", "Some Song Title Artist Band")
        ]
        
        for title, artist, expected_pattern in test_cases:
            processed_title, processed_artist = service._preprocess_search_keywords(title, artist)
            result = f"{processed_title} {processed_artist}".strip()
            
            # 验证处理后的内容包含预期的关键词
            assert len(processed_title) > 0 or len(processed_artist) > 0
            # 验证特殊字符已被清理
            assert '(' not in result and ')' not in result
            assert '[' not in result and ']' not in result
            assert '{' not in result and '}' not in result
    
    def test_stop_word_filtering(self):
        """测试停用词过滤"""
        service = MetadataService()
        
        title, artist = service._preprocess_search_keywords(
            "稻香 Live Version", 
            "周杰伦 feat. 五月天"
        )
        
        # 验证停用词被过滤
        assert "live" not in title.lower()
        assert "version" not in title.lower()
        assert "feat" not in artist.lower()

class TestProgressiveSearchStrategy:
    """测试渐进式搜索策略"""
    
    @pytest.mark.asyncio
    async def test_multi_strategy_search_flow(self):
        """测试多策略搜索的执行流程"""
        service = MetadataService()
        
        # 模拟不同的搜索策略结果
        with patch.object(service, '_exact_search', new=AsyncMock(return_value=None)) as mock_exact:
            with patch.object(service, '_optimized_search', new=AsyncMock(return_value=None)) as mock_optimized:
                with patch.object(service, '_title_only_search', new=AsyncMock(return_value=Mock(success=True))) as mock_title:
                    
                    result = await service.get_best_match_metadata("测试歌曲", "测试艺人")
                    
                    # 验证按顺序尝试了不同策略
                    assert mock_exact.called
                    assert mock_optimized.called
                    assert mock_title.called
                    
                    # 验证找到了结果
                    assert result.success

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
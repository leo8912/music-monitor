import pytest
import pytest_asyncio
from app.services.metadata_service import MetadataService
from app.services.smart_merger import SongMetadata

@pytest.mark.asyncio
async def test_get_best_match_metadata_returns_object():
    """验证 get_best_match_metadata 返回 SongMetadata 对象而不是 dict"""
    service = MetadataService()
    
    # 我们 mock 内部 provider 避免真实网络请求
    # 这里主要测试接口定义是否存在和返回类型
    try:
        # Mocking provider behavior would be ideal, but for the "Red" phase, 
        # we expect the method itself might not exist or not return the right type yet.
        # Calling with a dummy query
        result = await service.get_best_match_metadata("Test Title", "Test Artist")
        
        assert isinstance(result, SongMetadata)
        assert result.confidence >= 0.0
    except AttributeError:
        pytest.fail("MetadataService has no method 'get_best_match_metadata'")
    except Exception as e:
        # If it raises NotImplementedError or similar, that's fine for Red phase, 
        # but we want to assert it fails if not implemented.
        pytest.fail(f"Execution failed: {e}")

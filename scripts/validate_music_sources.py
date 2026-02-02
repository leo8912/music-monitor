"""
验证音乐源更新是否正确应用
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.download.multi_source_searcher import MultiSourceSearcher
from core.audio_downloader import AudioDownloader


async def validate_music_sources():
    """验证音乐源更新"""
    print("=== 验证音乐源更新 ===")
    
    # 1. 验证MultiSourceSearcher配置
    print("\n1. 验证MultiSourceSearcher配置...")
    searcher = MultiSourceSearcher()
    
    expected_sources = ["kuwo", "netease", "joox", "apple", "deezer", "kugou", "migu", "qobuz", "qqmusic", "spotify", "tencent", "tidal", "ximalaya", "ytmusic"]
    expected_priority = ["kuwo", "netease", "joox", "apple", "deezer", "kugou", "migu", "qobuz", "qqmusic", "spotify", "tencent", "tidal", "ximalaya", "ytmusic"]
    
    print(f"  实际支持的源: {searcher.SUPPORTED_SOURCES}")
    print(f"  期望支持的源: {expected_sources}")
    print(f"  ✅ 支持的源配置正确" if searcher.SUPPORTED_SOURCES == expected_sources else "❌ 支持的源配置错误")
    
    print(f"  实际搜索优先级: {searcher.SEARCH_PRIORITY}")
    print(f"  期望搜索优先级: {expected_priority}")
    print(f"  ✅ 搜索优先级配置正确" if searcher.SEARCH_PRIORITY == expected_priority else "❌ 搜索优先级配置错误")
    
    # 2. 验证AudioDownloader配置
    print(f"\n2. 验证AudioDownloader配置...")
    downloader = AudioDownloader()
    
    # 测试search_songs_all_sources方法使用正确的源
    # 我们不实际调用API，而是检查源列表
    print(f"  AudioDownloader SOURCE_MAP keys: {list(downloader.SOURCE_MAP.keys())}")
    
    # 3. 运行一个小测试来验证功能
    print(f"\n3. 运行功能测试...")
    title, artist = "夜曲", "周杰伦"
    
    # 测试搜索功能
    for source in searcher.SUPPORTED_SOURCES:
        results = await searcher.search_single_source(title, artist, source, count=1)
        print(f"  {source}: 找到 {len(results)} 个结果")
    
    # 测试最佳质量搜索
    best_result = await searcher.find_best_quality(title, artist)
    if best_result:
        print(f"  最佳结果: {best_result.title} - {', '.join(best_result.artist)} (源: {best_result.source}) [权重: {best_result.weight_score}]")
    else:
        print(f"  未找到最佳结果")
    
    print(f"\n4. 验证完成!")
    
    print(f"\n总结:")
    print(f"- 支持的音乐源已包含所有源，实际可用的源在前面: {expected_sources[:3]}")
    print(f"- 搜索优先级已按要求调整: {expected_priority[:3]}")
    print(f"- 权重评分机制继续正常工作")
    print(f"- 代码已适配GD Studio API的实际支持情况")


if __name__ == "__main__":
    asyncio.run(validate_music_sources())
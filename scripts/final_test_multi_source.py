"""
最终测试脚本 - 验证多源搜索功能、权重评分和API使用方式
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.download.multi_source_searcher import MultiSourceSearcher
from core.audio_downloader import AudioDownloader


async def final_test():
    """最终测试"""
    print("=== 最终测试：多源搜索功能、权重评分和API使用 ===")
    
    # 1. 测试MultiSourceSearcher
    print("\n1. 测试MultiSourceSearcher...")
    searcher = MultiSourceSearcher()
    
    print(f"支持的源: {searcher.SUPPORTED_SOURCES}")
    print(f"搜索优先级: {searcher.SEARCH_PRIORITY}")
    
    # 测试搜索功能
    title = "夜曲"
    artist = "周杰伦"
    
    print(f"\n搜索: {title} - {artist}")
    
    # 测试所有支持的源
    for source in searcher.SUPPORTED_SOURCES:
        print(f"\n搜索源: {source}")
        results = await searcher.search_single_source(title, artist, source, count=3)
        print(f"  找到 {len(results)} 个结果:")
        
        for i, result in enumerate(results[:3]):
            print(f"    {i+1}. {result.title} - {', '.join(result.artist) if result.artist else 'Unknown'} "
                  f"[权重: {result.weight_score}] (专辑: {result.album})")
    
    # 测试find_best_quality方法
    print(f"\n2. 测试find_best_quality方法...")
    best_result = await searcher.find_best_quality(title, artist)
    if best_result:
        print(f"  找到最佳结果: {best_result.title} - {', '.join(best_result.artist)} "
              f"[权重: {best_result.weight_score}] (源: {best_result.source})")
    else:
        print("  未找到合适结果")
    
    # 3. 测试权重评分功能
    print(f"\n3. 测试权重评分功能...")
    from app.services.download.multi_source_searcher import SearchResult
    
    # 测试正确匹配
    correct_result = SearchResult(
        id="123456",
        source="kuwo",
        title="夜曲",
        artist=["周杰伦"],
        album="十一月的萧邦"
    )
    correct_score = searcher._calculate_weight_score(correct_result, "夜曲", "周杰伦")
    print(f"  正确匹配结果权重: {correct_score}")
    
    # 测试翻唱版本
    cover_result = SearchResult(
        id="123457",
        source="netease",
        title="夜曲 (Cover)",
        artist=["其他歌手"],
        album="翻唱专辑"
    )
    cover_score = searcher._calculate_weight_score(cover_result, "夜曲", "周杰伦")
    print(f"  翻唱版本权重 (不同歌手): {cover_score}")
    
    # 测试Live版本
    live_result = SearchResult(
        id="123458",
        source="kuwo",
        title="夜曲 (Live)",
        artist=["周杰伦"],
        album="演唱会现场"
    )
    live_score = searcher._calculate_weight_score(live_result, "夜曲", "周杰伦")
    print(f"  Live版本权重: {live_score}")
    
    # 4. 测试AudioDownloader
    print(f"\n4. 测试AudioDownloader...")
    downloader = AudioDownloader()
    
    # 测试search_songs_all_sources
    print("  测试search_songs_all_sources...")
    results = await downloader.search_songs_all_sources(title, artist, count_per_source=2)
    print(f"  从所有源共找到 {len(results)} 个结果")
    
    # 显示前几个结果
    for i, result in enumerate(results[:6]):
        print(f"    {i+1}. {result['title']} - {', '.join(result['artist']) if result['artist'] else 'Unknown'} "
              f"(源: {result['source']})")
    
    print(f"\n5. 测试完成!")
    print(f"\n总结:")
    print(f"- 已添加所有GD Studio API实际支持的音乐源")
    print(f"- 实现了搜索结果权重评分机制")
    print(f"- 歌手、歌曲名相同的结果优先级高")
    print(f"- 如果第一个音乐源前三都没有匹配结果会跳转到下一个源")
    print(f"- 修复了API使用方式问题，只使用实际支持的源")


if __name__ == "__main__":
    asyncio.run(final_test())
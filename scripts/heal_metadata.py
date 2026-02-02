#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
heal_metadata.py - 批量元数据修复脚本

功能:
1. 扫描数据库中所有本地歌曲
2. 使用 SmartMerger 智能判断是否需要补全
3. 调用 EnrichmentService 进行修复
4. 支持 --dry-run 预览模式

用法:
    python scripts/heal_metadata.py --dry-run        # 预览模式，不实际修改
    python scripts/heal_metadata.py --limit 50       # 最多处理 50 首
    python scripts/heal_metadata.py --artist "周杰伦"  # 只处理指定歌手
    python scripts/heal_metadata.py --force          # 强制重新处理所有歌曲

Author: google
Created: 2026-02-02
"""
import asyncio
import argparse
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.services.smart_merger import SmartMerger
from app.services.enrichment_service import EnrichmentService


async def scan_songs(limit: int = 100, artist_name: str = None) -> list:
    """扫描需要修复的歌曲"""
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(
            selectinload(Song.sources),
            selectinload(Song.artist)
        ).where(Song.local_path.isnot(None))
        
        if artist_name:
            from app.models.artist import Artist
            stmt = stmt.join(Artist).where(Artist.name == artist_name)
        
        stmt = stmt.limit(limit)
        
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        return songs


def analyze_song(song: Song) -> dict:
    """分析歌曲的元数据状态"""
    issues = []
    
    # 检查封面
    if not song.cover:
        issues.append("无封面")
    elif not song.cover.startswith('/uploads/'):
        issues.append("封面为远程URL")
    
    # 检查专辑
    if SmartMerger.is_garbage_value(song.album):
        issues.append("专辑缺失/垃圾")
    
    # 检查发布时间
    if SmartMerger.is_invalid_date(song.publish_time):
        issues.append("日期无效")
    
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist.name if song.artist else "Unknown",
        "album": song.album or "N/A",
        "cover": "OK" if song.cover and song.cover.startswith('/uploads/') else "MISS",
        "date": song.publish_time.strftime('%Y-%m-%d') if song.publish_time else "N/A",
        "issues": issues,
        "needs_fix": len(issues) > 0
    }


async def heal_songs(songs: list, dry_run: bool = True, force: bool = False):
    """修复歌曲元数据"""
    service = EnrichmentService()
    
    fixed_count = 0
    failed_count = 0
    total = len(songs)
    
    for i, song in enumerate(songs, 1):
        analysis = analyze_song(song)
        
        if not analysis["needs_fix"] and not force:
            continue
        
        if dry_run:
            print(f"[{i}/{total}] 📝 将修复: {analysis['title']} ({', '.join(analysis['issues'])})")
        else:
            try:
                updated = await service.enrich_song(song.id)
                if updated:
                    print(f"[{i}/{total}] ✅ 已修复: {analysis['title']}")
                    fixed_count += 1
                else:
                    print(f"[{i}/{total}] ⏭️ 跳过: {analysis['title']} (无需更新)")
            except Exception as e:
                print(f"[{i}/{total}] ❌ 失败: {analysis['title']} - {e}")
                failed_count += 1
    
    return fixed_count, failed_count


async def main():
    parser = argparse.ArgumentParser(description="批量元数据修复脚本")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际修改")
    parser.add_argument("--limit", type=int, default=100, help="最多处理的歌曲数量")
    parser.add_argument("--artist", type=str, help="只处理指定歌手")
    parser.add_argument("--force", action="store_true", help="强制重新处理所有歌曲")
    parser.add_argument("--list", action="store_true", help="仅列出需要修复的歌曲")
    
    args = parser.parse_args()
    
    print("\n🔧 元数据批量修复工具\n")
    
    # 扫描歌曲
    print(f"📂 正在扫描歌曲库 (limit={args.limit})...\n")
    songs = await scan_songs(limit=args.limit, artist_name=args.artist)
    
    if not songs:
        print("⚠️ 未找到任何本地歌曲")
        return
    
    # 分析
    analysis_results = [analyze_song(s) for s in songs]
    need_fix = [r for r in analysis_results if r["needs_fix"]]
    
    print(f"📊 扫描结果: 共 {len(songs)} 首歌曲, {len(need_fix)} 首需要修复\n")
    
    # 列表模式
    if args.list:
        print("-" * 80)
        print(f"{'标题':<25} {'歌手':<15} {'专辑':<15} {'封面':<6} {'日期':<12} {'问题'}")
        print("-" * 80)
        
        for r in need_fix[:50]:  # 最多显示 50 条
            issues_str = ", ".join(r["issues"])
            print(f"{r['title'][:24]:<25} {r['artist'][:14]:<15} {r['album'][:14]:<15} {r['cover']:<6} {r['date']:<12} {issues_str}")
        
        print("-" * 80)
        return
    
    # 执行修复
    if args.dry_run:
        print("⚠️ 预览模式，不会实际修改\n")
    else:
        print("🚀 开始修复...\n")
    
    fixed, failed = await heal_songs(songs, dry_run=args.dry_run, force=args.force)
    
    if not args.dry_run:
        print(f"\n✅ 修复完成: 成功 {fixed} 首, 失败 {failed} 首")


if __name__ == "__main__":
    asyncio.run(main())

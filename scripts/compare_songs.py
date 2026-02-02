from core.database import SessionLocal, MediaRecord

db = SessionLocal()

# 查询李剑青的QQ音乐歌曲
qq_songs = db.query(MediaRecord).filter(
    MediaRecord.author.contains('李剑青'),
    MediaRecord.source == 'qqmusic'
).all()

netease_songs = db.query(MediaRecord).filter(
    MediaRecord.author.contains('李剑青'),
    MediaRecord.source == 'netease'
).all()

print("=" * 60)
print("数据库中的歌曲统计")
print("=" * 60)
print(f"QQ音乐: {len(qq_songs)} 首")
print(f"网易云: {len(netease_songs)} 首")
print(f"总计: {len(qq_songs) + len(netease_songs)} 首\n")

print("=" * 60)
print("QQ音乐歌曲列表（前20首）")
print("=" * 60)
for i, song in enumerate(qq_songs[:20], 1):
    print(f"{i:2d}. {song.title[:50]}")
    print(f"    ID: {song.media_id} | 发布: {song.publish_time.strftime('%Y-%m-%d') if song.publish_time else '未知'}")

if len(qq_songs) > 20:
    print(f"\n... 还有 {len(qq_songs) - 20} 首")

db.close()

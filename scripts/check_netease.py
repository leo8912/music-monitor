from core.database import SessionLocal, MediaRecord

db = SessionLocal()

# 查询李剑青的所有网易云歌曲，看看是否有类似标题
netease_songs = db.query(MediaRecord).filter(
    MediaRecord.author.contains('李剑青'),
    MediaRecord.source == 'netease'
).all()

print(f"网易云共找到 {len(netease_songs)} 首歌曲\n")

# 查找可能匹配图片中标题的歌曲
keywords = ["为你守", "勿", "矿工"]

for kw in keywords:
    matching = [s for s in netease_songs if kw in s.title]
    if matching:
        for song in matching:
            print(f"【网易云】{song.title}")
            print(f"  封面: {song.cover[:60] if song.cover else '❌ 无'}")
            print(f"  专辑: {song.album if song.album else '❌ 无'}")
            print(f"  发布: {song.publish_time}")
            print()

db.close()

from core.database import SessionLocal, MediaRecord

db = SessionLocal()

# 查询图片中显示有问题的歌曲
problem_titles = ["为你守在灯火下", "勿勿", "乐人", "女矿工挂"]

print("=" * 60)
print("查询问题歌曲的数据库信息")
print("=" * 60)

for title in problem_titles:
    songs = db.query(MediaRecord).filter(MediaRecord.title.contains(title)).all()
    if songs:
        for song in songs:
            print(f"\n【{song.source.upper()}】{song.title}")
            print(f"  媒体ID: {song.media_id}")
            print(f"  封面URL: {song.cover[:80] if song.cover else '❌ 无'}")
            print(f"  专辑: {song.album if song.album else '❌ 无'}")
            print(f"  发布时间: {song.publish_time}")
            print(f"  作者: {song.author}")
    else:
        print(f"\n未找到: {title}")

db.close()

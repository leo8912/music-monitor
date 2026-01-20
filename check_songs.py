from core.database import SessionLocal, MediaRecord

db = SessionLocal()

# 查询李剑青的歌曲
songs = db.query(MediaRecord).filter(MediaRecord.author.contains('李剑青')).order_by(MediaRecord.publish_time.desc()).limit(10).all()

print(f"找到 {len(songs)} 首歌曲\n")

for i, s in enumerate(songs[:10], 1):
    print(f"{i}. 【{s.source}】{s.title[:40]}")
    print(f"   封面: {'有 (' + s.cover[:50] + '...)' if s.cover else '❌ 无'}")
    print(f"   专辑: {s.album if s.album else '❌ 无'}")
    print(f"   发布: {s.publish_time.strftime('%Y-%m-%d')if s.publish_time else '❌ 无'}")
    print()

db.close()

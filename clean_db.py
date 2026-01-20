from core.database import SessionLocal, MediaRecord

def clean_dirty_data():
    db = SessionLocal()
    
    print("开始清理QQ音乐脏数据...")
    
    # 查找QQ音乐来源且没有专辑信息的记录
    # 注意：数据库中album可能存为NULL或空字符串
    # 也可以根据cover为空来辅助判断，因为这些歌也无法获取封面
    
    dirty_songs = db.query(MediaRecord).filter(
        MediaRecord.source == 'qqmusic',
        (MediaRecord.album == None) | (MediaRecord.album == '') | (MediaRecord.album == '-')
    ).all()
    
    count = len(dirty_songs)
    print(f"找到 {count} 条脏数据")
    
    if count > 0:
        for song in dirty_songs:
            print(f"删除: {song.title} (ID: {song.media_id})")
            db.delete(song)
        
        db.commit()
        print("✅ 清理完成！")
    else:
        print("没有发现脏数据。")
        
    db.close()

if __name__ == "__main__":
    clean_dirty_data()

"""
扫描本地音频文件并同步到数据库
"""
import os
from datetime import datetime
from core.database import SessionLocal, MediaRecord

def scan_and_sync():
    """扫描 audio_cache 和 favorites 目录，将文件同步到数据库"""
    print("\n" + "="*70)
    print(" 🔄 音频文件同步工具")
    print("="*70)
    
    db = SessionLocal()
    try:
        # 扫描目录
        dirs_to_scan = [
            ('audio_cache', 'audio_cache'),
            ('favorites', 'favorites')
        ]
        
        all_files = []
        for dir_name, dir_path in dirs_to_scan:
            if not os.path.exists(dir_path):
                continue
            
            files = [f for f in os.listdir(dir_path) if f.endswith(('.flac', '.mp3', '.m4a'))]
            print(f"\n📁 {dir_name}: 找到 {len(files)} 个音频文件")
            
            for filename in files:
                full_path = os.path.join(dir_path, filename)
                all_files.append((filename, full_path, dir_name))
        
        print(f"\n总计: {len(all_files)} 个音频文件")
        
        # 解析文件名并创建/更新数据库记录
        print("\n" + "="*70)
        print(" 🔍 解析文件并同步数据库...")
        print("="*70)
        
        added = 0
        updated = 0
        skipped = 0
        
        for filename, full_path, source_dir in all_files:
            # 解析文件名: "歌手 - 歌名.flac"
            if ' - ' not in filename:
                print(f"⚠️  跳过 (格式不正确): {filename}")
                skipped += 1
                continue
            
            artist, title_with_ext = filename.split(' - ', 1)
            title = title_with_ext.rsplit('.', 1)[0]
            
            # 检查数据库中是否已有此记录
            existing = db.query(MediaRecord).filter(
                MediaRecord.title == title,
                MediaRecord.author == artist
            ).first()
            
            if existing:
                # 更新本地路径
                if existing.local_audio_path != full_path:
                    existing.local_audio_path = full_path
                    updated += 1
                    print(f"✏️  更新: {artist} - {title}")
                else:
                    skipped += 1
            else:
                # 创建新记录
                # 生成 unique_key (因为不知道来源，使用 unknown)
                unique_key = f"manual_{artist}_{title}".replace(' ', '_')
                
                new_record = MediaRecord(
                    unique_key=unique_key,
                    source='manual',  # 标记为手动添加
                    media_type='audio',
                    media_id=unique_key,
                    title=title,
                    author=artist,
                    local_audio_path=full_path,
                    publish_time=datetime.now()
                )
                
                db.add(new_record)
                added += 1
                print(f"➕ 新增: {artist} - {title}")
        
        # 提交更改
        db.commit()
        
        print("\n" + "="*70)
        print(" 📊 同步结果")
        print("="*70)
        print(f"\n新增记录: {added}")
        print(f"更新记录: {updated}")
        print(f"跳过记录: {skipped}")
        print(f"总处理文件: {len(all_files)}")
        
        # 显示同步后的数据库状态
        total_records = db.query(MediaRecord).count()
        has_local = db.query(MediaRecord).filter(MediaRecord.local_audio_path.isnot(None)).count()
        
        print(f"\n数据库总记录数: {total_records}")
        print(f"有本地文件的记录: {has_local}")
        
        print("\n✅ 同步完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    confirm = input("\n⚠️  此操作将扫描本地文件并同步到数据库，是否继续? (y/n): ").strip().lower()
    if confirm == 'y':
        scan_and_sync()
    else:
        print("❌ 已取消")

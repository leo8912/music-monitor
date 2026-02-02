import asyncio
import sqlite3
from loguru import logger

async def cleanup_duplicates():
    """
    清理数据库中的重复歌曲记录。
    逻辑：发现具有相同 (source, source_id) 但属于不同 Song 的记录，并将它们合并。
    """
    db_path = 'music_monitor.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("🔍 正在检查重复的 SongSource...")
    
    # 1. 查找重复的 (source, source_id)
    cursor.execute('''
        SELECT source, source_id, COUNT(DISTINCT song_id) as song_count
        FROM song_sources
        WHERE source != 'local'
        GROUP BY source, source_id
        HAVING song_count > 1
    ''')
    duplicates = cursor.fetchall()
    
    if not duplicates:
        logger.info("✅ 未发现重复歌曲源。")
        conn.close()
        return

    logger.info(f"发现 {len(duplicates)} 组重复歌曲源。")

    for source, source_id, count in duplicates:
        logger.info(f"🔄 处理重复源: {source}:{source_id} (关联歌曲数: {count})")
        
        # 获取关联的所有 song_id
        cursor.execute('''
            SELECT DISTINCT song_id FROM song_sources
            WHERE source = ? AND source_id = ?
        ''', (source, source_id))
        song_ids = [row[0] for row in cursor.fetchall()]
        
        # 选取第一个作为 Master
        master_id = song_ids[0]
        slave_ids = song_ids[1:]
        
        logger.info(f"  🏆 Master Song ID: {master_id}, Slaves: {slave_ids}")
        
        # A. 将 Slave 的所有 Source 迁移到 Master (如果 Master 没有该源)
        for slave_id in slave_ids:
            # 检查 Slave 有哪些 Source 是 Master 没有的
            cursor.execute('SELECT source, source_id, cover, duration, url, data_json FROM song_sources WHERE song_id = ?', (slave_id,))
            slave_sources = cursor.fetchall()
            
            for s_src, s_sid, s_cov, s_dur, s_url, s_json in slave_sources:
                # 检查 Master 是否已有该源
                cursor.execute('SELECT id FROM song_sources WHERE song_id = ? AND source = ? AND source_id = ?', (master_id, s_src, s_sid))
                if not cursor.fetchone():
                    logger.info(f"  🔗 迁移源 {s_src}:{s_sid} 从 {slave_id} 到 {master_id}")
                    cursor.execute('''
                        INSERT INTO song_sources (song_id, source, source_id, cover, duration, url, data_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (master_id, s_src, s_sid, s_cov, s_dur, s_url, s_json))
            
            # B. 迁移本地路径 (如果 Master 没有)
            cursor.execute('SELECT local_path, status, is_favorite FROM songs WHERE id = ?', (slave_id,))
            slave_song = cursor.fetchone()
            if slave_song:
                s_path, s_status, s_fav = slave_song
                cursor.execute('SELECT local_path, status, is_favorite FROM songs WHERE id = ?', (master_id,))
                master_song = cursor.fetchone()
                
                updates = []
                params = []
                if master_song and not master_song[0] and s_path:
                    logger.info(f"  📂 迁移本地路径: {s_path}")
                    updates.append("local_path = ?, status = 'DOWNLOADED'")
                    params.extend([s_path])
                
                if s_fav:
                    updates.append("is_favorite = 1")
                
                if updates:
                    sql = f"UPDATE songs SET {', '.join(updates)} WHERE id = ?"
                    params.append(master_id)
                    cursor.execute(sql, tuple(params))

        # C. 删除 Slave 的 Song 记录及其 Source
        for slave_id in slave_ids:
            cursor.execute('DELETE FROM song_sources WHERE song_id = ?', (slave_id,))
            cursor.execute('DELETE FROM songs WHERE id = ?', (slave_id,))
            logger.info(f"  🗑️ 已删除冗余歌曲 ID: {slave_id}")

    conn.commit()
    logger.info("✅ 数据库清理完成。")
    conn.close()

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())

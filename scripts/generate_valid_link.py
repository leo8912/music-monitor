"""
生成有效测试链接（已修复编码问题）
"""
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params
from urllib.parse import quote
import webbrowser
import os

def generate_link():
    db = SessionLocal()
    try:
        # 1. 查找收藏夹中的歌曲
        target_title = "我不要原谅你"
        record = db.query(MediaRecord).filter(MediaRecord.title.contains(target_title)).first()
        
        if not record:
            print(f"❌ 未找到歌曲: {target_title}")
            # 尝试找任意有文件的歌曲
            record = db.query(MediaRecord).filter(MediaRecord.local_audio_path.isnot(None)).first()
            if not record:
                print("❌ 数据库中没有可播放的歌曲")
                return
            print(f"⚠️ 自动切换到已有歌曲: {record.title}")

        print("\n" + "="*60)
        print(" 🎵 歌曲详情")
        print("="*60)
        print(f"标题: {record.title}")
        print(f"歌手: {record.author}")
        print(f"Key : {record.unique_key}")
        print(f"文件: {record.local_audio_path}")

        # 2. 生成签名
        sign_params = generate_signed_url_params(record.unique_key)
        
        # 3. 构建链接 (关键修复：对 id 进行 URL 编码)
        # 之前的错误写法: ...?id={sign_params['id']}...
        # 正确的写法:   ...?id={quote(sign_params['id'])}...
        
        base_url = "http://localhost:8000"
        encoded_id = quote(sign_params['id'])
        
        magic_url = f"{base_url}/#/mobile/play?id={encoded_id}&sign={sign_params['sign']}&expires={sign_params['expires']}"
        
        print("\n" + "="*60)
        print(" 🔗 移动端播放测试链接")
        print("="*60)
        print(f"\n{magic_url}\n")
        
        print(f"Expires: {sign_params['expires']}")
        
        # 4. 自动打开
        print("\n" + "="*60)
        print(" 🚀 正在打开浏览器...")
        print("="*60)
        webbrowser.open(magic_url)
        print("已打开！请按 F12 切换到手机模式查看效果。")

    finally:
        db.close()

if __name__ == "__main__":
    generate_link()

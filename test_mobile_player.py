"""
快速生成任素汐-困的移动端播放链接
"""
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params

db = SessionLocal()
try:
    # 查找任素汐的歌曲
    record = db.query(MediaRecord).filter(MediaRecord.title.contains('困')).first()
    
    if not record:
        print("❌ 未找到歌曲")
    else:
        print("\n" + "="*70)
        print(" 🎵 找到的歌曲")
        print("="*70)
        print(f"\n标题: {record.title}")
        print(f"歌手: {record.author}")
        print(f"unique_key: {record.unique_key}")
        print(f"本地文件: {record.local_audio_path}")
        
        # 生成签名链接
        sign_params = generate_signed_url_params(record.unique_key)
        base_url = "http://localhost:18001"
        magic_url = f"{base_url}/#/mobile/play?id={sign_params['id']}&sign={sign_params['sign']}&expires={sign_params['expires']}"
        
        print("\n" + "="*70)
        print(" 📱 移动端播放链接")
        print("="*70)
        print(f"\n{magic_url}\n")
        
        print("="*70)
        print(" 🖥️  浏览器测试步骤")
        print("="*70)
        print("\n1. 复制上面的链接")
        print("2. 在浏览器中粘贴并打开")
        print("3. 按 F12 打开开发者工具")
        print("4. 按 Ctrl+Shift+M 切换手机模式")
        print("5. 选择 'iPhone 12 Pro' 或其他手机")
        print("6. 刷新页面 (F5)")
        print("\n💡 也可以直接访问，播放器会自适应桌面浏览器")
        
        # 自动在浏览器打开
        print("\n" + "="*70)
        import webbrowser
        webbrowser.open(magic_url)
        print("✅ 已在默认浏览器中打开链接")
        print("💡 记得切换到手机模式查看最佳效果！")
        
finally:
    db.close()

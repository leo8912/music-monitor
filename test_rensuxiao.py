"""
为任素汐-困生成移动端播放链接（正确端口：8000）
"""
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params
import webbrowser

db = SessionLocal()
try:
    # 查找任素汐-困
    record = db.query(MediaRecord).filter(
        MediaRecord.title == '困',
        MediaRecord.author == '任素汐'
    ).first()
    
    if not record:
        print("❌ 未找到'任素汐 - 困'")
        exit(1)
    
    print("\n" + "="*70)
    print(" 🎵 歌曲信息")
    print("="*70)
    print(f"\n标题: {record.title}")
    print(f"歌手: {record.author}")
    print(f"unique_key: {record.unique_key}")
    print(f"本地文件: {record.local_audio_path}")
    
    # 生成签名链接（使用正确的端口 8000）
    sign_params = generate_signed_url_params(record.unique_key)
    base_url = "http://localhost:8000"  # ✅ 正确的端口
    magic_url = f"{base_url}/#/mobile/play?id={sign_params['id']}&sign={sign_params['sign']}&expires={sign_params['expires']}"
    
    print("\n" + "="*70)
    print(" 📱 移动端播放链接（端口 8000）")
    print("="*70)
    print(f"\n{magic_url}\n")
    
    print("签名参数:")
    print(f"  id: {sign_params['id']}")
    print(f"  sign: {sign_params['sign'][:30]}...")
    print(f"  expires: {sign_params['expires']} (72小时有效)")
    
    print("\n" + "="*70)
    print(" 🖥️  浏览器测试步骤")
    print("="*70)
    print("\n1. 复制上面的链接到浏览器")
    print("2. 按 F12 打开开发者工具")
    print("3. 按 Ctrl+Shift+M 切换手机模式")
    print("4. 选择 'iPhone 12 Pro'")
    print("5. 刷新页面 (F5)")
    
    print("\n💡 或者直接在桌面浏览器访问也可以，播放器会自适应")
    
    # 自动在浏览器打开
    print("\n" + "="*70)
    webbrowser.open(magic_url)
    print("✅ 已在默认浏览器中打开链接")
    
finally:
    db.close()

"""
最终版本：生成并测试任素汐-困的播放链接
"""
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params, verify_signature
from urllib.parse import quote
import webbrowser

db = SessionLocal()
try:
    # 查找歌曲
    record = db.query(MediaRecord).filter(
        MediaRecord.title == '困',
        MediaRecord.author == '任素汐'
    ).first()
    
    if not record:
        print("❌ 未找到歌曲")
        exit(1)
    
    print("\n" + "="*70)
    print(" 🎵 歌曲信息")
    print("="*70)  
    print(f"\ntitle: {record.title}")
    print(f"author: {record.author}")
    print(f"unique_key: {record.unique_key}")
    
    # 生成签名
    sign_params = generate_signed_url_params(record.unique_key)
    
    print("\n" + "="*70)
    print(" 🔐 签名参数")
    print("="*70)
    print(f"\nid: {sign_params['id']}")
    print(f"sign: {sign_params['sign']}")
    print(f"expires: {sign_params['expires']}")
    
    # 立即验证
    is_valid = verify_signature(
        sign_params['id'],
        sign_params['sign'],
        sign_params['expires']
    )
    print(f"\n签名验证: {'✅ 通过' if is_valid else '❌ 失败'}")
    
    if not is_valid:
        print("\n签名验证失败，无法继续！")
        exit(1)
    
    # 生成完整链接
    base_url = "http://localhost:8000"
    encoded_id = quote(sign_params['id'])
    
    magic_url = f"{base_url}/#/mobile/play?id={encoded_id}&sign={sign_params['sign']}&expires={sign_params['expires']}"
    
    print("\n" + "="*70)
    print(" 📱 移动端播放链接")
    print("="*70)
    print(f"\n{magic_url}\n")
    
    print("="*70)
    print(" 📋 请复制上面的链接到浏览器测试")
    print("="*70)
    print("\n浏览器测试步骤:")
    print("1. 复制上面的完整链接")
    print("2. 在浏览器中粘贴并打开")
    print("3. 按 F12 打开开发者工具")
    print("4. 按 Ctrl+Shift+M 切换手机模式")
    print("5. 选择 iPhone 12 Pro")
    print("6. 刷新页面 (F5)")
    
    print("\n💡 提示: 也可以直接访问，播放器会自适应桌面")
    
    # 自动打开
    print("\n" + "="*70)
    webbrowser.open(magic_url)
    print("✅ 已在浏览器中打开")
    
finally:
    db.close()

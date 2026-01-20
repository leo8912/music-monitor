"""
测试签名验证
"""
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params, verify_signature
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
    print(" 🔍 数据库记录")
    print("="*70)
    print(f"\ntitle: {record.title}")
    print(f"author: {record.author}")
    print(f"unique_key: {record.unique_key}")
    print(f"local_audio_path: {record.local_audio_path}")
    
    # 生成签名
    print("\n" + "="*70)
    print(" 🔐 生成签名")
    print("="*70)
    sign_params = generate_signed_url_params(record.unique_key)
    print(f"\nid: {sign_params['id']}")
    print(f"sign: {sign_params['sign']}")
    print(f"expires: {sign_params['expires']}")
    
    # 立即验证签名
    print("\n" + "="*70)
    print(" ✅ 验证签名")
    print("="*70)
    is_valid = verify_signature(
        sign_params['id'],
        sign_params['sign'],
        sign_params['expires']
    )
    print(f"\n签名是否有效: {is_valid}")
    
    if not is_valid:
        print("❌ 签名验证失败！这就是 403 错误的原因")
        exit(1)
    
    # 生成链接
    base_url = "http://localhost:8000"
    
    # 注意：URL 中的特殊字符需要编码
    from urllib.parse import quote
    encoded_id = quote(sign_params['id'])
    encoded_sign = sign_params['sign']  # sign 是 hex，不需要编码
    
    magic_url = f"{base_url}/#/mobile/play?id={encoded_id}&sign={encoded_sign}&expires={sign_params['expires']}"
    
    print("\n" + "="*70)
    print(" 📱 移动端播放链接")
    print("="*70)
    print(f"\n{magic_url}\n")
    
    print("✅ 链接已验证，签名有效！")
    
    # 自动打开
    webbrowser.open(magic_url)
    print("\n已在浏览器中打开，请按 F12 + Ctrl+Shift+M 切换手机模式")
    
finally:
    db.close()

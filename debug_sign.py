"""
调试签名验证
"""
from core.security import generate_signed_url_params, verify_signature, get_secret_key
import hmac
import hashlib

song_id = 'manual_任素汐_困'

print("=" * 70)
print(" 🔐 签名生成与验证调试")
print("="*70)

# 1. 生成签名
params = generate_signed_url_params(song_id)
print(f"\n生成参数:")
print(f"  id: {params['id']}")
print(f"  sign: {params['sign']}")
print(f"  expires: {params['expires']}")

# 2. 获取密钥
secret = get_secret_key()
print(f"\nSecret Key: {secret[:20]}...")

# 3. 手动重新计算签名（模拟 verify_signature）
data = f"{params['id']}|{params['expires']}"
print(f"\n签名数据: {data}")

expected_sign = hmac.new(
    key=secret.encode('utf-8'),
    msg=data.encode('utf-8'),
    digestmod=hashlib.sha256
).hexdigest()

print(f"\n手动计算的签名: {expected_sign}")
print(f"生成的签名:     {params['sign']}")
print(f"签名匹配: {expected_sign == params['sign']}")

# 4. 调用 verify_signature
is_valid = verify_signature(params['id'], params['sign'], params['expires'])
print(f"\nverify_signature 返回: {is_valid}")

# 5. 测试中文编码
print("\n" + "="*70)
print(" 🔍 编码测试")
print("="*70)
print(f"\nsong_id 类型: {type(song_id)}")
print(f"song_id bytes: {song_id.encode('utf-8')}")
print(f"UTF-8 编码后长度: {len(song_id.encode('utf-8'))}")

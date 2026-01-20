"""
直接测试 API 接口
"""
import requests
from core.security import generate_signed_url_params

# 生成参数
song_id = 'manual_任素汐_困'
params = generate_signed_url_params(song_id)

print("=" *70)
print(" 🔐 生成的签名参数")
print("="*70)
print(f"\nid: {params['id']}")
print(f"sign: {params['sign']}")
print(f"expires: {params['expires']}")

# 构建URL
url = f"http://localhost:8000/api/mobile/metadata"

print("\n" + "="*70)
print(" 📡 测试 API 请求")
print("="*70)
print(f"\nURL: {url}")
print(f"参数: id={params['id']}, sign={params['sign'][:20]}..., expires={params['expires']}")

try:
    # 发送请求
    response = requests.get(url, params=params)
    
    print(f"\n状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 成功！")
        data = response.json()
        print(f"\n返回数据:")
        print(f"  title: {data.get('title')}")
        print(f"  artist: {data.get('artist')}")
        print(f"  audio_url: {data.get('audio_url')}")
    else:
        print(f"❌ 失败！")
        print(f"响应: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

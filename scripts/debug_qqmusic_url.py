#!/usr/bin/env python3
"""
调试QQ音乐封面URL构造问题
"""

def debug_url_construction(source_id):
    print(f"原始source_id: '{source_id}'")
    print(f"source_id repr: {repr(source_id)}")
    print(f"source_id长度: {len(source_id)}")
    
    cleaned_source_id = source_id.strip()
    print(f"清理后source_id: '{cleaned_source_id}'")
    print(f"清理后source_id repr: {repr(cleaned_source_id)}")
    print(f"清理后长度: {len(cleaned_source_id)}")
    
    url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{cleaned_source_id}.jpg"
    print(f"构造的URL: {url}")
    print(f"URL repr: {repr(url)}")


if __name__ == "__main__":
    # 测试有问题的source_id
    debug_url_construction('002zSrPI1J0v7J')
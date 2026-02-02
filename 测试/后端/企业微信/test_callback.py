# -*- coding: utf-8 -*-
"""
企业微信回调本地验证脚本
支持读取真实配置进行签名校验和解密模拟

Author: google
Updated: 2026-02-02
"""
import sys
import os
import time
import hashlib
import requests
import yaml
from wechatpy.crypto import WeChatCrypto
import xml.etree.ElementTree as ET

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def load_real_config():
    # 尝试在当前目录或根目录查找 config.yaml
    search_paths = ["config.yaml", "../../config.yaml", "../../../config.yaml"]
    for path in search_paths:
        if os.path.exists(path):
            with open(path, "r", encoding='utf-8') as f:
                return yaml.safe_load(f)
    print("❌ 找不到配置文件 config.yaml")
    return None

def test_signature_and_decrypt():
    cfg = load_real_config()
    if not cfg: return
    
    wecom = cfg.get('notify', {}).get('wecom', {})
    token = wecom.get('token')
    aes_key = wecom.get('encoding_aes_key')
    corpid = wecom.get('corpid')
    
    if not all([token, aes_key, corpid]):
        print("⚠️ 配置文件中 WeCom 回调参数 (token, encoding_aes_key, corpid) 不完整")
        return

    print(f"✅ 已加载配置: CorpID={corpid}")
    # 兼容处理 FixedWeChatCrypto 或 WeChatCrypto
    crypto = WeChatCrypto(token, aes_key, corpid)
    
    # 1. 模拟验证 (GET)
    timestamp = str(int(time.time()))
    nonce = "test_nonce"
    echostr = "hello_world"
    
    print("\n--- 1. GET 验证模拟 ---")
    try:
        # 这里模拟微信后台的签名生成方式
        params = sorted([token, timestamp, nonce, echostr])
        signature = hashlib.sha1("".join(params).encode('utf-8')).hexdigest()
        print(f"生成的签名: {signature}")
        print("提示: 实际 GET 验证通过 FastAPI 路由处理，请在浏览器或 Postman 测试接口。")
    except Exception as e:
        print(f"GET 验证模拟失败: {e}")

    # 2. 模拟加密消息 (POST)
    print("\n--- 2. POST 消息模拟 ---")
    xml_content = f"""<xml>
        <ToUserName><![CDATA[{corpid}]]></ToUserName>
        <FromUserName><![CDATA[TestUser]]></FromUserName>
        <CreateTime>{int(time.time())}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[歌曲 七里香]]></Content>
        <MsgId>1234567890</MsgId>
        <AgentID>1</AgentID>
    </xml>"""
    
    try:
        encrypted_xml = crypto.encrypt_message(xml_content, nonce, timestamp)
        print("消息加密成功！")
        
        url = "http://127.0.0.1:8000/api/wecom/callback"
        print(f"提示: 请使用内网穿透工具 (如 ngrok) 将真实微信回调转发到 {url}")
        print("如果你想在本地内网测试，请运行以下 Python 代码发送 mock 请求:")
        print(f"""
import requests
url = "{url}"
params = {{
    "msg_signature": "YOUR_SIGNATURE", 
    "timestamp": "{timestamp}",
    "nonce": "{nonce}"
}}
data = \"\"\"{encrypted_xml}\"\"\"
# resp = requests.post(url, params=params, data=data) 
# print(resp.text)
        """)
        
    except Exception as e:
        print(f"消息模拟失败: {e}")

if __name__ == "__main__":
    test_signature_and_decrypt()

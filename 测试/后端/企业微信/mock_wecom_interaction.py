# -*- coding: utf-8 -*-
"""
企业微信本地模拟交互脚本 (内网闭环测试)
无需公网 IP，直接通过代码模拟微信服务器向本地发送加密消息。

使用方法:
1. 确保项目后端已启动 (python main.py)
2. 运行此脚本: python "测试\后端\企业微信\mock_wecom_interaction.py"

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
    search_paths = ["config.yaml", "../../config.yaml", "../../../config.yaml"]
    for path in search_paths:
        if os.path.exists(path):
            with open(path, "r", encoding='utf-8') as f:
                return yaml.safe_load(f)
    return None

def send_mock_msg(content: str, user_id: str = "TestUser"):
    cfg = load_real_config()
    if not cfg:
        print("❌ 错误: 找不到 config.yaml")
        return
        
    wecom = cfg.get('notify', {}).get('wecom', {})
    token = wecom.get('token')
    aes_key = wecom.get('encoding_aes_key')
    corpid = wecom.get('corpid')
    
    if not all([token, aes_key, corpid]):
        print("❌ 错误: config.yaml 中 WeCom 回调配置不完整")
        return

    crypto = WeChatCrypto(token, aes_key, corpid)
    timestamp = str(int(time.time()))
    nonce = "mocknonce"
    
    # 1. 构造原始 XML 消息
    xml_content = f"""<xml>
        <ToUserName><![CDATA[{corpid}]]></ToUserName>
        <FromUserName><![CDATA[{user_id}]]></FromUserName>
        <CreateTime>{timestamp}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{content}]]></Content>
        <MsgId>1234567890</MsgId>
        <AgentID>1</AgentID>
    </xml>"""
    
    # 2. 加密消息
    encrypted_xml = crypto.encrypt_message(xml_content, nonce, timestamp)
    
    # 3. 生成签名 (真正的签名计算方式)
    # 微信加密消息签名计算: token, timestamp, nonce, msg_encrypt 的字典序排序
    root = ET.fromstring(encrypted_xml)
    msg_encrypt = root.find("Encrypt").text
    
    params = sorted([token, timestamp, nonce, msg_encrypt])
    msg_signature = hashlib.sha1("".join(params).encode('utf-8')).hexdigest()
    
    # 4. 发送到本地 API
    url = "http://127.0.0.1:8000/api/wecom/callback"
    query_params = {
        "msg_signature": msg_signature,
        "timestamp": timestamp,
        "nonce": nonce
    }
    
    print(f"发送消息: '{content}'")
    try:
        resp = requests.post(url, params=query_params, data=encrypted_xml, timeout=10)
        
        if resp.status_code == 200:
            if resp.text == "success":
                print("系统响应: success (已转入后台处理)")
            else:
                # 5. 解密响应
                try:
                    # 从响应中解析出需要解密的字段
                    resp_root = ET.fromstring(resp.text)
                    resp_encrypt = resp_root.find("Encrypt").text
                    resp_sig = resp_root.find("MsgSignature").text
                    resp_time = resp_root.find("TimeStamp").text
                    resp_nonce = resp_root.find("Nonce").text
                    
                    decrypted_reply = crypto.decrypt_message(
                        resp.text, resp_sig, resp_time, resp_nonce
                    )
                    reply_root = ET.fromstring(decrypted_reply)
                    reply_content = reply_root.find("Content").text
                    print(f"系统回复:\n{reply_content}")
                except Exception as e:
                    print(f"解密响应失败: {e}")
                    print(f"原始响应内容: {resp.text}")
        else:
            print(f"❌ 请求失败: HTTP {resp.status_code}\n{resp.text}")
            
    except Exception as e:
        print(f"❌ 无法连接到本地服务: {e}")

if __name__ == "__main__":
    print("--- 企业微信本地模拟器 ---")
    print("输入 'exit' 退出\n")
    
    while True:
        text = input("请输入消息内容: ")
        if text.lower() in ['exit', 'quit']:
            break
        if not text.strip():
            continue
        send_mock_msg(text)
        print("-" * 30)

import requests
import time
import uuid
import logging
from wechatpy.crypto import WeChatCrypto
from wechatpy import create_reply
import xml.etree.cElementTree as ET
from core.config import config, load_config

# Load real config to get keys
config.update(load_config())
wecom_cfg = config.get('notify', {}).get('wecom', {})
TOKEN = wecom_cfg.get('token')
AES_KEY = wecom_cfg.get('encoding_aes_key')
CORP_ID = wecom_cfg.get('corpid')

if not TOKEN or not AES_KEY:
    print("❌ 缺少配置: wecom token 或 aes_key")
    exit(1)

crypto = WeChatCrypto(TOKEN, AES_KEY, CORP_ID)

import hashlib

def calculate_signature(token, timestamp, nonce, encrypt):
    sort_list = [token, timestamp, nonce, encrypt]
    sort_list.sort()
    sha = hashlib.sha1("".join(sort_list).encode("utf-8"))
    return sha.hexdigest()

def send_text(content):
    nonce = str(int(time.time()))
    timestamp = str(int(time.time()))
    
    # WeCom requires Encrypted XML. 
    # encrypt_message returns just the ciphertext in some versions, or XML?
    # Let's inspect what it returns.
    # Actually, wechatpy encrypt_message returns the encrypted content string (just the base64).
    # We need to wrap it.
    
    # But wait, wechatpy might return the full XML?
    # Let's trust verify logic: decrypt_message takes XML.
    
    raw_xml_for_encryption = f"""<xml>
    <ToUserName><![CDATA[{CORP_ID}]]></ToUserName>
    <FromUserName><![CDATA[UserTest]]></FromUserName>
    <CreateTime>{timestamp}</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[{content}]]></Content>
    <MsgId>{int(time.time()*1000)}</MsgId>
    <AgentID>1000002</AgentID>
    </xml>"""
    
    # Encrypt
    encrypt = crypto.encrypt_message(raw_xml_for_encryption, nonce, timestamp)
    # encrypt is the output XML string from wechatpy usually?
    # Let's check type.
    if isinstance(encrypt, bytes): encrypt = encrypt.decode('utf-8')
    
    # Wechatpy's encrypt_message returns the formatted XML usually:
    # <xml><Encrypt>...</Encrypt><MsgSignature>...</MsgSignature>...</xml>
    # If so, we need to extract the 'Encrypt' field to calculate signature for URL?
    # No, signature is calculated on the Encrypt CONTENT.
    
    # Let's assume encrypt_message returns the ciphertext string based on Attribute error 'get_signature'.
    # Because if it was full XML logic, it would handle signature.
    
    # Actually, look at wechatpy source (common knowledge to me): 
    # WeChatCrypto.encrypt_message returns the XML string.
    # Wait, does it?
    
    # To be safe, let's use a simpler approach if we rely on hashlib.
    
    # Let's try to assume it returns XML.
    # But for calculation of URL signature, we need the Encrypt content.
    
    # Manual approach:
    # 1. Encrypt content
    # 2. Build XML
    
    # To avoid complexity, I'll assume wechatpy's `encrypt_message` returns the XML string.
    # And we parse it to get Encrypt text for signature.
    
    try:
        res_xml_str = crypto.encrypt_message(raw_xml_for_encryption, nonce, timestamp)
        root = ET.fromstring(res_xml_str)
        encrypt_content = root.find("Encrypt").text
        signature = calculate_signature(TOKEN, timestamp, nonce, encrypt_content)
        
        url = f"http://127.0.0.1:8000/api/wecom/callback?msg_signature={signature}&timestamp={timestamp}&nonce={nonce}&echostr="
        
        print(f"📤 发送: {content}")
        res = requests.post(url, data=res_xml_str, headers={'Content-Type': 'application/xml'})
        
        if res.status_code == 200:
             # Decrypt response
            try:
                # Response is XML with its own signature
                root = ET.fromstring(res.content)
                msg_signature = root.find("MsgSignature").text
                # timestamp/nonce in response might differ or reuse?
                # Usually checks signature against values inside XML or passed params?
                # wechatpy's decrypt_message verifies signature.
                # If we pass response XML string, we must pass the signature found in it.
                
                # Check if TimeStamp/Nonce are in XML (Yes they are)
                resp_timestamp = root.find("TimeStamp").text
                resp_nonce = root.find("Nonce").text
                
                decrypted_xml = crypto.decrypt_message(res.content, msg_signature, resp_timestamp, resp_nonce)
                root_dec = ET.fromstring(decrypted_xml)
                
                resp_content = root_dec.find("Content").text
                print(f"📩 回复: {resp_content}\n")
            except Exception as e:
                print(f"📩 回复(原文): {res.text[:100]}... (解密失败: {e})")
        else:
            print(f"❌ Error: {res.status_code} {res.text}")

    except Exception as e:
        print(f"❌ Encryption Error: {e}")


if __name__ == "__main__":
    print(f"🔧 Starting Local WeChat Test (AES_KEY: {AES_KEY[:5]}...)")
    while True:
        txt = input("请输入测试指令 (输入 q 退出): ").strip()
        if txt == 'q': break
        if not txt: continue
        send_text(txt)

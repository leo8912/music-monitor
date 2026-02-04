import sys
import os
import time
import random
import string
import requests
import yaml
import hashlib
import xml.etree.cElementTree as ET
from wechatpy.crypto import WeChatCrypto

# Add project root to path
sys.path.append(os.getcwd())

def load_config():
    try:
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config/config.yaml not found.")
        sys.exit(1)

def main():
    config = load_config()
    wecom_cfg = config.get('notify', {}).get('wecom', {})
    
    token = wecom_cfg.get('token')
    encoding_aes_key = wecom_cfg.get('encoding_aes_key')
    corpid = wecom_cfg.get('corpid')
    
    if not all([token, encoding_aes_key, corpid]):
        print("Error: WeCom config missing in config.yaml")
        sys.exit(1)

    crypto = WeChatCrypto(token, encoding_aes_key, corpid)
    
    # Simulate a user
    user_id = "test_user_001"
    agent_id = wecom_cfg.get('agentid', '1000001')
    
    print(f"=== WeCom Interaction Simulator ===", flush=True)
    print(f"User: {user_id}", flush=True)
    print(f"Target: http://127.0.0.1:8000/api/wecom/callback", flush=True)
    print("Type your message and press Enter. Type 'exit' to quit.\n", flush=True)

    while True:
        try:
            content = input("You > ").strip()
        except EOFError:
            break
            
        if content.lower() in ['exit', 'quit']:
            break
        
        if not content:
            continue

        # Construct XML payload
        xml_template = """<xml>
            <ToUserName><![CDATA[{to_user}]]></ToUserName>
            <FromUserName><![CDATA[{from_user}]]></FromUserName>
            <CreateTime>{time}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
            <MsgId>{msg_id}</MsgId>
            <AgentID>{agent_id}</AgentID>
        </xml>"""
        
        timestamp = str(int(time.time()))
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        msg_id = str(int(time.time() * 1000))
        
        raw_xml = xml_template.format(
            to_user=corpid,
            from_user=user_id,
            time=timestamp,
            content=content,
            msg_id=msg_id,
            agent_id=agent_id
        )
        
        # Encrypt
        encrypt_xml = crypto.encrypt_message(raw_xml, nonce, timestamp)
        
        # Parse out the 'Encrypt' content for signature calculation
        # encrypt_message returns a full XML
        if isinstance(encrypt_xml, bytes):
            enc_str = encrypt_xml.decode('utf-8')
        else:
            enc_str = encrypt_xml
            
        root = ET.fromstring(enc_str)
        encrypt_content = root.find('Encrypt').text
        
        # Requests
        # Signature = SHA1(Sort(Token, Timestamp, Nonce, Encrypt))
        sl = [token, timestamp, nonce, encrypt_content]
        sl.sort()
        sha1 = hashlib.sha1()
        sha1.update("".join(sl).encode('utf-8'))
        signature = sha1.hexdigest()
        
        url = "http://127.0.0.1:8000/api/wecom/callback"
        params = {
            "msg_signature": signature,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        print(f"Sending...", flush=True)
        try:
            response = requests.post(url, params=params, data=encrypt_xml, timeout=10)
            if response.status_code == 200:
                resp_content = response.content
                if not resp_content:
                    print("Server > (No Reply/Success)", flush=True)
                    continue
                
                # Decrypt response
                try:
                    # Try decrypting
                    decrypted_xml = crypto.decrypt_message(
                        resp_content, 
                        signature, # Use same signature for simplicity or assume valid
                        timestamp, 
                        nonce
                    )
                    
                    root = ET.fromstring(decrypted_xml)
                    reply_content = root.find('Content').text
                    print(f"Music Monitor > {reply_content}\n", flush=True)
                except Exception as e:
                     # If decryption fails, maybe it's plain text error?
                    print(f"Server Raw > {resp_content}", flush=True)
            else:
                print(f"Error: HTTP {response.status_code}", flush=True)
                print(f"Body: {response.text}", flush=True)
                
        except Exception as e:
            print(f"Request Error: {e}", flush=True)

if __name__ == "__main__":
    main()

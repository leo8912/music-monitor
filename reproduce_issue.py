from wechatpy.crypto import WeChatCrypto
import logging

try:
    # Dummy values
    token = "token"
    aes_key = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"
    corp_id = "corp_id"
    
    crypto = WeChatCrypto(token, aes_key, corp_id)
    print("WeChatCrypto instantiated.")
    
    if hasattr(crypto, 'check_signature'):
        print("WeChatCrypto has check_signature.")
    else:
        print("WeChatCrypto DOES NOT have check_signature.")
        
except Exception as e:
    print(f"Error: {e}")

from wechatpy.crypto import WeChatCrypto, PrpCrypto
import logging

class FixedWeChatCrypto(WeChatCrypto):
    def check_signature(self, signature, timestamp, nonce, echo_str):
        # Just checking if methods exist and can be called without AttributeError
        # We don't have valid signatures to pass verification, so Expect InvalidSignatureException or similar
        return self._check_signature(signature, timestamp, nonce, echo_str, PrpCrypto)

try:
    # Dummy values
    token = "token"
    aes_key = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"
    corp_id = "corp_id"
    
    crypto = FixedWeChatCrypto(token, aes_key, corp_id)
    print("FixedWeChatCrypto instantiated.")
    
    if hasattr(crypto, 'check_signature'):
        print("FixedWeChatCrypto has check_signature.")
        try:
             # This will likely fail signature check, but shouldn't raise AttributeError
             crypto.check_signature("sig", "123", "nonce", "echo")
        except Exception as e:
             print(f"Call check_signature result: {type(e).__name__}: {e}")
             if "AttributeError" in str(type(e).__name__):
                 print("FAILED: Still getting AttributeError")
             else:
                 print("SUCCESS: Method called successfully (even if signature validation failed)")
    else:
        print("FixedWeChatCrypto DOES NOT have check_signature.")
        
except Exception as e:
    print(f"Error: {e}")

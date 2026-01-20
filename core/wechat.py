from wechatpy.crypto import WeChatCrypto, PrpCrypto
import hashlib

class FixedWeChatCrypto(WeChatCrypto):
    def check_signature(self, signature, timestamp, nonce, echo_str):
        return self._check_signature(signature, timestamp, nonce, echo_str, PrpCrypto)
        
    def get_signature(self, timestamp, nonce, encrypt):
        """Internal wechatpy signature calculation used for encrypted replies."""
        v = [self.token, timestamp, nonce, encrypt]
        v.sort()
        sha = hashlib.sha1("".join(v).encode("utf-8"))
        return sha.hexdigest()

from wechatpy.crypto import WeChatCrypto, PrpCrypto

class FixedWeChatCrypto(WeChatCrypto):
    def check_signature(self, signature, timestamp, nonce, echo_str):
        return self._check_signature(signature, timestamp, nonce, echo_str, PrpCrypto)

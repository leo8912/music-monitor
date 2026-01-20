"""
微信企业号本地测试工具
支持测试歌手搜索、添加和歌曲下载功能
"""
import requests
import time
import logging
import xml.etree.cElementTree as ET
from wechatpy.crypto import WeChatCrypto
from core.config import config, load_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from core.wechat import FixedWeChatCrypto

# 加载配置
# 由于 config.yaml 被移到了 config/ 目录，我们需要手动指定或更新环境
config.update(load_config())
if not config:
    # 尝试从 config 子目录加载
    import os
    if os.path.exists("config/config.yaml"):
        with open("config/config.yaml", "r", encoding='utf-8') as f:
            import yaml
            config.update(yaml.safe_load(f))

wecom_cfg = config.get('notify', {}).get('wecom', {})
TOKEN = wecom_cfg.get('token')
AES_KEY = wecom_cfg.get('encoding_aes_key')
CORP_ID = wecom_cfg.get('corpid')

if not TOKEN or not AES_KEY:
    print("❌ 错误: 缺少 WeChat 配置")
    print("请在 config.yaml 中配置:")
    print("  notify.wecom.token")
    print("  notify.wecom.encoding_aes_key")
    print("  notify.wecom.corpid")
    exit(1)

crypto = WeChatCrypto(TOKEN, AES_KEY, CORP_ID)

# 测试目标地址（可修改）
# - 本地开发: http://127.0.0.1:8000
# - 本地Docker: http://127.0.0.1:18001
BASE_URL = "http://127.0.0.1:18001"  # 默认测试Docker容器

import hashlib

def calculate_signature(token, timestamp, nonce, encrypt):
    """计算签名"""
    sort_list = [token, timestamp, nonce, encrypt]
    sort_list.sort()
    sha = hashlib.sha1("".join(sort_list).encode("utf-8"))
    return sha.hexdigest()

def send_text(content, user_id="TestUser001"):
    """发送文本消息到微信回调接口"""
    nonce = str(int(time.time() * 1000))
    timestamp = str(int(time.time()))
    
    # 构造原始XML
    raw_xml = f"""<xml>
    <ToUserName><![CDATA[{CORP_ID}]]></ToUserName>
    <FromUserName><![CDATA[{user_id}]]></FromUserName>
    <CreateTime>{timestamp}</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[{content}]]></Content>
    <MsgId>{int(time.time()*1000)}</MsgId>
    <AgentID>1000002</AgentID>
    </xml>"""
    
    try:
        # 加密消息
        encrypted_xml = crypto.encrypt_message(raw_xml, nonce, timestamp)
        
        # 从加密XML中提取Encrypt字段计算签名
        root = ET.fromstring(encrypted_xml)
        encrypt_content = root.find("Encrypt").text
        signature = calculate_signature(TOKEN, timestamp, nonce, encrypt_content)
        
        # 构造回调URL
        url = f"{BASE_URL}/api/wecom/callback?msg_signature={signature}&timestamp={timestamp}&nonce={nonce}"
        
        print(f"\n📤 发送消息: {content}")
        print(f"   用户ID: {user_id}")
        
        # 发送POST请求
        res = requests.post(url, data=encrypted_xml, headers={'Content-Type': 'application/xml'}, timeout=10)
        
        if res.status_code == 200:
            try:
                # 解析响应XML
                resp_root = ET.fromstring(res.content)
                msg_signature = resp_root.find("MsgSignature").text
                resp_timestamp = resp_root.find("TimeStamp").text
                resp_nonce = resp_root.find("Nonce").text
                
                # 解密响应
                decrypted_xml = crypto.decrypt_message(
                    res.content, 
                    msg_signature, 
                    resp_timestamp, 
                    resp_nonce
                )
                
                dec_root = ET.fromstring(decrypted_xml)
                
                # 提取回复内容
                msg_type = dec_root.find("MsgType").text
                
                if msg_type == "text":
                    resp_content = dec_root.find("Content").text
                    print(f"📩 文本回复:\n{resp_content}\n")
                
                elif msg_type == "news":
                    articles = dec_root.findall(".//item")
                    print(f"📩 图文回复 ({len(articles)} 项):")
                    for idx, item in enumerate(articles, 1):
                        title = item.find("Title").text
                        desc = item.find("Description").text or ""
                        url = item.find("Url").text or ""
                        print(f"  {idx}. {title}")
                        if desc:
                            print(f"     {desc}")
                        if url:
                            print(f"     🔗 {url}")
                    print()
                
                else:
                    print(f"📩 其他类型回复: {msg_type}")
                    print(f"   内容: {decrypted_xml[:200]}...\n")
                    
            except Exception as e:
                logger.error(f"响应解析失败: {e}")
                print(f"📩 原始响应: {res.text[:200]}...")
        else:
            print(f"❌ HTTP错误: {res.status_code}")
            print(f"   响应: {res.text[:200]}")
    
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 {BASE_URL}")
        print("   请确认服务是否运行:")
        print("   - 本地开发: python main.py")
        print("   - Docker:   docker logs music-monitor-test")
    except Exception as e:
        logger.error(f"发送失败: {e}", exc_info=True)
        print(f"❌ 错误: {e}")


def test_artist_search():
    """测试歌手搜索功能"""
    print("\n" + "="*50)
    print("测试场景: 歌手搜索")
    print("="*50)
    
    test_cases = [
        "任素汐",
        "周杰伦",
        "李荣浩"
    ]
    
    for artist in test_cases:
        input(f"\n按回车测试搜索: {artist} ...")
        send_text(artist)


def test_artist_add():
    """测试添加歌手功能"""
    print("\n" + "="*50)
    print("测试场景: 添加歌手")
    print("="*50)
    print("步骤:")
    print("1. 先搜索歌手")
    print("2. 回复序号选择")
    
    artist_name = input("\n请输入歌手名: ").strip() or "任素汐"
    
    # 第一步：搜索
    print(f"\n➡️  步骤1: 搜索 {artist_name}")
    send_text(artist_name)
    
    # 第二步：选择
    choice = input("\n请输入序号选择歌手 (默认1): ").strip() or "1"
    print(f"\n➡️  步骤2: 选择序号 {choice}")
    send_text(choice)


def test_song_download():
    """测试歌曲下载功能"""
    print("\n" + "="*50)
    print("测试场景: 歌曲搜索与下载")
    print("="*50)
    
    song_name = input("\n请输入歌曲名 (默认'成都'): ").strip() or "成都"
    
    # 第一步：搜索歌曲
    print(f"\n➡️  步骤1: 搜索歌曲 '{song_name}'")
    send_text(f"下载 {song_name}")
    
    # 第二步：选择下载
    choice = input("\n请输入序号下载 (默认1): ").strip() or "1"
    print(f"\n➡️  步骤2: 选择下载序号 {choice}")
    send_text(choice)


def interactive_mode():
    """交互模式"""
    print("\n" + "="*50)
    print("交互模式")
    print("="*50)
    print("直接输入文本发送到WeChat回调")
    print("输入 'q' 退出\n")
    
    while True:
        txt = input("🔧 输入指令: ").strip()
        if txt.lower() == 'q':
            break
        if not txt:
            continue
        send_text(txt)


def change_url():
    """切换目标URL"""
    global BASE_URL
    
    print("\n当前目标:")
    print("  1. http://127.0.0.1:8000  (本地开发)")
    print("  2. http://127.0.0.1:18001 (Docker容器)")
    print("  3. 自定义")
    
    url_choice = input("选择 (1-3): ").strip()
    if url_choice == '1':
        BASE_URL = "http://127.0.0.1:8000"
    elif url_choice == '2':
        BASE_URL = "http://127.0.0.1:18001"
    elif url_choice == '3':
        BASE_URL = input("请输入完整URL: ").strip()
    
    print(f"✅ 已切换到: {BASE_URL}")


def main():
    """主菜单"""
    print("\n" + "="*60)
    print(" 📱 微信企业号本地测试工具")
    print("="*60)
    print(f"目标地址: {BASE_URL}")
    print(f"Corp ID: {CORP_ID}")
    print(f"Token: {TOKEN[:5]}***")
    print("="*60)
    
    while True:
        print("\n请选择测试场景:")
        print("  1. 🎤 测试歌手搜索")
        print("  2. ➕ 测试添加歌手")
        print("  3. 🎵 测试歌曲下载")
        print("  4. 💬 交互模式 (自由输入)")
        print("  5. 🔧 切换目标地址")
        print("  q. 退出")
        
        choice = input("\n选择 (1-5/q): ").strip().lower()
        
        if choice == '1':
            test_artist_search()
        elif choice == '2':
            test_artist_add()
        elif choice == '3':
            test_song_download()
        elif choice == '4':
            interactive_mode()
        elif choice == '5':
            change_url()
        
        elif choice == 'q':
            print("\n👋 再见!")
            break
        else:
            print("❌ 无效选择")


if __name__ == "__main__":
    main()

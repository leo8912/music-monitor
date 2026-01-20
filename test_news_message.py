"""
测试企微图文消息（News）卡片发送
"""
import asyncio
import logging
import os
import yaml
from notifiers.wecom import WeComNotifier
from core.security import generate_signed_url_params

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_test_config():
    """加载配置文件"""
    config_path = "config/config.yaml"
    if not os.path.exists(config_path):
        config_path = "config.yaml"
    
    if not os.path.exists(config_path):
        print(f"❌ 找不到配置文件: {config_path}")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

async def test_news_message():
    """测试发送图文消息"""
    print("\n" + "="*60)
    print(" 📤 测试企微图文消息发送")
    print("="*60)
    
    # 加载配置
    config = load_test_config()
    
    # 检查配置
    wecom_cfg = config.get('notify', {}).get('wecom', {})
    if not wecom_cfg.get('corpid') or not wecom_cfg.get('corpsecret'):
        print("❌ 错误: 缺少企微配置")
        print("请在 config.yaml 中配置:")
        print("  notify.wecom.corpid")
        print("  notify.wecom.corpsecret")
        print("  notify.wecom.agentid")
        return
    
    print(f"Corp ID: {wecom_cfg.get('corpid')[:10]}***")
    print(f"Agent ID: {wecom_cfg.get('agentid')}")
    
    # 生成测试用的签名链接
    test_song_id = "netease_12345"
    sign_params = generate_signed_url_params(test_song_id)
    
    base_url = config.get('global', {}).get('external_url', 'http://localhost:8000')
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    from urllib.parse import quote
    encoded_id = quote(sign_params['id'])
    magic_url = f"{base_url}/#/mobile/play?id={encoded_id}&sign={sign_params['sign']}&expires={sign_params['expires']}"
    
    # 准备测试数据
    test_data = {
        "title": "✅ 测试：下载完成",
        "description": "🎙️ 歌手: 测试歌手\n💾 已加入收藏\n\n点击立即播放（72小时有效）",
        "url": magic_url,
        "pic_url": "https://p2.music.126.net/tGHU62DTszbTsM7vzNgHjw==/109951165631226326.jpg"
    }
    
    print("\n📋 发送内容:")
    print(f"  标题: {test_data['title']}")
    print(f"  描述: {test_data['description']}")
    print(f"  链接: {test_data['url'][:80]}...")
    print(f"  封面: {test_data['pic_url'][:60]}...")
    
    # 询问是否指定用户
    send_to_all = input("\n发送给所有人? (y/n, 默认y): ").strip().lower()
    user_ids = None
    
    if send_to_all == 'n':
        user_id = input("请输入用户ID: ").strip()
        if user_id:
            user_ids = [user_id]
            print(f"将发送给用户: {user_id}")
    
    if user_ids is None:
        print("将发送给: @all (所有人)")
    
    # 确认发送
    confirm = input("\n确认发送? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ 已取消")
        return
    
    # 创建通知器
    notifier = WeComNotifier()
    
    # 先测试连接
    print("\n🔧 测试企微连接...")
    try:
        is_connected = await notifier.check_connectivity()
        if not is_connected:
            print("❌ 企微连接失败，请检查配置")
            return
        print("✅ 企微连接成功")
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return
    
    # 发送图文消息
    print("\n📤 正在发送图文消息...")
    try:
        await notifier.send_news_message(
            title=test_data['title'],
            description=test_data['description'],
            url=test_data['url'],
            pic_url=test_data['pic_url'],
            user_ids=user_ids
        )
        print("✅ 发送成功！")
        print("\n请检查企业微信是否收到图文消息卡片")
        print("卡片应包含:")
        print("  - 封面图片")
        print("  - 标题和描述")
        print("  - 可点击的链接")
        
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        import traceback
        traceback.print_exc()


async def test_text_message():
    """测试发送普通文本消息"""
    print("\n" + "="*60)
    print(" 📤 测试企微文本消息发送")
    print("="*60)
    
    # 加载配置
    config = load_test_config()
    
    notifier = WeComNotifier()
    
    # 先测试连接
    print("\n🔧 测试企微连接...")
    try:
        is_connected = await notifier.check_connectivity()
        if not is_connected:
            print("❌ 企微连接失败，请检查配置")
            return
        print("✅ 企微连接成功")
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return
    
    # 发送测试文本
    test_content = "🎵 这是一条测试消息\n来自 Music Monitor 通知系统\n\n✅ 如果收到此消息，说明配置正常！"
    
    print(f"\n📋 发送内容:\n{test_content}")
    
    confirm = input("\n确认发送? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ 已取消")
        return
    
    print("\n📤 正在发送文本消息...")
    try:
        await notifier.send_text(test_content)
        print("✅ 发送成功！")
        print("\n请检查企业微信是否收到文本消息")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主菜单"""
    print("\n" + "="*60)
    print(" 📱 企业微信通知测试工具")
    print("="*60)
    
    while True:
        print("\n请选择测试类型:")
        print("  1. 📰 测试图文消息卡片 (News)")
        print("  2. 💬 测试文本消息")
        print("  q. 退出")
        
        choice = input("\n选择 (1-2/q): ").strip().lower()
        
        if choice == '1':
            await test_news_message()
        elif choice == '2':
            await test_text_message()
        elif choice == 'q':
            print("\n👋 再见!")
            break
        else:
            print("❌ 无效选择")


if __name__ == "__main__":
    asyncio.run(main())

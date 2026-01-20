"""
快速生成移动端播放链接测试工具
"""
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params


def main():
    print("\n" + "="*70)
    print(" 🎵 移动端播放链接生成器")
    print("="*70)
    
    # 查询数据库中的歌曲
    db = SessionLocal()
    try:
        records = db.query(MediaRecord).limit(10).all()
        
        if not records:
            print("❌ 数据库中暂无歌曲记录")
            return
        
        print(f"\n数据库中的歌曲 (共 {len(records)} 首):")
        for i, r in enumerate(records, 1):
            print(f"  {i}. {r.title} - {r.author} ({r.source})")
        
        # 选择歌曲
        choice = input(f"\n请选择歌曲序号 (1-{len(records)}, 默认1): ").strip()
        if not choice:
            choice = "1"
        
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(records):
                print("❌ 无效的序号")
                return
        except ValueError:
            print("❌ 请输入数字")
            return
        
        song = records[idx]
        
        print(f"\n✅ 已选择:")
        print(f"  标题: {song.title}")
        print(f"  歌手: {song.author}")
        print(f"  来源: {song.source}")
        print(f"  unique_key: {song.unique_key}")
        
        # 询问服务地址
        base_url = input("\n请输入服务地址 (默认: http://localhost:18001): ").strip()
        if not base_url:
            base_url = "http://localhost:18001"
        
        # 生成签名链接
        print(f"\n🔗 生成链接...")
        sign_params = generate_signed_url_params(song.unique_key)
        
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        
        magic_url = f"{base_url}/#/mobile/play?id={sign_params['id']}&sign={sign_params['sign']}&expires={sign_params['expires']}"
        
        print(f"\n" + "="*70)
        print(" 📱 移动端播放链接")
        print("="*70)
        
        print(f"\n完整链接:")
        print(f"\n{magic_url}\n")
        
        print(f"签名参数:")
        print(f"  id: {sign_params['id']}")
        print(f"  sign: {sign_params['sign'][:30]}...")
        print(f"  expires: {sign_params['expires']} (72小时有效)")
        
        # 浏览器模拟方法
        print("\n" + "="*70)
        print(" 🖥️  浏览器模拟手机访问方法")
        print("="*70)
        
        print("\n【推荐】方法1: Chrome/Edge 开发者工具模拟")
        print("  1. 复制上面的链接")
        print("  2. 在浏览器中粘贴并打开")
        print("  3. 按 F12 打开开发者工具")
        print("  4. 按 Ctrl+Shift+M 切换设备模拟模式")
        print("  5. 选择 'iPhone 12 Pro' 或其他手机型号")
        print("  6. 刷新页面 (F5)")
        
        print("\n方法2: 直接访问（桌面版也支持）")
        print("  移动端播放器自适应屏幕，桌面浏览器也能正常使用")
        
        print("\n方法3: 真机测试（需要局域网）")
        print("  1. 获取电脑局域网IP: ipconfig (查看IPv4地址)")
        print("  2. 将链接中的 localhost 替换为局域网IP")
        print("  3. 确保手机和电脑在同一WiFi")
        print("  4. 在手机浏览器中打开链接")
        
        print("\n💡 功能说明:")
        print("  ✅ 沉浸式全屏播放器")
        print("  ✅ 专辑封面高斯模糊背景")
        print("  ✅ 播放/暂停控制")
        print("  ✅ 进度条拖动")
        print("  ✅ 快进/快退 10秒")
        print("  ✅ 点击封面切换歌词视图")
        print("  ✅ 歌词自动滚动")
        
        # 询问是否在浏览器中打开
        print("\n" + "="*70)
        open_browser = input("\n是否在默认浏览器中打开? (y/n, 默认y): ").strip().lower()
        if open_browser != 'n':
            import webbrowser
            webbrowser.open(magic_url)
            print("\n✅ 已在浏览器中打开")
            print("💡 记得按 F12 然后 Ctrl+Shift+M 切换到手机模式查看效果")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

import asyncio
import os
import yaml
from urllib.parse import quote
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params
from notifiers.wecom import WeComNotifier
from core.config import load_config

async def main():
    load_config()
    print("Connecting to DB...")
    db = SessionLocal()
    try:
        # Find "困" or latest
        record = db.query(MediaRecord).filter(MediaRecord.title.like("%困%")).first()
        if not record:
            record = db.query(MediaRecord).order_by(MediaRecord.id.desc()).first()
        
        if not record:
            print("❌ No songs found in DB.")
            return

        print(f"🎵 Found song: {record.title} - {record.author}")
        
        # Load Config for base URL
        config_path = "config/config.yaml" if os.path.exists("config/config.yaml") else "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
            
        base_url = cfg.get('global', {}).get('external_url', 'http://localhost:8000')
        if base_url.endswith('/'): base_url = base_url[:-1]
        
        # Ensure we use the correct port if it is localhost (user runs on 8000)
        if "localhost" in base_url and "8000" not in base_url:
             # Just a heuristic, if user forgot to set port in external_url
             pass

        # Generate Link
        song_id = record.unique_key
        sign_params = generate_signed_url_params(song_id)
        
        encoded_id = quote(sign_params['id'])
        magic_url = f"{base_url}/#/mobile/play?id={encoded_id}&sign={sign_params['sign']}&expires={sign_params['expires']}"
        
        cover = record.cover if record.cover else "https://p2.music.126.net/tGHU62DTszbTsM7vzNgHjw==/109951165631226326.jpg"

        # Check cover path. If relative local path /uploads/..., WeCom needs full URL.
        if cover.startswith("/"):
            cover = f"{base_url}{cover}"
            
        print(f"🔗 URL: {magic_url}")
        print(f"🖼️ Cover: {cover}")
        
        wecom_cfg = cfg.get('notify', {}).get('wecom', {})
        notifier = WeComNotifier(
            corp_id=wecom_cfg.get('corpid'),
            secret=wecom_cfg.get('corpsecret'),
            agent_id=wecom_cfg.get('agentid')
        )
        
        await notifier.send_news_message(
            title=f"✅ 测试推送: {record.title}",
            description=f"🎙️ {record.author}\n💾 已加入收藏\n\n点击立即测试移动端播放器 v2.0",
            url=magic_url,
            pic_url=cover
        )
        print("✅ Message sent successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

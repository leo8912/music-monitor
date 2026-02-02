"""
生成链接并保存到文件，防止日志截断
"""
from core.database import SessionLocal, MediaRecord
from core.security import generate_signed_url_params
from urllib.parse import quote
import webbrowser

db = SessionLocal()
try:
    record = db.query(MediaRecord).filter(MediaRecord.title.contains("我不要原谅你")).first()
    if not record: record = db.query(MediaRecord).first()
    
    sign_params = generate_signed_url_params(record.unique_key)
    base_url = "http://localhost:8000"
    encoded_id = quote(sign_params['id'])
    magic_url = f"{base_url}/#/mobile/play?id={encoded_id}&sign={sign_params['sign']}&expires={sign_params['expires']}"
    
    with open("mobile_link.txt", "w", encoding="utf-8") as f:
        f.write(magic_url)
        
    print("Link saved to mobile_link.txt")
    webbrowser.open(magic_url)
finally:
    db.close()

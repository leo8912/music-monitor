from core.database import SessionLocal, MediaRecord
import yaml

# 读取配置
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("当前QQ音乐配置:")
for u in config['monitor']['qqmusic']['users']:
    print(f"- {u['name']} ({u['id']})")

print("\n请重启后端服务以加载新配置并触发同步。")

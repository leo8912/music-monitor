import os
import time
import sys

DB_FILE = "music_monitor.db"

def reset_db():
    print(f"🔄 正在尝试重置本地数据库: {DB_FILE} ...")
    
    if not os.path.exists(DB_FILE):
        print("✅ 数据库文件不存在，无需删除。环境已是干净的。")
        return

    ctx = 0
    while os.path.exists(DB_FILE) and ctx < 5:
        try:
            os.remove(DB_FILE)
            print("✅ 成功删除旧数据库文件！")
            break
        except PermissionError:
            print(f"⚠️ 文件被占用，尝试等待 1 秒... ({ctx+1}/5)")
            time.sleep(1)
            ctx += 1
    
    if os.path.exists(DB_FILE):
        print("❌ 删除失败！文件仍被其他进程占用。")
        print("请手动关闭所有 python 进程或重启终端，然后手动删除 'music_monitor.db'。")
        sys.exit(1)
    else:
        print("✨ 环境重置完成！现在可以直接运行 python main.py 了。")

if __name__ == "__main__":
    reset_db()

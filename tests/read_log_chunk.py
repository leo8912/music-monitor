
with open("logs/application.log", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    print("".join(lines[3600:3650]))

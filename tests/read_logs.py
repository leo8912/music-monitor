
import os

log_file = "logs/application.log"
if not os.path.exists(log_file):
    print("Log file not found")
else:
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        print("".join(lines[-100:]))

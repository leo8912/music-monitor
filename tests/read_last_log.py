
import os

log_file = "logs/application.log"
with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
    print("".join(lines[-100:]))

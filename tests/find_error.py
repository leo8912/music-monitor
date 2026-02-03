
import os
with open("logs/application.log", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "NameError" in line:
            print(f"--- Found at line {i+1} ---")
            print("".join(lines[i-5:i+10]))

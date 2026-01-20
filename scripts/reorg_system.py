import re

path = "d:/code/music-monitor/main.py"
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

def find_line(txt):
    for i, line in enumerate(lines):
        if txt in line:
            return i
    return -1

# 1. Duplicate Lifespan
# First @asynccontextmanager
first_lifespan_dec = find_line('@asynccontextmanager')
# Second @asynccontextmanager
second_lifespan_dec = -1
if first_lifespan_dec != -1:
    for i in range(first_lifespan_dec + 1, len(lines)):
        if '@asynccontextmanager' in lines[i]:
            second_lifespan_dec = i
            break

# 2. System Endpoints
start_status = find_line('@app.get("/api/status")')
# End of block 2 (before log handler or similar)
# We want to keep 277-279: api_log_handler setup
# Setup usually looks like: api_log_handler.setFormatter
end_status_block = find_line('api_log_handler.setFormatter')

# 3. Logs/Notify block
start_logs = find_line('@app.get("/api/logs")')
# This goes to EOF usually

ranges = []

if first_lifespan_dec != -1 and second_lifespan_dec != -1:
    print(f"Removing Duplicate Lifespan: {first_lifespan_dec} to {second_lifespan_dec}")
    ranges.append((first_lifespan_dec, second_lifespan_dec))
else:
    print(f"Warning: Duplicate Lifespan not found. {first_lifespan_dec}, {second_lifespan_dec}")

if start_status != -1 and end_status_block != -1:
    print(f"Removing Status/Settings: {start_status} to {end_status_block}")
    ranges.append((start_status, end_status_block))
else:
    print(f"Warning: Status/Settings block not found. {start_status}, {end_status_block}")

if start_logs != -1:
    print(f"Removing Logs/Notify: {start_logs} to EOF")
    ranges.append((start_logs, len(lines)))
else:
    print("Warning: Logs block not found")

# Filter lines
keep = [True] * len(lines)
for s, e in ranges:
    for i in range(s, e):
        if i < len(keep):
            keep[i] = False

new_lines = []
for i, line in enumerate(lines):
    if keep[i]:
        # Fix Config Reload Logic
        # if "config = load_config()" replacing "config.update(load_config())"
        # and "global config" removal
        if "global config" in line:
             continue # Remove global config line
        
        if "config = load_config()" in line:
             new_lines.append(line.replace("config = load_config()", "config.update(load_config())"))
        else:
             new_lines.append(line)

with open(path, "w", encoding='utf-8') as f:
    f.writelines(new_lines)
print("Done")

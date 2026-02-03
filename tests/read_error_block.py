
with open("logs/application.log", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    # Find lines with "10:43" to locate the error
    start_idx = 0
    for i, line in enumerate(lines):
        if "10:43" in line and "Traceback" not in line: # Start of the block
             start_idx = i
    
    # Print the last found block + 50 lines
    if start_idx > 0:
        print("".join(lines[start_idx:start_idx+50]))
    else:
        print("Timestamp not found, printing last 50 lines:")
        print("".join(lines[-50:]))

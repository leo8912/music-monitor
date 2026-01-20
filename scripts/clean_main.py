
path = "d:/code/music-monitor/main.py"
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

# Target Line 355: "# --- Auth Endpoints ---"
# Target Line 534: "# Allow CORS for dev ..."
# (Indices are line_num - 1)

start_idx = 354
end_idx = 533 # Line 534

# Verification
if "# --- Auth Endpoints ---" not in lines[start_idx]:
    print(f"Error: Start line mismatch: {lines[start_idx]}")
    exit(1)

if "# Allow CORS" not in lines[end_idx]:
    print(f"Error: End line mismatch: {lines[end_idx]}")
    # Try searching
    found = False
    for i in range(len(lines)):
        if "# Allow CORS" in lines[i]:
            end_idx = i
            found = True
            break
    if not found:
        print("Error: Could not find end line")
        exit(1)

print(f"Removing lines {start_idx+1} to {end_idx}")
new_lines = lines[:start_idx] + lines[end_idx:]

with open(path, "w", encoding='utf-8') as f:
    f.writelines(new_lines)
print("Success")

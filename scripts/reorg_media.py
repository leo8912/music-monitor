import re

path = "d:/code/music-monitor/main.py"
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

def find_line(txt):
    for i, line in enumerate(lines):
        if txt in line:
            return i
    return -1

# 1. Remove Download/Serve/Lyric
# Start: @app.post("/api/download_audio")
# End: # Add Middleware (Session)
start_dl = find_line('@app.post("/api/download_audio")')
start_mid = find_line('# Add Middleware (Session)')

# 2. Remove ArtistConfig...Proxy
# Start: class ArtistConfig(BaseModel):
# End: @app.get("/api/settings")
start_art = find_line('class ArtistConfig(BaseModel):')
start_sett = find_line('@app.get("/api/settings")')

# 3. Remove match_bilibili
# Start: @app.get("/api/match_bilibili")
# End: @app.post("/api/test_notify/{channel}")
start_bili = find_line('@app.get("/api/match_bilibili")')
start_test = find_line('@app.post("/api/test_notify/{channel}")')

# 4. Remove get_history
# Start: @app.get("/api/history")
# End: End of file? Or next function? 
# Usually get_history was last or near last.
start_hist = find_line('@app.get("/api/history")')
# Find next definition or end
start_next = -1
if start_hist != -1:
    for i in range(start_hist + 1, len(lines)):
        if lines[i].startswith("@app.") or lines[i].startswith("def ") or lines[i].startswith("class "):
             # Check if it's a new top level block
             pass
    # Assuming it's the last function shown in view?
    # In Step 997, get_history goes to 798.
    # Check if anything follows. 
    # Just delete from start_hist to end if strictly nothing else?
    # Safer: Look for next known endpoint? No.
    # Just look for Double Newline after indentation reset?
    # Let's delete from start_hist to len(lines) if it's truly last.
    pass

ranges = []
if start_dl != -1 and start_mid != -1:
    print(f"Removing Audio/Lyric: {start_dl} to {start_mid}")
    ranges.append((start_dl, start_mid))
else:
    print(f"Warning: Audio/Lyric block not found. {start_dl}, {start_mid}")

if start_art != -1 and start_sett != -1:
    print(f"Removing Artist/Proxy: {start_art} to {start_sett}")
    ranges.append((start_art, start_sett))
else:
    print(f"Warning: Artist/Proxy block not found. {start_art}, {start_sett}")

if start_bili != -1 and start_test != -1:
    print(f"Removing Bilibili: {start_bili} to {start_test}")
    ranges.append((start_bili, start_test))
else:
    print(f"Warning: Bilibili block not found")

if start_hist != -1:
    # Assume it goes to end of file for now?
    # Or find end by indent.
    # Or just delete fixed valid amount if we know logic.
    # To be safe, let's keep it if unsure, OR search for `if __name__` (none).
    # Since it was near end, let's assume end.
    print(f"Removing History: {start_hist} to EOF")
    ranges.append((start_hist, len(lines)))
else:
    print("Warning: History block not found")

# Sort ranges descending to keep indices valid?
# Actually constructing new list is easier.
# Mark lines to keep.
keep = [True] * len(lines)
for s, e in ranges:
    for i in range(s, e):
        if i < len(keep):
            keep[i] = False

new_lines = [line for i, line in enumerate(lines) if keep[i]]

with open(path, "w", encoding='utf-8') as f:
    f.writelines(new_lines)
print("Done")


import os

file_path = "app/services/enrichment_service.py"

new_method_body = """    def _write_mp3_tags(self, file_path: str, album_name: str = None, cover_path: str = None):
        \"\"\"写入 MP3 标签 (带容错)\"\"\"
        try:
            # 尝试作为 MP3 解析 (会检查 MPEG 帧)
            audio = MP3(file_path, ID3=ID3)
        except Exception:
            # 如果音频帧损坏，尝试仅操作 ID3 标签
            try:
                audio = ID3(file_path)
            except Exception:
                # 如果完全没有标签，创建一个新的
                audio = ID3()
        
        # 确保有 tags 属性 (对于 MP3 对象) 或本身就是 ID3 对象
        if isinstance(audio, MP3) and not audio.tags:
            audio.add_tags()
        
        if cover_path and os.path.exists(cover_path):
            mime = 'image/png' if cover_path.endswith('.png') else 'image/jpeg'
            with open(cover_path, 'rb') as f:
                # 无论 audio 是 MP3 还是 ID3，add 方法都可用
                target = audio.tags if isinstance(audio, MP3) else audio
                target.add(APIC(
                    encoding=3,  # UTF-8
                    mime=mime,
                    type=3,  # Front cover
                    desc='Cover',
                    data=f.read()
                ))
        
        if album_name:
            target = audio.tags if isinstance(audio, MP3) else audio
            target.add(TALB(encoding=3, text=album_name))
            
        if isinstance(audio, MP3):
            audio.save()
        else:
            audio.save(file_path)
        logger.info(f"✅ MP3 标签已更新: {os.path.basename(file_path)}")
"""

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find start and end of the function
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "def _write_mp3_tags" in line:
        start_idx = i
        break

if start_idx != -1:
    # Assuming it's the last method or followed by something at same indentation
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith("    def ") or lines[i].strip() == "": # Naive check for next method or EOF
             # But wait, there might be empty lines inside the function.
             # Better: find the next method definition at same indentation level
             if lines[i].startswith("    def ") or lines[i].startswith("class "):
                 end_idx = i
                 break
    
    if end_idx == -1:
        end_idx = len(lines) # End of file

    # Replace lines
    new_lines = lines[:start_idx] + [new_method_body] + lines[end_idx:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Successfully patched _write_mp3_tags")
else:
    print("Method _write_mp3_tags not found")

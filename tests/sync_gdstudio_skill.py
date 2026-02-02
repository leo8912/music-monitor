
import asyncio
import aiohttp
import os
import re
import sys
import datetime

# Paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_PATH = os.path.join(os.environ.get('USERPROFILE', ''), '.gemini', 'antigravity', 'skills', 'music-monitor-dev', 'SKILL.md')
API_DOC_PATH = os.path.join(ROOT_DIR, '文档', 'api使用方法.md')
API_BASE = "https://music-api.gdstudio.xyz/api.php"

async def test_source_stability(session, source):
    """Test if a source is currently returning 200 for a search request."""
    params = {"types": "search", "source": source, "name": "稻香", "count": 1}
    try:
        async with session.get(API_BASE, params=params, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                return source, True if isinstance(data, list) and len(data) > 0 else False
            return source, False
    except:
        return source, False

async def get_stable_sources():
    sources = ["netease", "tencent", "tidal", "spotify", "ytmusic", "qobuz", "joox", "deezer", "migu", "kugou", "kuwo", "ximalaya", "apple"]
    async with aiohttp.ClientSession() as session:
        tasks = [test_source_stability(session, s) for s in sources]
        results = await asyncio.gather(*tasks)
    return [s for s, stable in results if stable]

def update_api_doc(stable_sources):
    if not os.path.exists(API_DOC_PATH):
        print(f"API Doc file not found: {API_DOC_PATH}")
        return
    
    with open(API_DOC_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    now_str = datetime.date.today().strftime("%Y-%m-%d")
    stable_str = "、".join(stable_sources)
    
    # Update stable sources line
    content = re.sub(r"当前稳定音乐源（动态更新）：.*", f"当前稳定音乐源（动态更新）：{stable_str}", content)
    
    # Update update date line
    content = re.sub(r"更新日期：.*", f"更新日期：{now_str} (此文件为 Skill 系统的参考源，修改后请运行 tests/sync_gdstudio_skill.py 一键同步到 AI 技能中)", content)
    
    with open(API_DOC_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"API Documentation (Doc) updated with {len(stable_sources)} stable sources.")

def update_skill_md(stable_sources):
    if not os.path.exists(SKILL_PATH):
        print(f"Skill file not found: {SKILL_PATH}")
        return
    
    with open(SKILL_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_sources = ["netease", "tencent", "tidal", "spotify", "ytmusic", "qobuz", "joox", "deezer", "migu", "kugou", "kuwo", "ximalaya", "apple"]
    unstable = [s for s in all_sources if s not in stable_sources]
    now_str = datetime.date.today().strftime("%Y-%m-%d")
    
    new_stable_block = f"### Stable Sources (Verified {now_str})\n"
    for s in stable_sources:
        tag = "Recommend" if s in ['netease', 'kuwo', 'migu', 'joox'] else "External"
        new_stable_block += f"*   **{tag}**: `{s}`.\n"
    
    if unstable:
        new_stable_block += f"*   **Issues**: {', '.join([f'`{s}`' for s in unstable])} (Currently return 400 or empty).\n"
    
    replacement = f"## 6. GDStudio API Reference\n\nOfficial Instance: `{API_BASE}`\n\n{new_stable_block}"
    
    marker = "## 6. GDStudio API Reference"
    if marker in content:
        parts = content.split(marker)
        following = parts[1].split("\n## ")
        remaining = "\n## ".join(following[1:]) if len(following) > 1 else ""
        new_content = parts[0] + replacement + (("\n## " + remaining) if remaining else "")
        
        with open(SKILL_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Skill document updated.")
    else:
        print("Marker '## 6. GDStudio API Reference' not found in SKILL.md")

async def main():
    print("Scanning GDStudio API for source stability...")
    stable = await get_stable_sources()
    print(f"Stable sources found: {stable}")
    update_api_doc(stable)
    update_skill_md(stable)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from qqmusic_api import singer

async def generate_report():
    mid = "001BGUL33uMuK8"
    songs = await singer.get_songs(mid, num=100)
    
    report = f"# QQ音乐API返回歌曲列表对比\n\n"
    report += f"**歌手**: 李剑青 (MID: {mid})\n"
    report += f"**API返回数量**: {len(songs)} 首\n\n"
    report += "| 序号 | 歌曲名 | 专辑 | MID | 备注 |\n"
    report += "|:---:|:---|:---|:---|:---|\n"
    
    for i, song in enumerate(songs, 1):
        name = song.get('name', '').strip()
        album = song.get('album', {}).get('name', '')
        mid = song.get('mid', '')
        # 简单标记疑似问题歌曲
        note = ""
        if "瓦塔西" in name or "矿工" in name:
            note = "⚠️ 疑似非正式曲目"
        elif not album:
            note = "⚠️ 缺失专辑信息"
            
        report += f"| {i} | {name} | {album} | {mid} | {note} |\n"
        
    with open("qq_api_songs_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("报告已生成: qq_api_songs_report.md")

if __name__ == "__main__":
    asyncio.run(generate_report())

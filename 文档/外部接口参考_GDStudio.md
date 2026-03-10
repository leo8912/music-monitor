# 外部接口参考: GDStudio (Download API)

> **更新日期**: 2026-01-29  
> 此文件为 Skill 系统的参考源，修改后可能需要同步到 AI 技能中。

## 概述
GD Studio's Online Music Platform API (基于开源项目 Meting & MKOnlineMusicPlayer).
- **当前稳定音乐源**: `netease`, `joox`, `kuwo`
- **频率限制**: 5分钟内不超50次请求
- **免责声明**: 本站资源来自网络，仅限本人学习参考，严禁下载、传播或商用。

## 1. 搜索
`GET https://music-api.gdstudio.xyz/api.php`
- **参数**:
  - `types`: "search"
  - `source`: [MUSIC SOURCE] (如 `netease_album`)
  - `name`: [KEYWORD] (曲目名、歌手名、专辑名)
  - `count`: [PAGE LENGTH] (默认20)
  - `pages`: [PAGE NUM]
- **返回**: id（曲目ID）、name（歌曲名）、artist（歌手列表）、album（专辑名）、pic_id（专辑图ID）、url_id、lyric_id、source

## 2. 获取歌曲 (核心下载接口)
`GET https://music-api.gdstudio.xyz/api.php`
- **参数**:
  - `types`: "url"
  - `source`: [MUSIC SOURCE]
  - `id`: [TRACK ID]
  - `br`: 音质，可选 128/192/320/740/999 (999为无损默认)
- **返回**: url（音乐链接）、br（实际返回音质）、size（文件大小 KB）

## 3. 获取专辑图
`GET https://music-api.gdstudio.xyz/api.php`
- **参数**:
  - `types`: "pic"
  - `source`: [MUSIC SOURCE]
  - `id`: [PIC ID]
  - `size`: 300或500
- **返回**: url（专辑图链接）

## 4. 获取歌词
`GET https://music-api.gdstudio.xyz/api.php`
- **参数**:
  - `types`: "lyric"
  - `source`: [MUSIC SOURCE]
  - `id`: [LYRIC ID]
- **返回**: lyric（LRC格式）、tlyric（中文翻译）

---
trigger: always_on
---

# 项目开发规则总览
我是Windows系统环境，注意命令使用方式
## 1. 代码组织规范
- 每个文件代码、文档都要在开头注释备注下该文件的目的、作用。无法备注的文件要在文件夹下写一个md备注各文件作用。后期修改时也要同步修改备注，加上各文件的更新日志,后缀作者为ali
- 测试文件要都放在测试文件夹下，文件夹名测试分门别类
- 文档目录结构要规范清晰
- api和相关稳定等等放在文档文件夹下，文件夹名文档
- 所有需求、todo、修改方案计划、等等都放在需求文件夹下，文件夹名需求

GD Studio's Online Music Platform API
To report any unlawful activity or to protect your local authority, please contact us: gdstudio@email.com

Based on open-source projects Meting & MKOnlineMusicPlayer.

Written by metowolf & mengkun. Modded by GD Studio.

This platform is for study purposes only. Do NOT use it commercially!



免责声明：本站资源来自网络，仅限本人学习参考，严禁下载、传播或商用，如侵权请与我联系删除。继续使用将视为同意本声明

若使用本站提供的API，请注明出处“GD音乐台(music.gdstudio.xyz)”，尊重作者。使用过程如遇问题可B站私信：GD-Studio

当前稳定音乐源（动态更新）：netease、kuwo、joox

当前访问频率限制（动态更新）：5分钟内不超50次请求

更新日期：2025-12-3


搜索
API：https://music-api.gdstudio.xyz/api.php?types=search&source=[MUSIC SOURCE]&name=[KEYWORD]&count=[PAGE LENGTH]&pages=[PAGE NUM]

source：音乐源。可选项，参数值netease（默认）、tencent、tidal、spotify、ytmusic、qobuz、joox、deezer、migu、kugou、kuwo、ximalaya、apple。部分可能失效，建议使用稳定音乐源

* 高级用法：在音乐源后加上“_album”，如“netease_album”，可获取专辑中的曲目列表

name：关键字。必选项，关键字可以是曲目名、歌手名、专辑名

count：页面长度。可选项，一次返回显示多少内容，默认为20条

pages：页码。可选项，返回搜索结果第几页，默认为第1页

返回：id（曲目ID，即track_id）、name（歌曲名）、artist（歌手列表）、album（专辑名）、pic_id（专辑图ID）、url_id（URL ID，废弃）、lyric_id（歌词ID）、source（音乐源）


获取歌曲
API：https://music-api.gdstudio.xyz/api.php?types=url&source=[MUSIC SOURCE]&id=[TRACK ID]&br=[128/192/320/740/999]

source：音乐源。可选项，参数值netease（默认）、tencent、tidal、spotify、ytmusic、qobuz、joox、deezer、migu、kugou、kuwo、ximalaya、apple。部分可能失效，建议使用稳定音乐源

id：曲目ID。必选项，即track_id，根据音乐源不同，曲目ID的获取方式各不相同，可通过本站提供的搜索接口获取

br：音质。可选项，可选128、192、320、740、999（默认），其中740、999为无损音质

返回：url（音乐链接）、br（实际返回音质）、size（文件大小，单位为KB）


获取专辑图
API：https://music-api.gdstudio.xyz/api.php?types=pic&source=[MUSIC SOURCE]&id=[PIC ID]&size=[300/500]

source：音乐源。可选项，参数值netease（默认）、tencent、tidal、spotify、ytmusic、qobuz、joox、deezer、migu、kugou、kuwo、ximalaya、apple。部分可能失效，建议使用稳定音乐源

id：专辑图ID。必选项，专辑图ID即pic_id，可通过本站提供的搜索接口获取

size：图片尺寸。可选项，可选300（默认）、500，其中300为小图，500为大图，返回的图片不一定是300px或500px

返回：url（专辑图链接）


获取歌词
API：https://music-api.gdstudio.xyz/api.php?types=lyric&source=[MUSIC SOURCE]&id=[LYRIC ID]

source：音乐源。可选项，参数值netease（默认）、tencent、tidal、spotify、ytmusic、qobuz、joox、deezer、migu、kugou、kuwo、ximalaya、apple。部分可能失效，建议使用稳定音乐源

id：歌词ID。必选项，歌词ID即lyric_id（一般与曲目ID相同），可通过本站提供的搜索接口获取

返回：lyric（LRC格式的原语种歌词）、tlyric（LRC格式的中文翻译歌词，不一定会返回）

## 正确的qqmusic-api和pyncm调用方式

### 3.1 qqmusic-api 调用方式

**注意**: 部分接口（如歌词）需要 Cookie。在无 Cookie 环境下，请参考下方的替代方案。

1. **搜索歌手/歌曲** (无需 Cookie):
   ```python
   from qqmusic_api import search
   from qqmusic_api.search import SearchType
   
   # 搜索歌曲 (推荐用于获取元数据)
   results = await search.search_by_type("歌曲名 歌手名", search_type=SearchType.SONG, num=10)
   
   # 搜索歌手
   results = await search.search_by_type("歌手名", search_type=SearchType.SINGER, num=10)
   ```
   
2. **获取歌手歌曲列表** (无需 Cookie):
   ```python
   from qqmusic_api import singer
   
   # 获取歌手歌曲列表
   # 注意：返回的是列表(list)，不是字典
   song_list = await singer.get_songs("歌手MID", num=1000)
   ```
   
3. **获取歌曲详情** (⚠️ `song.query_song` 需要 Cookie):
   ```python
   # ❌ 错误示范 (需 Cookie，否则报错 10006)
   # detail = await song.query_song("歌曲MID")
   
   # ✅ 推荐替代方案 (无需 Cookie)
   # 通过搜索接口获取详情(专辑、封面等)
   results = await search.search_by_type("歌曲名 歌手名", search_type=SearchType.SONG, num=1)
   ```

4. **获取歌词**:
   ```python
   from qqmusic_api import lyric
   
   # 方式 A: 官方接口 (⚠️ 需要 Cookie)
   # lyrics = await lyric.get_lyric("歌曲MID")
   
   # 方式 B: 旧版接口 (✅ 无需 Cookie, 本项目已将其封装为 fallback)
   # URL: https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg
   # 只要正确伪造 Referer 为 https://y.qq.com/ 即可成功调用
   ```

### 3.3 自动重试机制 (新增)

针对 API 偶发失败（如 Code 2001），系统已在 `MusicProvider` 层内置自动重试机制：

- **策略**: 指数退避 (Index Backoff)
- **重试次数**: 3次
- **覆盖接口**: 
  - 搜索歌手 (`search_artist`)
  - 搜索歌曲 (`search_song`)
  - 获取歌曲列表 (`get_artist_songs`)

### pyncm调用方式

1. 搜索：
   ```python
   from pyncm import apis
   
   # 搜索歌曲 (stype=1) 或歌手 (stype=100)
   search_result = apis.cloudsearch.GetSearchResult("关键词", stype=1, limit=10)
   ```
   
2. 获取歌手歌曲：
   ```python
   # 获取歌手信息
   artist_search = apis.cloudsearch.GetSearchResult("歌手名", stype=100, limit=1)
   artist_id = artist_search['result']['artists'][0]['id']
   
   # 获取歌手歌曲列表
   artist_tracks = apis.artist.GetArtistTracks(artist_id)
   ```
   
3. 获取歌词：
   ```python
   # 获取歌词
   lyrics_info = apis.track.GetTrackLyrics(song_id)
   ```
   
4. 获取歌曲详情：
   ```python
   # 获取歌曲详情
   detail = apis.track.GetTrackDetail([song_id])
   ```

## 当前调用逻辑梳理

### 1. 搜索歌手
- 调用qqmusic-api、pyncm来搜索列表并提供头像、歌手名
- 进行去重处理
- 如本地数据库已有头像、歌手名，优先从本地数据库获取

### 2. 添加歌手后自动搜索歌曲列表
- 调用qqmusic-api、pyncm获取封面、专辑名、发布日期
- 进行去重处理
- 匹配歌手名、歌曲名一致性
- 如本地数据库已有相关数据，优先从本地数据库获取

### 3. 本地歌曲补全数据
- 调用qqmusic-api、pyncm补全元数据并写入数据库
- 补全内容包括：歌手名、歌手头像、歌曲名、封面、歌词、发布日期
- 如本地数据库已有相关数据，优先从本地数据库获取

### 4. 点击播放逻辑
- 优先匹配本地媒体库是否有匹配文件
- 如有匹配，直接本地播放，并将文件路径写入下载历史数据库
- 如无匹配，调用gdstudio搜索下载无损最高音质
- 搜索结果按所有音乐源顺序搜索，匹配最高音质
- 匹配歌手、专辑名一致性并打分
- 直到完全一致停止搜索并开始下载
- 确保不下载翻唱歌曲

### 5、下载逻辑
 - 下载只用gdstudio的api接口，注意5分钟50次的限制频率



app/services/
├── music_providers/          # 音乐源提供者(新)
│   ├── __init__.py
│   ├── base.py              # 基础抽象类
│   ├── netease_provider.py  # 网易云提供者(pyncm同步→异步)
│   ├── qqmusic_provider.py  # QQ音乐提供者(qqmusic-api同步→异步)
│   └── aggregator.py        # 聚合器(并发调用+打分去重)
│
├── download_service.py       # 下载服务(专用 gdstudio)
├── metadata_service.py       # 元数据补全服务（包括歌手、专辑名、歌曲名、封面、歌词、发布日期）
├── artist_service.py         # 歌手管理服务(新)
└── song_service.py           # 歌曲管理服务(新)
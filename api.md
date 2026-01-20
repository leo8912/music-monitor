# Music Monitor API 文档

> 本文档记录项目中使用的所有音乐API接口

---

## API 数据源架构

### 主数据源（官方SDK）
- **网易云音乐**: `pyncm` Python SDK
- **QQ音乐**: `qqmusic_api` Python SDK

### 备用数据源
- **GD Studio API**: `music-api.gdstudio.xyz`
- 用于：下载链接、封面图片、歌词（备用）

---

## 1. 搜索歌手

### 网易云音乐

**使用SDK**: `pyncm`

```python
import pyncm.apis.cloudsearch as cloudsearch

# 搜索歌手
data = cloudsearch.GetSearchResult(artist_name, stype=100)
```

**返回字段**:
```json
{
  "result": {
    "artists": [
      {
        "id": 12459252,
        "name": "宿羽阳",
        "picUrl": "https://p1.music.126.net/..."
      }
    ]
  }
}
```

### QQ音乐

**使用SDK**: `qqmusic_api`

```python
from qqmusic_api.search import search_by_type, SearchType

# 搜索歌手
data = await search_by_type(artist_name, SearchType.SINGER)
```

**返回字段**:
```json
[
  {
    "mid": "000GBnpV1IcEfl",
    "name": "宿羽阳"
  }
]
```

---

## 2. 获取歌手全部歌曲列表

### 网易云音乐

**使用SDK**: `pyncm`

```python
import pyncm.apis.artist as artist_api

# 获取歌手歌曲（最多500首）
data = artist_api.GetArtistSongs(artist_id, limit=500)
```

**返回字段**:
```json
{
  "code": 200,
  "total": 80,
  "songs": [
    {
      "id": 1974443814,
      "name": "歌曲名",
      "publishTime": 1640966400000,
      "album": {
        "name": "专辑名",
        "picUrl": "https://...",
        "publishTime": 1640966400000
      },
      "ar": [{"name": "歌手名"}]
    }
  ]
}
```

**获取信息**:
- ✅ 歌曲名: `song['name']`
- ✅ 发布日期: `song['publishTime']` (毫秒时间戳)
- ✅ 专辑名: `song['album']['name']`
- ✅ 封面URL: `song['album']['picUrl']`

### QQ音乐

**使用SDK**: `qqmusic_api`

```python
from qqmusic_api import singer

# 获取歌手歌曲（最多500首）
data = await singer.get_songs(artist_id, num=500)
```

**返回字段**:
```json
[
  {
    "mid": "001JHOcX12axZC",
    "name": "歌曲名",
    "time_public": "2021-12-31",
    "album": {
      "mid": "002fRO3M4JXJdp",
      "name": "专辑名"
    },
    "singer": [{"name": "歌手名"}]
  }
]
```

**获取信息**:
- ✅ 歌曲名: `song['name']`
- ✅ 发布日期: `song['time_public']` (YYYY-MM-DD格式)
- ✅ 专辑名: `song['album']['name']`
- ✅ 封面URL: 通过album_mid构造

**封面URL构造规则**:
```python
album_mid = song['album']['mid']
cover_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg"
```

---

## 3. 获取歌曲封面

### 方案1: SDK直接获取（推荐）

**网易云**: 歌曲数据中已包含 `album.picUrl`

**QQ音乐**: 通过album_mid构造URL
```python
cover_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg"
```

### 方案2: GD Studio API（备用）

当SDK没有返回封面时使用：

```
GET https://music-api.gdstudio.xyz/api.php
  ?types=pic
  &source=tencent
  &id={pic_id}
  &size=500
```

**参数**:
- `types`: 固定为 `pic`
- `source`: `netease` 或 `tencent`
- `id`: 专辑图ID
- `size`: `300` 或 `500`

**返回**:
```json
{
  "url": "https://p1.music.126.net/..."
}
```

---

## 4. 获取发布日期

### 网易云音乐

**直接从SDK获取**:
```python
# 优先级1: 歌曲发布时间
pub_ts = song.get('publishTime', 0)

# 优先级2: 专辑发布时间
if not pub_ts:
    pub_ts = song.get('album', {}).get('publishTime', 0)

# 转换为datetime（毫秒 -> 秒）
pub_date = datetime.fromtimestamp(pub_ts / 1000)
```

### QQ音乐

**直接从SDK获取**:
```python
pub_time_str = song.get('time_public', '')

# 支持多种格式
for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
    try:
        pub_date = datetime.strptime(pub_time_str, fmt)
        break
    except ValueError:
        continue
```

---

## 5. 获取专辑信息

### 网易云音乐

**直接从歌曲数据获取**:
```python
album_name = song.get('album', {}).get('name', '')
```

### QQ音乐

**直接从歌曲数据获取**:
```python
album_name = song.get('album', {}).get('name', '')
album_mid = song.get('album', {}).get('mid', '')
```

---

## 6. 下载歌曲

### GD Studio API

**下载链接API**:
```
GET https://music-api.gdstudio.xyz/api.php
  ?types=url
  &source=netease
  &id={song_id}
  &br={quality}
```

**参数**:
- `types`: 固定为 `url`
- `source`: `netease` 或 `tencent`
- `id`: 歌曲ID
- `br`: 音质 (128/320/999)

**音质参数**:
| br值 | 音质 | 格式 | 文件大小 |
|------|------|------|---------|
| 128 | 标准 | MP3 | ~4MB |
| 320 | 高音质 | MP3 | ~10MB |
| 999 | 无损 | FLAC | ~50MB |

**返回**:
```json
{
  "url": "https://m701.music.126.net/.../xxx.mp3",
  "size": 11161644,
  "br": 320
}
```

**多重回退策略**:
1. 原始ID + 高音质(999)
2. 搜索新ID + 高音质(999)  
3. 原始ID + 标准音质(128)
4. 跨源尝试: netease → tencent → kugou

---

## 7. 获取歌词

### GD Studio API（推荐）

**歌词API**:
```
GET https://music-api.gdstudio.xyz/api.php
  ?types=lyric
  &source=netease
  &id={song_id}
```

**参数**:
- `types`: 固定为 `lyric`
- `source`: `netease` 或 `tencent`
- `id`: 歌曲ID

**返回**:
```json
{
  "lyric": "[00:00.00]作词:...\n[00:05.20]歌词内容...",
  "tlyric": "[00:05.20]翻译内容..."
}
```

### OIAPI（备用，不推荐）

**酷狗歌词**:
```
GET https://oiapi.net/api/Kggc?msg={歌曲名}&n=1
```

**QQ音乐歌词**:
```
GET https://oiapi.net/api/QQMusicLyric?keyword={歌曲名}&n=1
```

> ⚠️ OIAPI不稳定，仅作备用

---

## 使用流程示例

### 完整流程：从搜索到下载

```python
# 1. 搜索歌手
import pyncm.apis.cloudsearch as cloudsearch
data = cloudsearch.GetSearchResult("宿羽阳", stype=100)
artist_id = data['result']['artists'][0]['id']

# 2. 获取歌手全部歌曲
import pyncm.apis.artist as artist_api
songs_data = artist_api.GetArtistSongs(artist_id, limit=500)
songs = songs_data['songs']

# 3. 提取信息
for song in songs:
    song_id = song['id']
    title = song['name']
    album = song['album']['name']
    cover = song['album']['picUrl']
    pub_time = song.get('publishTime', 0)
    
    # 4. 下载歌曲
    download_url = f"https://music-api.gdstudio.xyz/api.php?types=url&source=netease&id={song_id}&br=320"
    
    # 5. 获取歌词
    lyric_url = f"https://music-api.gdstudio.xyz/api.php?types=lyric&source=netease&id={song_id}"
```

---

## API限流说明

### GD Studio API
- **限制**: 5分钟50次请求
- **实现**: 令牌桶算法
- **位置**: `core/audio_downloader.py::RateLimiter`

### 官方SDK
- **pyncm**: 无明显限制
- **qqmusic_api**: 无明显限制

---

## 数据字段映射

| 需求 | 网易云字段 | QQ音乐字段 | 备用方案 |
|------|-----------|-----------|---------|
| 歌曲名 | `song['name']` | `song['name']` | - |
| 歌手名 | `song['ar'][0]['name']` | `song['singer'][0]['name']` | - |
| 专辑名 | `song['album']['name']` | `song['album']['name']` | - |
| 发布日期 | `song['publishTime']` (ms) | `song['time_public']` (str) | - |
| 封面URL | `song['album']['picUrl']` | 构造URL | GD Studio |
| 下载链接 | - | - | GD Studio ✅ |
| 歌词 | - | - | GD Studio ✅ |

---

## 注意事项

1. **版权**: 仅供学习研究，请勿商业使用
2. **数量限制**: SDK单次最多获取500首歌曲
3. **下载链接时效**: 建议获取后立即下载
4. **音质可用性**: 无损音质取决于音乐源
5. **限流控制**: 注意GD Studio的50次/5分钟限制

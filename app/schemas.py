"""
Schemas数据传输对象 - API数据模型定义

此文件定义了所有API的数据传输对象（DTO），包括：
- 认证相关的请求和响应模型
- 媒体资源相关的请求和响应模型
- 艺术家和歌曲相关的配置模型

Author: music-monitor development team
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

# --- Auth Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdateProfileRequest(BaseModel):
    username: str
    avatar: Optional[str] = None

# --- Media Models ---
class DownloadRequest(BaseModel):
    source: str
    song_id: str
    title: str
    artist: str
    album: str = ""
    pic_url: str = ""

class ArtistConfig(BaseModel):
    name: str
    id: Optional[str] = None
    source: Optional[str] = None
    avatar: Optional[str] = None

class SubscriptionResponse(BaseModel):
    success: bool
    message: str = ""
    status: Optional[str] = None # For compatibility


class SongResponse(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[int] = None
    cover_url: Optional[str] = None
    lyric_url: Optional[str] = None
    local_audio_path: Optional[str] = None
    is_favorite: bool = False
    source: Optional[str] = None
    media_id: Optional[str] = None
    unique_key: Optional[str] = None
    status: Optional[str] = None  # SongStatus enum value
    publish_time: Optional[str] = None
    quality: Optional[str] = "HQ"  # Quality enum: PQ, SQ, HQ, HR
    quality_details: Optional[str] = None  # e.g. "FLAC | SQ" or "24bit / 96kHz | HR"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    local_files: Optional[list] = []  # List of local file details
    available_sources: Optional[list] = []  # List of available sources (qqmusic, netease, local)

    model_config = ConfigDict(from_attributes=True)


# --- 阶段4.5: 统一响应模型 (OpenAPI schema 覆盖) ---

class VersionResponse(BaseModel):
    """系统版本信息"""
    backend_version: str
    frontend_version: str
    version: str
    build_date: str
    name: str
    author: str


class TaskControlResponse(BaseModel):
    """任务暂停/恢复/取消操作响应"""
    status: str
    task_id: str


class SystemStatusJob(BaseModel):
    """调度任务信息"""
    id: str
    next_run: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """系统运行状态"""
    status: str
    jobs: list[SystemStatusJob] = []


class ProfileStatsResponse(BaseModel):
    """个人中心统计"""
    artist_count: int = 0
    song_count: int = 0
    cache_size: str = "0 MB"


class AuthCheckResponse(BaseModel):
    """鉴权状态检查"""
    authenticated: bool
    user: Optional[str] = None
    avatar: Optional[str] = None
    enabled: bool


class UserResponse(BaseModel):
    """当前登录用户信息 (GET /api/user)"""
    username: str
    avatar: Optional[str] = None


class LoginResponse(BaseModel):
    """登录/登出响应"""
    success: Optional[bool] = None
    message: Optional[str] = None


class DownloadAudioResponse(BaseModel):
    """音频下载结果"""
    local_path: Optional[str] = None
    local_audio_path: Optional[str] = None
    quality: Optional[int] = None
    has_lyric: Optional[bool] = None


class MobileMetadataResponse(BaseModel):
    """移动端签名元数据响应"""
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    cover: Optional[str] = None
    lyrics: Optional[str] = None
    audio_url: Optional[str] = None
    source: Optional[str] = None
    is_favorite: Optional[bool] = None
    local_audio_path: Optional[str] = None
    id: Optional[str] = None
    unique_key: Optional[str] = None


class ArtistListItem(BaseModel):
    """关注歌手列表项"""
    name: str
    id: str
    source: Optional[str] = None
    sources: list[str] = []
    avatar: Optional[str] = None
    song_count: int = 0


class ArtistDetailResponse(BaseModel):
    """艺人详情 (歌曲列表 + 专辑分组)"""
    id: int
    name: str
    avatar: Optional[str] = None
    sources: list[str] = []
    songs: list[dict] = []
    albums: list[dict] = []


class ScanResultResponse(BaseModel):
    """系统扫描结果"""
    status: Optional[str] = None
    new_files_found: Optional[int] = 0
    metadata_enriched: Optional[int] = 0
    message: Optional[str] = None


class ScanLibraryResponse(BaseModel):
    """本地库扫描结果 (library /scan)"""
    success: bool = True
    new_files_found: int = 0
    removed_files_count: int = 0
    status: Optional[str] = None


class GenericActionResponse(BaseModel):
    """通用操作响应 (success/message/status 组合)"""
    success: Optional[bool] = None
    message: Optional[str] = None
    status: Optional[str] = None
    task_id: Optional[str] = None
    url: Optional[str] = None
    unique_key: Optional[str] = None
    count: Optional[int] = None
    connected: Optional[bool] = None


class SongInfoResponse(BaseModel):
    """在线歌曲信息 (MusicProvider SongInfo.to_dict)"""
    title: str
    artist: str
    album: str
    source: str
    id: str
    cover_url: str = ""
    duration: int = 0
    publish_time: str = ""


class ArtistInfoResponse(BaseModel):
    """在线歌手信息 (MusicProvider ArtistInfo.to_dict)"""
    name: str
    source: str
    id: str
    avatar: str
    songCount: int = 0
    extra_ids: dict = {}


class ArtistOnlineSongsResponse(BaseModel):
    """歌手在线歌曲列表"""
    source: str
    artist_id: str
    offset: int
    limit: int
    items: list[SongInfoResponse] = []
    total: int = 0


class LocalizeAvatarResponse(BaseModel):
    """歌手头像本地化结果"""
    name: str
    avatar: str = ""


class EnrichResponse(BaseModel):
    """元数据补全结果"""
    success: Optional[bool] = None
    enriched_count: Optional[int] = None
    message: Optional[str] = None


class FavoriteResponse(BaseModel):
    """收藏切换结果"""
    song_id: Optional[int] = None
    is_favorite: Optional[bool] = None
    new_path: Optional[str] = None
    message: Optional[str] = None


class DeleteResponse(BaseModel):
    """删除操作响应"""
    success: Optional[bool] = None
    message: Optional[str] = None
    file_deleted: Optional[bool] = None


class RedownloadResponse(BaseModel):
    """重新下载结果"""
    success: bool
    song: Optional[dict] = None


class RefreshArtistResponse(BaseModel):
    """刷新歌手结果"""
    success: bool
    new_songs_count: int = 0


class FixQualityResponse(BaseModel):
    """音质修复结果"""
    success: Optional[bool] = None
    updated: Optional[int] = None
    details: Optional[list] = None
    message: Optional[str] = None
    error: Optional[str] = None


class MetadataFetchResponse(BaseModel):
    """元数据获取结果 (歌词/封面)"""
    success: bool
    lyrics: Optional[str] = None
    has_lyrics: Optional[bool] = None
    has_cover: Optional[bool] = None
    cover_url: Optional[str] = None
    error: Optional[str] = None


class SearchDownloadItemResponse(BaseModel):
    """搜索结果下载项 (discovery /search_download)"""
    id: str
    source: str
    title: str
    artist: str
    album: str = ""
    cover_url: str = ""
    quality: Optional[int] = None
    size: Optional[float] = None
    publish_time: str = ""


class ProbeQualityResponse(BaseModel):
    """音质探测结果 (discovery /probe_qualities)"""
    quality: int
    available: bool
    actual_br: Optional[int] = None
    size: Optional[float] = None


class ApiHealthItemResponse(BaseModel):
    """单源接口健康检查结果 (discovery /api_health)"""
    source: str
    # search 状态: ok / empty(200 但无结果) / unsupported(400) / error
    search_status: str
    search_count: int = 0
    search_latency_ms: int = 0
    # url 状态: ok / empty(url 为空) / unsupported(400) / error / skip(未测)
    url_status: str = ""
    url_latency_ms: int = 0
    message: str = ""


class ApiHealthResponse(BaseModel):
    """GDStudio API 健康检查总结果 (discovery /api_health)"""
    tested_at: str
    cached: bool
    ttl_seconds: int
    total: int
    items: list[ApiHealthItemResponse]


class DownloadFromSearchResponse(BaseModel):
    """从搜索结果直接下载结果 (library /download)"""
    success: bool
    song: Optional[dict] = None
    message: Optional[str] = None

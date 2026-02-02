"""
Schemas数据传输对象 - API数据模型定义

此文件定义了所有API的数据传输对象（DTO），包括：
- 认证相关的请求和响应模型
- 媒体资源相关的请求和响应模型
- 艺术家和歌曲相关的配置模型

Author: music-monitor development team
"""
from pydantic import BaseModel
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
    status: Optional[str] = None
    publish_time: Optional[str] = None
    quality: Optional[str] = "HQ" # SQ, HQ, Hi-Res
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

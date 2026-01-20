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

"""
音乐源提供者模块

此模块提供统一的音乐源访问接口,支持:
- 网易云音乐 (pyncm)
- QQ音乐 (qqmusic-api)

Author: google
Created: 2026-01-23
"""

from .base import MusicProvider, ArtistInfo, SongInfo
from .netease_provider import NeteaseProvider
from .qqmusic_provider import QQMusicProvider
from .aggregator import MusicAggregator

__all__ = [
    'MusicProvider',
    'ArtistInfo',
    'SongInfo',
    'NeteaseProvider',
    'QQMusicProvider',
    'MusicAggregator',
]

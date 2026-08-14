"""
Domain Enums - 纯业务枚举

定义所有业务域的枚举类型，不包含框架依赖。
"""

from enum import Enum


class SongStatus(str, Enum):
    """歌曲状态枚举"""
    PENDING = "PENDING"  # 待下载
    DOWNLOADED = "DOWNLOADED"  # 已下载
    ERROR = "ERROR"  # 下载错误
    DELETED = "DELETED"  # 已删除


class SourceName(str, Enum):
    """音乐来源枚举"""
    NETEASE = "netease"
    QQMUSIC = "qqmusic"
    LOCAL = "local"
    GDSTUDIO = "gdstudio"


class Quality(str, Enum):
    """音质枚举"""
    PQ = "PQ"  # 普通品质 (128kbps)
    SQ = "SQ"  # 标准品质 (320kbps)
    HQ = "HQ"  # 高品质 (FLAC)
    HR = "HR"  # 超高品质 (Hi-Res, 24bit/96kHz+)


class NotificationType(str, Enum):
    """通知类型枚举"""
    WECOM = "wecom"
    TELEGRAM = "telegram"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型枚举"""
    DOWNLOAD = "download"
    METADATA_HEAL = "metadata_heal"
    SCAN = "scan"
    MONITOR = "monitor"

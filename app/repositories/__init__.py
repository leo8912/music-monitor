"""
Repository层 - 数据访问抽象层

此目录包含所有数据访问对象（Repository），用于封装数据库CRUD操作。
遵循Repository设计模式，为上层服务提供统一的数据访问接口。

主要职责：
- 封装SQLAlchemy数据库操作
- 提供类型安全的数据访问方法
- 实现常见的CRUD操作（Create, Read, Update, Delete）
- 处理数据库查询构建

使用方式：
- 继承BaseRepository以获得通用CRUD功能
- 为特定实体实现专用方法
- 在Service层中注入Repository实例

Author: music-monitor development team

更新日志:
- 2026-01-22: 添加 MediaRecordRepository
"""
from .base import BaseRepository
from .song import SongRepository
from .artist import ArtistRepository
from .media_record import MediaRecordRepository

__all__ = ["BaseRepository", "SongRepository", "ArtistRepository", "MediaRecordRepository"]
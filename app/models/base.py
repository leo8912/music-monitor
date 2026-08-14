"""
Base模型 - 数据库基础配置

此文件定义了SQLAlchemy的基础配置，包括数据库引擎、会话管理器和基础模型类。
提供异步数据库连接支持和基础的数据库会话生成器。

Author: music-monitor development team
"""
# 注意：declarative_base 只保留 sqlalchemy.orm 版本（SQLAlchemy 2.0 官方位置）。
# 原先第 9 行还从已废弃的 sqlalchemy.ext.declarative 重复导入了一次，被本行覆盖，
# 属死代码且会触发 MovedIn20Warning，已删除。
from sqlalchemy.orm import declarative_base

Base = declarative_base()


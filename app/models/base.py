"""
Base模型 - 数据库基础配置

此文件定义了SQLAlchemy的基础配置，包括数据库引擎、会话管理器和基础模型类。
提供异步数据库连接支持和基础的数据库会话生成器。

Author: music-monitor development team
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()


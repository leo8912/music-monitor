from sqlalchemy import Column, Integer, JSON, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class SystemSettings(Base):
    """
    系统配置表 (单例表)
    存储所有动态业务配置，替代 config.yaml 中的业务部分
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)
    
    # --- 下载设置 ---
    # JSON 结构: { "concurrent": 3, "quality": 999, "sources": ["netease", "qqmusic"], "retry_attempts": 3, "timeout": 30 }
    download_settings = Column(JSON, default=dict)

    # --- 监控设置 ---
    # JSON 结构: { "enabled": true, "interval": 60 }
    monitor_settings = Column(JSON, default=dict)

    # --- 通知设置 ---
    # JSON 结构: { "wecom": { "enabled": false, "token": "..." }, "telegram": { ... } }
    notify_settings = Column(JSON, default=dict)

    # --- 元数据设置 ---
    # JSON 结构: { "enable_cover": true, "enable_lyrics": true, "cover_priority": ["plugin"], ... }
    metadata_settings = Column(JSON, default=dict)
    
    # --- 调度器设置 ---
    # JSON 结构: { "check_interval_minutes": 60, "cleanup_interval_hours": 24 }
    scheduler_settings = Column(JSON, default=dict)

    # --- 系统保留/覆盖 ---
    # 预留用于存储一些不在上述分类中的杂项，或者未来扩展
    system_overrides = Column(JSON, default=dict)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

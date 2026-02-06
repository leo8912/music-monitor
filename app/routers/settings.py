from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
from pydantic import BaseModel

from core.database import get_async_session
from app.models.settings import SystemSettings
from core.config_manager import get_config_manager, reload_config
import logging

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)

# --- Schemas ---
# 定义 Pydantic 模型用于验证
class SettingsUpdate(BaseModel):
    # 全部可选，支持局部更新
    download: Optional[Dict[str, Any]] = None
    monitor: Optional[Dict[str, Any]] = None
    notify: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    scheduler: Optional[Dict[str, Any]] = None
    system: Optional[Dict[str, Any]] = None

class TestNotifyRequest(BaseModel):
    type: str # wecom, telegram
    config: Optional[Dict[str, Any]] = None # 可选，如果不传则使用当前保存的配置

# --- Endpoints ---

@router.get("", response_model=Dict[str, Any])
async def get_settings():
    """
    获取当前所有配置 (混合了 YAML 和 DB 的最终结果)
    """
    # 直接返回内存中的 Config，它是已经 Merge 过的最终状态
    manager = get_config_manager()
    # 强制刷新以确保从 DB 获取最新
    manager.reload()
    return manager._config

@router.patch("", response_model=Dict[str, Any])
async def update_settings(
    update_data: SettingsUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新业务配置 (写入数据库)
    """
    try:
        # 1. 获取或创建 DB 记录
        result = await db.execute(select(SystemSettings).filter_by(id=1))
        settings = result.scalars().first()
        
        if not settings:
            settings = SystemSettings()
            db.add(settings)
        
        # 2. 更新字段 (JSON Merge)
        # 注意：这里我们做简单的顶层替换/合并。
        # 如果需要更深层的 Patch，需要在 python 层面做 merge。
        # 这里假设前端传来的是完整的 section (例如 download 全部字段)，或者是需要我们 merge。
        # 为了安全，建议前端传来的 section 与 DB 中的进行 merge。
        
        current_config = get_config_manager()
        
        def merge_section(current_db_val, new_val):
            # 如果 DB 为空，取 ConfigManager 里的当前值作为基准 (含 Defaults)
            base = current_db_val or {}
            # Deep merge logic inside helper? 
            # 简单起见，我们使用 Python dict update，支持增量更新
            if not base:
                base = {}
            base.update(new_val)
            return base

        if update_data.download:
            settings.download_settings = merge_section(settings.download_settings, update_data.download)
            
        if update_data.monitor:
            settings.monitor_settings = merge_section(settings.monitor_settings, update_data.monitor)
            
        if update_data.notify:
            settings.notify_settings = merge_section(settings.notify_settings, update_data.notify)
            
        if update_data.metadata:
            settings.metadata_settings = merge_section(settings.metadata_settings, update_data.metadata)
            
        if update_data.scheduler:
            settings.scheduler_settings = merge_section(settings.scheduler_settings, update_data.scheduler)
            
        if update_data.system:
            # Map 'system' update to 'system_overrides' column
            # But system_overrides might contain other overrides too. 
            # We should wrap it in 'system' key if we want to follow structure, OR just flat merge if overrides are flat.
            # ConfigManager expects: { "system": { "external_url": "..." } }
            # So we should store { "system": { ... } } inside system_overrides?
            # ConfigManager._load_from_db says: `if settings.system_overrides: merge(config_ref, settings.system_overrides)`
            # So safe way is: settings.system_overrides = { "system": ... } merged with existing.
            
            # Since system_overrides is a JSON dict of *overrides* (root level),
            # we should update the "system" key inside it.
            
            current_overrides = settings.system_overrides or {}
            # Ensure it's a dict
            if not isinstance(current_overrides, dict): current_overrides = {}
            
            # Merge logic for system section within overrides
            current_system_section = current_overrides.get("system", {})
            new_system_section = update_data.system
            
            # Merge
            if isinstance(current_system_section, dict):
                current_system_section.update(new_system_section)
            else:
                current_system_section = new_system_section
                
            current_overrides["system"] = current_system_section
            settings.system_overrides = current_overrides.copy() # triggers SA update check

        await db.commit()
        
        # 3. 触发配置重载 (更新内存)
        # Reload runs synchronously, so we can call it here or in background?
        # reload_config() calls Sync DB logic.
        # But we are in async environment. 
        # get_config_manager().reload() uses synchronous engine creation. It should be fine.
        reload_config()
        
        return get_config_manager()._config
        
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-notify")
async def test_notify(req: TestNotifyRequest):
    """
    测试通知配置
    """
    from app.services.notification import NotificationService
    # Temporarily construct a service with specific config or load from system
    
    cfg = req.config
    if not cfg:
        # Use system config
        full_config = get_config_manager().get("notify", {})
        if req.type == "wecom":
            cfg = full_config.get("wecom")
        elif req.type == "telegram":
            cfg = full_config.get("telegram")
            
    if not cfg:
        raise HTTPException(status_code=400, detail="Configuration not found")
        
    try:
        # 这里需要 NotificationService 支持传入 config 发送
        # 目前 NotificationService 可能只读全局配置。
        # 我们可以临时实例化一个 sender。
        
        success = False
        error_msg = ""
        
        logger.info(f"Testing notification for {req.type} with config provided: {bool(req.config)}")

        if req.type == "wecom":
            try:
                # 动态导入避免循环依赖
                # 使用正确的模块路径
                from app.notifiers.wecom import WeComNotifier
                from app.notifiers.telegram import TelegramNotifier
                
                notifier = WeComNotifier(
                    corp_id=cfg.get("corp_id"),
                    secret=cfg.get("secret"),
                    agent_id=cfg.get("agent_id")
                )
                
                # WeCom usually requires caching token, but for test we try to send directly
                logger.info("Attempting to send test message via WeCom...")
                
                # We need to bypass cache or manually init connection
                # verify credentials by getting token
                # 注意：根据 WeComNotifier 实现，可能需要 explicit connect 或者 send_text 会自动处理
                # 安全起见，直接调用 send_text 看是否报错
                
                # 尝试强制刷新 token (如果支持) 或直接发送
                # 假设 send_text 会自动 get_token
                await notifier.send_text("Music Monitor: 测试通知配置成功 ✅")
                success = True
                logger.info("WeCom test message sent successfully")
                
            except Exception as e:
                success = False
                error_msg = str(e)
                logger.error(f"WeCom test failed: {e}", exc_info=True)

        elif req.type == "telegram":
            # TODO: Impl Telegram test
            logger.warning("Telegram test not implemented yet")
            error_msg = "Telegram test not implemented yet"
            pass
            
        if success:
            return {"success": True, "message": "测试发送成功"}
        else:
            return {"success": False, "message": f"测试失败: {error_msg}"}
            
    except Exception as e:
        logger.error(f"Test notify endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

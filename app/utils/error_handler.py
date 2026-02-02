# -*- coding: utf-8 -*-
"""
错误处理工具

提供统一的错误处理装饰器和工具函数，用于服务层的异常处理和降级。

Author: google
Created: 2026-02-02
"""
from functools import wraps
from typing import Callable, Any, Optional
import logging

from app.exceptions import (
    BaseError,
    DownloadError,
    MetadataError,
    DatabaseError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError
)

logger = logging.getLogger(__name__)


def handle_service_errors(
    fallback_value: Any = None,
    raise_on_critical: bool = True,
    log_level: str = "error"
):
    """
    服务层错误处理装饰器
    
    自动捕获和处理服务层异常，提供降级和日志记录。
    
    Args:
        fallback_value: 发生错误时返回的降级值
        raise_on_critical: 是否在关键错误时重新抛出异常
        log_level: 日志级别 (debug, info, warning, error, critical)
    
    Example:
        @handle_service_errors(fallback_value=[], raise_on_critical=False)
        async def get_songs(self, artist_id):
            # 如果发生错误，返回空列表
            return await self.repo.get_songs(artist_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            
            except DownloadError as e:
                _log(log_level, f"下载失败: {e.message}", exc_info=e)
                # 下载错误通常可以降级
                return fallback_value
            
            except MetadataError as e:
                _log("warning", f"元数据获取失败: {e.message}", exc_info=e)
                # 元数据错误可以降级，使用默认值
                return fallback_value
            
            except RateLimitError as e:
                _log("warning", f"API 频率限制: {e.message}", exc_info=e)
                # 频率限制错误，建议降级
                return fallback_value
            
            except NetworkError as e:
                _log("error", f"网络错误: {e.message}", exc_info=e)
                if raise_on_critical:
                    raise
                return fallback_value
            
            except DatabaseError as e:
                _log("error", f"数据库错误: {e.message}", exc_info=e)
                # 数据库错误通常是关键错误
                if raise_on_critical:
                    raise
                return fallback_value
            
            except ServiceUnavailableError as e:
                _log("warning", f"服务不可用: {e.message}", exc_info=e)
                return fallback_value
            
            except BaseError as e:
                _log(log_level, f"业务异常: {e.message}", exc_info=e)
                if raise_on_critical:
                    raise
                return fallback_value
            
            except Exception as e:
                _log("critical", f"未预期的错误: {str(e)}", exc_info=e)
                # 未知错误，重新抛出
                if raise_on_critical:
                    raise
                return fallback_value
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            
            except DownloadError as e:
                _log(log_level, f"下载失败: {e.message}", exc_info=e)
                return fallback_value
            
            except MetadataError as e:
                _log("warning", f"元数据获取失败: {e.message}", exc_info=e)
                return fallback_value
            
            except BaseError as e:
                _log(log_level, f"业务异常: {e.message}", exc_info=e)
                if raise_on_critical:
                    raise
                return fallback_value
            
            except Exception as e:
                _log("critical", f"未预期的错误: {str(e)}", exc_info=e)
                if raise_on_critical:
                    raise
                return fallback_value
        
        # 根据函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def handle_download_errors(fallback_value: Any = None):
    """
    下载错误处理装饰器（简化版）
    
    专门用于下载相关方法，自动处理下载失败、网络错误等。
    """
    return handle_service_errors(
        fallback_value=fallback_value,
        raise_on_critical=False,
        log_level="warning"
    )


def handle_metadata_errors(fallback_value: Any = None):
    """
    元数据错误处理装饰器（简化版）
    
    专门用于元数据获取方法，失败时返回降级值。
    """
    return handle_service_errors(
        fallback_value=fallback_value,
        raise_on_critical=False,
        log_level="info"
    )


def _log(level: str, message: str, exc_info: Exception = None):
    """内部日志函数"""
    log_func = getattr(logger, level, logger.error)
    if exc_info:
        log_func(message, exc_info=True)
    else:
        log_func(message)


def safe_execute(func: Callable, *args, default=None, **kwargs):
    """
    安全执行函数，捕获所有异常并返回默认值
    
    Args:
        func: 要执行的函数
        *args: 函数参数
        default: 发生异常时返回的默认值
        **kwargs: 函数关键字参数
    
    Returns:
        函数执行结果或默认值
    
    Example:
        result = safe_execute(risky_function, arg1, arg2, default=[])
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"安全执行失败: {str(e)}")
        return default


async def safe_execute_async(func: Callable, *args, default=None, **kwargs):
    """
    安全执行异步函数，捕获所有异常并返回默认值
    
    Args:
        func: 要执行的异步函数
        *args: 函数参数
        default: 发生异常时返回的默认值
        **kwargs: 函数关键字参数
    
    Returns:
        函数执行结果或默认值
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"安全执行失败: {str(e)}")
        return default


class ErrorContext:
    """
    错误上下文管理器
    
    用于在代码块中自动捕获和处理异常。
    
    Example:
        with ErrorContext("获取歌曲列表", default_value=[]):
            songs = await get_songs()
        # 如果发生错误，songs 将是 []
    """
    
    def __init__(
        self,
        operation: str,
        default_value: Any = None,
        raise_on_error: bool = False
    ):
        self.operation = operation
        self.default_value = default_value
        self.raise_on_error = raise_on_error
        self.result = default_value
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"{self.operation} 失败: {exc_val}", exc_info=True)
            if self.raise_on_error:
                return False  # 重新抛出异常
            return True  # 抑制异常
        return True

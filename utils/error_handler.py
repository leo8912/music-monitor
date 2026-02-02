"""
增强的错误处理和日志记录模块
此模块提供统一的错误处理机制和结构化日志记录，
帮助提升系统的可维护性和调试能力。

Author: ali
Update Log:
2024-12-19: 创建增强错误处理器和结构化日志记录
"""
import asyncio
import functools
import logging
import traceback
import time
from datetime import datetime
from typing import Any, Callable, Optional, Dict
from functools import wraps
from app.exceptions import BusinessError, ValidationError


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def _log_structured(self, level: int, msg: str, extra: Dict[str, Any] = None, 
                       exc_info: bool = False):
        """记录结构化日志"""
        # [Defensive] Filter out standard LogRecord attributes to prevent overwrite errors
        reserved = {
            'args', 'asctime', 'created', 'exc_info', 'filename', 'funcName', 
            'levelname', 'levelno', 'lineno', 'module', 'msecs', 'msg', 
            'name', 'pathname', 'process', 'processName', 'relativeCreated', 
            'stack_info', 'thread', 'threadName', 'exc_text'
        }
        
        log_extra = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.logger.name,
        }
        
        if extra:
            # Only add keys that don't conflict with reserved logging attributes
            for k, v in extra.items():
                if k not in reserved:
                    log_extra[k] = v
            
        self.logger.log(level, msg, extra=log_extra, exc_info=exc_info)
    
    def info(self, msg: str, extra: Dict[str, Any] = None):
        """记录INFO级别日志"""
        self._log_structured(logging.INFO, msg, extra)
    
    def warning(self, msg: str, extra: Dict[str, Any] = None):
        """记录WARNING级别日志"""
        self._log_structured(logging.WARNING, msg, extra)
    
    def error(self, msg: str, extra: Dict[str, Any] = None, exc_info: bool = False):
        """记录ERROR级别日志"""
        self._log_structured(logging.ERROR, msg, extra, exc_info)
    
    def debug(self, msg: str, extra: Dict[str, Any] = None):
        """记录DEBUG级别日志"""
        self._log_structured(logging.DEBUG, msg, extra)


def enhanced_error_handler(
    func: Optional[Callable] = None,
    *,
    reraise: bool = True,
    log_level: int = logging.ERROR,
    default_return: Any = None,
    retry_times: int = 0,
    retry_delay: float = 1.0
):
    """
    增强的错误处理装饰器
    
    Args:
        func: 被装饰的函数
        reraise: 是否重新抛出异常
        log_level: 日志级别
        default_return: 默认返回值
        retry_times: 重试次数
        retry_delay: 重试延迟（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retry_times + 1):
                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # 记录成功执行的日志
                    logger = StructuredLogger(f"function.{func.__name__}")
                    logger.info(
                        f"Function {func.__name__} executed successfully",
                        extra={
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "args_count": len(args),
                            "kwargs_count": len(kwargs),
                        }
                    )
                    return result
                    
                except ValidationError as e:
                    # 验证错误 - 通常是用户输入问题
                    logger = StructuredLogger(f"validation.{func.__name__}")
                    logger.error(
                        f"Validation error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "func_args": _safe_args_repr(args),
                            "func_kwargs": _safe_kwargs_repr(kwargs),
                        },
                        exc_info=True
                    )
                    if reraise:
                        raise
                    return default_return
                    
                except BusinessError as e:
                    # 业务错误 - 通常是预期的业务逻辑错误
                    logger = StructuredLogger(f"business.{func.__name__}")
                    logger.error(
                        f"Business error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "func_args": _safe_args_repr(args),
                            "func_kwargs": _safe_kwargs_repr(kwargs),
                        },
                        exc_info=True
                    )
                    if reraise:
                        raise
                    return default_return
                    
                except Exception as e:
                    last_exception = e
                    error_type = type(e).__name__
                    
                    logger = StructuredLogger(f"error.{func.__name__}")
                    logger.error(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": error_type,
                            "error_message": str(e),
                            "func_args": _safe_args_repr(args),
                            "func_kwargs": _safe_kwargs_repr(kwargs),
                            "traceback": traceback.format_exc(),
                        },
                        exc_info=True
                    )
                    
                    # 如果不是最后一次重试，等待后重试
                    if attempt < retry_times:
                        logger.info(
                            f"Retrying {func.__name__} after error (attempt {attempt + 1}/{retry_times + 1})",
                            extra={"attempt": attempt + 1}
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        if reraise:
                            raise
                        return default_return
            
            # 如果所有重试都失败，返回最后一个异常
            if last_exception and reraise:
                raise last_exception
            return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retry_times + 1):
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # 记录成功执行的日志
                    logger = StructuredLogger(f"function.{func.__name__}")
                    logger.info(
                        f"Function {func.__name__} executed successfully",
                        extra={
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "args_count": len(args),
                            "kwargs_count": len(kwargs),
                        }
                    )
                    return result
                    
                except ValidationError as e:
                    # 验证错误
                    logger = StructuredLogger(f"validation.{func.__name__}")
                    logger.error(
                        f"Validation error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "func_args": _safe_args_repr(args),
                            "func_kwargs": _safe_kwargs_repr(kwargs),
                        },
                        exc_info=True
                    )
                    if reraise:
                        raise
                    return default_return
                    
                except BusinessError as e:
                    # 业务错误
                    logger = StructuredLogger(f"business.{func.__name__}")
                    logger.error(
                        f"Business error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "func_args": _safe_args_repr(args),
                            "func_kwargs": _safe_kwargs_repr(kwargs),
                        },
                        exc_info=True
                    )
                    if reraise:
                        raise
                    return default_return
                    
                except Exception as e:
                    last_exception = e
                    error_type = type(e).__name__
                    
                    logger = StructuredLogger(f"error.{func.__name__}")
                    logger.error(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": error_type,
                            "error_message": str(e),
                            "func_args": _safe_args_repr(args),
                            "func_kwargs": _safe_kwargs_repr(kwargs),
                            "traceback": traceback.format_exc(),
                        },
                        exc_info=True
                    )
                    
                    # 如果不是最后一次重试，等待后重试
                    if attempt < retry_times:
                        logger.info(
                            f"Retrying {func.__name__} after error (attempt {attempt + 1}/{retry_times + 1})",
                            extra={"attempt": attempt + 1}
                        )
                        time.sleep(retry_delay)
                    else:
                        if reraise:
                            raise
                        return default_return
            
            # 如果所有重试都失败，返回最后一个异常
            if last_exception and reraise:
                raise last_exception
            return default_return
        
        # 根据函数是否是异步来返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    if func is None:
        # 装饰器被调用时带有参数
        return decorator
    else:
        # 装饰器被直接调用
        return decorator(func)


def _safe_args_repr(args) -> str:
    """安全地表示函数参数，避免敏感信息泄露"""
    try:
        # 限制参数数量和长度，避免日志过大
        safe_args = []
        for arg in args:
            arg_str = repr(arg)
            if len(arg_str) > 200:
                arg_str = arg_str[:200] + "..."
            safe_args.append(arg_str)
        return str(safe_args)[:500]  # 限制总长度
    except:
        return "<unrepresentable args>"


def _safe_kwargs_repr(kwargs) -> str:
    """安全地表示函数关键字参数，避免敏感信息泄露"""
    try:
        # 移除可能包含敏感信息的键
        sensitive_keys = {'password', 'token', 'secret', 'key', 'auth'}
        safe_kwargs = {}
        for k, v in kwargs.items():
            if k.lower() in sensitive_keys:
                safe_kwargs[k] = "<redacted>"
            else:
                v_str = repr(v)
                if len(v_str) > 200:
                    v_str = v_str[:200] + "..."
                safe_kwargs[k] = v_str
        result = str(safe_kwargs)
        return result[:500]  # 限制总长度
    except:
        return "<unrepresentable kwargs>"


class ErrorHandler:
    """错误处理器类，提供集中化的错误处理功能"""
    
    def __init__(self, logger_name: str = "error_handler"):
        self.logger = StructuredLogger(logger_name)
    
    async def handle_api_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        处理API错误并返回标准化错误响应
        
        Args:
            error: 捕获的异常
            context: 错误上下文信息
            
        Returns:
            标准化错误响应
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        self.logger.error(
            f"API error in {context}: {error_msg}",
            extra={
                "context": context,
                "error_type": error_type,
                "error_message": error_msg,
                "traceback": traceback.format_exc(),
            },
            exc_info=True
        )
        
        # 根据错误类型返回不同的响应
        if isinstance(error, ValidationError):
            return {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": error_msg,
                "details": getattr(error, 'details', {}),
            }
        elif isinstance(error, BusinessError):
            return {
                "success": False,
                "error": "BUSINESS_ERROR",
                "message": error_msg,
            }
        else:
            return {
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": "Internal server error occurred",
            }
    
    def log_performance(self, operation: str, duration: float, 
                      success: bool = True, extra: Dict[str, Any] = None):
        """
        记录性能指标
        
        Args:
            operation: 操作名称
            duration: 执行时长
            success: 是否成功
            extra: 额外信息
        """
        log_extra = {
            "operation": operation,
            "duration": duration,
            "success": success,
        }
        if extra:
            log_extra.update(extra)
            
        level = logging.INFO if success else logging.WARNING
        self.logger.logger.log(
            level,
            f"Operation {operation} completed {'successfully' if success else 'with issues'}",
            extra=log_extra
        )


# 使用示例
def example_usage():
    """
    使用示例：
    
    # 方式1: 装饰器使用
    @enhanced_error_handler(reraise=True, retry_times=3, retry_delay=1.0)
    async def example_async_function(param1, param2):
        # 函数实现
        pass
    
    # 方式2: 类方法使用
    class SomeService:
        @enhanced_error_handler(log_level=logging.WARNING)
        def example_sync_method(self, data):
            # 方法实现
            pass
    
    # 方式3: 手动使用错误处理器
    error_handler = ErrorHandler("my_service")
    try:
        # 一些可能出错的操作
        pass
    except Exception as e:
        response = await error_handler.handle_api_error(e, "some_operation")
        return response
    """
    pass
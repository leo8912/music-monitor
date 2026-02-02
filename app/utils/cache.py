# -*- coding: utf-8 -*-
"""
通用持久化缓存工具

用途:
- 缓存 API 请求结果 (元数据、搜索结果)
- 减少重复网络请求，提升性能
- 支持磁盘持久化

Author: google
Created: 2026-02-02
"""
import os
import json
import time
import logging
import hashlib
import functools
from typing import Any, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class DiskCache:
    """简单的基于文件的磁盘缓存"""
    
    def __init__(self, cache_dir: str = "cache/api_cache", ttl: int = 86400 * 7):
        """
        Args:
            cache_dir: 缓存目录
            ttl: 过期时间(秒)，默认7天
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
    
    def _get_cache_path(self, key: str) -> Path:
        """根据 key 生成 md5 文件名"""
        hashed_key = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{hashed_key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存内容"""
        path = self._get_cache_path(key)
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否过期
            if time.time() - data.get('timestamp', 0) > self.ttl:
                # logger.debug(f"Cache expired for key: {key}")
                return None
            
            return data.get('value')
        except Exception as e:
            logger.warning(f"Failed to read cache for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """设置缓存内容"""
        path = self._get_cache_path(key)
        try:
            data = {
                'key': key,
                'timestamp': time.time(),
                'value': value
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write cache for {key}: {e}")

# 全局缓存实例
api_cache = DiskCache()

def persistent_cache(namespace: str, ttl: int = 86400 * 7):
    """
    持久化缓存装饰器
    
    Usage:
        @persistent_cache(namespace="lyrics")
        async def fetch_lyrics(title, artist): ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成 cache key
            # 注意: 这里假设 args[0] 是 self, 如果不是需要调整
            # 我们通过函数名和参数生成 key
            func_args = args[1:] if args and hasattr(args[0], func.__name__) else args
            key_parts = [namespace, func.__name__]
            key_parts.extend([str(a) for a in func_args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            key = ":".join(key_parts)
            
            # 尝试获取缓存
            cached_val = api_cache.get(key)
            if cached_val is not None:
                # logger.debug(f"Cache hit for {func.__name__} ({key})")
                return cached_val
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 设置缓存 (仅当结果不为空时)
            if result:
                api_cache.set(key, result)
            
            return result
        
        return async_wrapper
    return decorator

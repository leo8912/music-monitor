# -*- coding: utf-8 -*-
"""
通用分页模型

定义统一的分页请求参数和响应格式,用于所有列表接口

Author: google
Created: 2026-01-30
"""
from typing import TypeVar, Generic, List
from pydantic import BaseModel, Field
from math import ceil


# 泛型类型变量
T = TypeVar('T')


class PaginationParams(BaseModel):
    """
    统一分页请求参数
    
    Attributes:
        page: 页码,从1开始
        page_size: 每页数量,默认20,最大100
    """
    page: int = Field(1, ge=1, description="页码,从1开始")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    
    def to_offset_limit(self) -> tuple[int, int]:
        """
        转换为 offset/limit 格式 (用于数据库查询)
        
        Returns:
            (offset, limit) 元组
        """
        offset = (self.page - 1) * self.page_size
        limit = self.page_size
        return offset, limit


class PaginatedResponse(BaseModel, Generic[T]):
    """
    统一分页响应格式
    
    Attributes:
        items: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页数量
        total_pages: 总页数
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """
        创建分页响应
        
        Args:
            items: 数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页数量
            
        Returns:
            PaginatedResponse 实例
        """
        total_pages = ceil(total / page_size) if page_size > 0 else 0
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


# 兼容旧格式的辅助函数
def convert_skip_limit_to_page(skip: int, limit: int) -> tuple[int, int]:
    """
    将旧的 skip/limit 参数转换为新的 page/page_size 参数
    
    Args:
        skip: 跳过的记录数
        limit: 每页数量
        
    Returns:
        (page, page_size) 元组
    """
    page = (skip // limit) + 1 if limit > 0 else 1
    page_size = limit
    return page, page_size

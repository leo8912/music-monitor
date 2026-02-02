# -*- coding: utf-8 -*-
"""
API 分页功能测试

测试统一分页模型和 API 端点

Author: google
Created: 2026-01-30
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.schemas.pagination import PaginationParams, PaginatedResponse, convert_skip_limit_to_page


class TestPaginationModels:
    """分页模型测试"""
    
    def test_pagination_params_to_offset_limit(self):
        """测试分页参数转换为 offset/limit"""
        # Page 1
        params = PaginationParams(page=1, page_size=20)
        offset, limit = params.to_offset_limit()
        assert offset == 0
        assert limit == 20
        
        # Page 2
        params = PaginationParams(page=2, page_size=20)
        offset, limit = params.to_offset_limit()
        assert offset == 20
        assert limit == 20
        
        # Page 3, size 10
        params = PaginationParams(page=3, page_size=10)
        offset, limit = params.to_offset_limit()
        assert offset == 20
        assert limit == 10
    
    def test_convert_skip_limit_to_page(self):
        """测试旧格式转换为新格式"""
        # skip=0, limit=20 -> page=1, page_size=20
        page, page_size = convert_skip_limit_to_page(0, 20)
        assert page == 1
        assert page_size == 20
        
        # skip=20, limit=20 -> page=2, page_size=20
        page, page_size = convert_skip_limit_to_page(20, 20)
        assert page == 2
        assert page_size == 20
        
        # skip=40, limit=10 -> page=5, page_size=10
        page, page_size = convert_skip_limit_to_page(40, 10)
        assert page == 5
        assert page_size == 10
    
    def test_paginated_response_create(self):
        """测试分页响应创建"""
        items = [1, 2, 3, 4, 5]
        total = 100
        page = 1
        page_size = 5
        
        response = PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
        
        assert response.items == items
        assert response.total == 100
        assert response.page == 1
        assert response.page_size == 5
        assert response.total_pages == 20  # ceil(100 / 5)


class TestPaginationAPI:
    """API 分页功能测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    def test_get_songs_with_new_params(self, client):
        """测试使用新分页参数获取歌曲"""
        # 需要登录才能访问
        # 这里假设有测试用户
        response = client.get("/api/library/songs", params={
            "page": 1,
            "page_size": 10
        })
        
        # 如果未登录,应该返回 401
        if response.status_code == 401:
            pytest.skip("需要登录")
        
        # 验证响应格式
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
    
    def test_get_songs_with_old_params(self, client):
        """测试使用旧分页参数获取歌曲 (向后兼容)"""
        response = client.get("/api/library/songs", params={
            "skip": 0,
            "limit": 10
        })
        
        if response.status_code == 401:
            pytest.skip("需要登录")
        
        # 应该仍然返回新格式
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "page_size" in data
    
    def test_get_download_history_pagination(self, client):
        """测试下载历史分页"""
        response = client.get("/api/download-history/", params={
            "page": 1,
            "page_size": 20
        })
        
        if response.status_code == 401:
            pytest.skip("需要登录")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "total_pages" in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

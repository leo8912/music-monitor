# -*- coding: utf-8 -*-
"""
后端服务健康检查测试

测试后端服务是否正常运行,所有 API 端点是否可访问

Author: google
Created: 2026-01-30
"""
import pytest
import httpx
import asyncio

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_server_running():
    """测试服务器是否正常运行"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/check_auth", timeout=5.0)
            # 200 或 401 都表示服务正常
            assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"
            print("✅ 服务器正常运行")
        except httpx.ConnectError:
            pytest.fail("❌ 无法连接到服务器,请确保后端服务正在运行")


@pytest.mark.asyncio
async def test_api_endpoints_accessible():
    """测试所有 API 端点是否可访问"""
    endpoints = [
        ("/api/library/songs?page=1&page_size=10", "歌曲列表"),
        ("/api/library/local-songs?page=1&page_size=10", "本地歌曲"),
        ("/api/download-history/?page=1&page_size=10", "下载历史"),
        ("/api/subscription/artists", "关注歌手"),
    ]
    
    results = []
    async with httpx.AsyncClient() as client:
        for endpoint, name in endpoints:
            try:
                response = await client.get(f"{BASE_URL}{endpoint}", timeout=5.0)
                # 401 表示需要认证,但端点存在
                if response.status_code in [200, 401]:
                    results.append((name, "✅ 可访问", response.status_code))
                else:
                    results.append((name, f"❌ 错误", response.status_code))
            except Exception as e:
                results.append((name, f"❌ 异常: {str(e)}", None))
    
    # 打印结果
    print("\n=== API 端点可访问性测试 ===")
    for name, status, code in results:
        print(f"{name}: {status} (状态码: {code})")
    
    # 验证所有端点都可访问
    failed = [r for r in results if "❌" in r[1]]
    assert len(failed) == 0, f"有 {len(failed)} 个端点不可访问"


@pytest.mark.asyncio
async def test_pagination_response_format():
    """测试分页响应格式"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/library/songs",
            params={"page": 1, "page_size": 5},
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # 验证响应格式
            required_fields = ["items", "total", "page", "page_size", "total_pages"]
            for field in required_fields:
                assert field in data, f"响应缺少字段: {field}"
            
            # 验证数据类型
            assert isinstance(data["items"], list), "items 应该是列表"
            assert isinstance(data["total"], int), "total 应该是整数"
            assert isinstance(data["page"], int), "page 应该是整数"
            assert isinstance(data["page_size"], int), "page_size 应该是整数"
            assert isinstance(data["total_pages"], int), "total_pages 应该是整数"
            
            # 验证分页参数
            assert data["page"] == 1, "page 应该是 1"
            assert data["page_size"] == 5, "page_size 应该是 5"
            
            print(f"✅ 分页响应格式正确: {len(data['items'])} 条记录, 共 {data['total']} 条")
        elif response.status_code == 401:
            print("⚠️ 需要认证,跳过分页格式测试")
            pytest.skip("需要认证")


if __name__ == '__main__':
    # 直接运行测试
    asyncio.run(test_server_running())
    asyncio.run(test_api_endpoints_accessible())
    asyncio.run(test_pagination_response_format())

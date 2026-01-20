"""
系统版本API路由
"""
from fastapi import APIRouter
from version import get_version_info

router = APIRouter()

@router.get("/api/version")
async def get_version():
    """获取系统版本信息"""
    return get_version_info()

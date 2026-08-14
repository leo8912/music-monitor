"""
系统版本API路由
"""
from fastapi import APIRouter, Depends
from version import get_version_info
from app.dependencies import require_auth
from app.schemas import VersionResponse

router = APIRouter(dependencies=[Depends(require_auth)])

@router.get("/api/version", response_model=VersionResponse)
async def get_version():
    """获取系统版本信息"""
    return get_version_info()

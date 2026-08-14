"""
API 错误码体系

定义统一的错误码和相应的 HTTP 状态码，用于所有 API 响应。
"""

from enum import IntEnum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class ErrorCode(IntEnum):
    """API 错误码定义"""

    # 2xx 成功
    SUCCESS = 200  # 成功

    # 4xx 客户端错误
    BAD_REQUEST = 400  # 请求参数错误
    UNAUTHORIZED = 401  # 未授权
    FORBIDDEN = 403  # 禁止访问
    NOT_FOUND = 404  # 资源不存在
    CONFLICT = 409  # 冲突（如重复资源）
    UNPROCESSABLE_ENTITY = 422  # 无法处理的实体
    TOO_MANY_REQUESTS = 429  # 请求过于频繁

    # 5xx 服务器错误
    INTERNAL_ERROR = 500  # 内部服务器错误
    SERVICE_UNAVAILABLE = 503  # 服务不可用

    # 业务特定错误码
    INVALID_AUTH = 4001  # 无效的认证凭据
    INVALID_CONFIG = 4002  # 配置错误
    DOWNLOAD_FAILED = 4003  # 下载失败
    METADATA_ERROR = 4004  # 元数据错误
    NETWORK_ERROR = 4005  # 网络错误
    DUPLICATE_RESOURCE = 4006  # 资源已存在
    RATE_LIMITED = 4007  # 频率限制


HTTP_STATUS_MAP = {
    ErrorCode.SUCCESS: 200,
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.UNPROCESSABLE_ENTITY: 422,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.INVALID_AUTH: 401,
    ErrorCode.INVALID_CONFIG: 400,
    ErrorCode.DOWNLOAD_FAILED: 500,
    ErrorCode.METADATA_ERROR: 500,
    ErrorCode.NETWORK_ERROR: 503,
    ErrorCode.DUPLICATE_RESOURCE: 409,
    ErrorCode.RATE_LIMITED: 429,
}


class ErrorResponse(BaseModel):
    """统一错误响应模型"""
    code: int
    message: str
    detail: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": 400,
                "message": "Bad Request",
                "detail": "Missing required field: title"
            }
        }
    )


class SuccessResponse(BaseModel):
    """统一成功响应模型（可选）"""
    code: int = ErrorCode.SUCCESS
    message: str = "Success"
    data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": 200,
                "message": "Success",
                "data": {"id": 1, "name": "example"}
            }
        }
    )

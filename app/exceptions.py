"""
应用异常定义模块
定义项目中使用的各种自定义异常类型

Author: ali
Update Log:
2024-12-19: 创建业务异常和验证异常定义
"""

class BaseError(Exception):
    """基础异常类"""
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BusinessError(BaseError):
    """业务异常 - 表示预期的业务逻辑错误"""
    pass


class ValidationError(BaseError):
    """验证异常 - 表示输入验证失败"""
    pass


class DownloadError(BaseError):
    """下载异常 - 表示下载过程中发生的错误"""
    pass


class MetadataError(BaseError):
    """元数据异常 - 表示元数据处理过程中发生的错误"""
    pass


class PluginError(BaseError):
    """插件异常 - 表示插件调用过程中发生的错误"""
    pass


class DatabaseError(BaseError):
    """数据库异常 - 表示数据库操作过程中发生的错误"""
    pass


class NetworkError(BaseError):
    """网络异常 - 表示网络请求过程中发生的错误"""
    pass


class AuthenticationError(BaseError):
    """认证异常 - 表示认证过程中发生的错误"""
    pass


class AuthorizationError(BaseError):
    """授权异常 - 表示授权过程中发生的错误"""
    pass


class NotFoundError(BaseError):
    """未找到异常 - 表示请求的资源未找到"""
    pass


class DuplicateError(BaseError):
    """重复异常 - 表示尝试创建重复资源时发生的错误"""
    pass


class RateLimitError(BaseError):
    """频率限制异常 - 表示超出API调用频率限制"""
    pass


class ServiceUnavailableError(BaseError):
    """服务不可用异常 - 表示外部服务暂时不可用"""
    pass


# 异常别名，保持向后兼容
APIError = BaseError
ConfigError = BaseError
CacheError = BaseError
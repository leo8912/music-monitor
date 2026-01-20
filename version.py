"""
版本信息模块
自动读取并提供版本号信息
"""
__backend_version__ = "1.0.0"
__frontend_version__ = "1.0.0"
__build_date__ = "2026-01-20"

def get_version_info():
    """获取版本信息"""
    return {
        "backend_version": __backend_version__,
        "frontend_version": __frontend_version__,
        "version": __backend_version__,  # 保持兼容性
        "build_date": __build_date__,
        "name": "Music Monitor",
        "author": "Leo"
    }

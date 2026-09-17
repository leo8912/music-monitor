"""
版本信息模块
自动读取并提供版本号信息
"""

__backend_version__ = "2.11.3"
__frontend_version__ = "2.11.3"
# 自动生成的构建时间 (Updated by Agent)
__build_date__ = "2026-09-17 12:50:00"

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

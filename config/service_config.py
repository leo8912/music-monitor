"""
服务配置模块
此模块定义了服务工厂和依赖注入的相关配置

Author: ali
Update Log:
2024-12-19: 创建服务配置，定义服务依赖关系
"""

SERVICE_CONFIG = {
    # 服务依赖配置
    'library_service': {
        'dependencies': ['database', 'metadata_service'],
        'singleton': True,
    },
    'metadata_service': {
        'dependencies': ['database', 'metadata_merger'],
        'singleton': True,
    },
    'subscription_service': {
        'dependencies': ['database'],
        'singleton': True,
    },
    'history_service': {
        'dependencies': ['database'],
        'singleton': True,
    },
    'notification_service': {
        'dependencies': ['database'],
        'singleton': True,
    },
    'media_service': {
        'dependencies': ['database', 'download_history_service'],
        'singleton': True,
    },
    'enhanced_metadata_service': {
        'dependencies': ['metadata_merger'],
        'singleton': True,
    },
    
    # 服务别名映射
    'aliases': {
        'library': 'library_service',
        'metadata': 'metadata_service',
        'subscription': 'subscription_service',
        'history': 'history_service',
        'notification': 'notification_service',
        'media': 'media_service',
        'enhanced_metadata': 'enhanced_metadata_service',
    }
}


def get_service_config(service_name: str) -> dict:
    """
    获取服务配置
    
    Args:
        service_name: 服务名称
        
    Returns:
        服务配置字典
    """
    return SERVICE_CONFIG.get(service_name, {})


def get_service_dependencies(service_name: str) -> list:
    """
    获取服务依赖列表
    
    Args:
        service_name: 服务名称
        
    Returns:
        依赖服务列表
    """
    config = get_service_config(service_name)
    return config.get('dependencies', [])


def is_singleton_service(service_name: str) -> bool:
    """
    检查服务是否为单例
    
    Args:
        service_name: 服务名称
        
    Returns:
        是否为单例服务
    """
    config = get_service_config(service_name)
    return config.get('singleton', False)


def get_service_alias(alias: str) -> str:
    """
    根据别名获取真实服务名
    
    Args:
        alias: 服务别名
        
    Returns:
        真实服务名称
    """
    return SERVICE_CONFIG['aliases'].get(alias, alias)
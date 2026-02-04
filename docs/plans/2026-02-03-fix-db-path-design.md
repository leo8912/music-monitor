# 数据库路径一致性修复设计方案

## 背景
在 Docker 环境（或任何通过环境变量自定义 `DATABASE_URL` 的环境）中，应用程序可以正确连接到自定义路径（例如 `/config/music_monitor.db`）。然而，通过 `init_db` 运行的 Alembic 迁移使用的是 `alembic.ini` 中的默认配置（`./music_monitor.db`）。

这种不匹配导致：
1. 迁移在错误的数据库文件上成功运行。
2. 应用程序连接到了正确路径下的空数据库。
3. 当应用程序尝试查询表时，报错 `no such table`。

## 根本原因
`alembic/env.py` 使用 `config.get_main_option("sqlalchemy.url")` 初始化 Alembic 配置上下文，这直接读取 `alembic.ini`，忽略了运行时的 `DATABASE_URL` 环境变量或 `core/database.py` 中的逻辑。

## 解决方案
修改 `alembic/env.py`，从 `core.database`（应用程序数据库连接的唯一真理来源）导入 `DATABASE_URL`，并在运行迁移之前覆盖 Alembic 配置中的 `sqlalchemy.url`。

这确保了无论是在 Docker、本地开发还是通过 CLI 运行，Alembic 始终与应用程序操作同一个数据库文件。

## 详细变更

### `alembic/env.py`

当前:
```python
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    # ...
```

建议修改:
```python
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# [新增] 从 core.database 导入 DATABASE_URL 以确保一致性
from core.database import DATABASE_URL
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    # ...
```

## 验证计划
1. 删除根目录和 `/config`（如果映射了）下的任何现有 `music_monitor.db`。
2. 启动应用程序。
3. 验证日志显示迁移正在运行。
4. 验证应用程序启动完成且没有 `no such table` 错误。

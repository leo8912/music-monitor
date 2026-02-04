# 数据库路径一致性修复实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 确保 Alembic 迁移使用与运行中的应用程序相同的数据库路径，解决 Docker/自定义环境中出现的 `no such table` 错误。

**架构:** 修改 `alembic/env.py`，从应用程序的配置 (`core.database`) 动态获取数据库 URL，而不是从 `alembic.ini` 静态读取。

**技术栈:** Python, Alembic, SQLAlchemy

---

### 任务 1: 统一数据库 URL 来源

**文件:**
- 修改: `d:/code/music-monitor/alembic/env.py`

**步骤 1: 检查当前状态**
确认 `alembic/env.py` 仅从 config读取配置。

**步骤 2: 修改 `alembic/env.py`**
注入来自 `core.database` 的 `DATABASE_URL`。

```python
# 在 fileConfig 调用之后插入 (~第18行)
from core.database import DATABASE_URL
config.set_main_option("sqlalchemy.url", DATABASE_URL)
```

**步骤 3: 验证**
运行 `python -m alembic check` 或启动应用程序，查看是否使用了正确的数据库。
(由于当前处于损坏状态，直接运行应用程序是最佳验证方式)。

**步骤 4: 提交**
```bash
git add alembic/env.py
git commit -m "fix(db): sync alembic db path with app config"
```

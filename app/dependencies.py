# -*- coding: utf-8 -*-
"""
路由级通用依赖 (FastAPI dependencies)

4.4 阶段引入：将 main.py 中硬编码的鉴权白名单中间件，
改为各 router / 端点上显式声明 `dependencies=[Depends(require_auth)]`。

设计约束：
- 与旧中间件语义完全一致：当 `auth.enabled = False`（未启用鉴权）时直接放行，
  因此测试环境（auth 禁用）下所有端点行为不变。
- 匿名端点（login / logout / check_auth / wecom callback / test_ws /
  discovery cover）所在的混合 router 采用端点级声明，其余纯鉴权 router
  采用 router 级声明。
"""
from fastapi import Request, HTTPException

from core.config_manager import get_config_manager


async def require_auth(request: Request):
    """要求已登录（会话中存在 user）；鉴权未启用时直接放行。

    行为与原 main.py `auth_middleware` 保持一致：
    1. `auth.enabled = False` → 放行（本地开发 / 测试环境）；
    2. session 中间件未激活（AssertionError）→ 500；
    3. 会话中无 user → 401。
    """
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
        return

    try:
        user = request.session.get("user")
    except AssertionError:
        # SessionMiddleware 未在作用域内激活（与旧中间件相同的兜底）
        raise HTTPException(status_code=500, detail="鉴权系统初始化异常")

    if not user:
        raise HTTPException(status_code=401, detail="未授权，请先登录")

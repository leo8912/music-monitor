"""
Router层 - API路由控制器

此目录包含所有的API路由端点，负责接收HTTP请求并返回响应。
严格遵循分层架构，不包含业务逻辑，仅负责参数验证和响应格式化。

主要职责：
- 接收HTTP请求并解析参数
- 调用Service层处理业务逻辑
- 返回标准化的JSON响应
- 处理HTTP层面的错误和异常

架构约束：
- 不得直接访问数据库或模型层
- 不得包含业务逻辑处理
- 必须通过依赖注入使用Service层
- 遵循RESTful API设计规范

Author: music-monitor development team
"""
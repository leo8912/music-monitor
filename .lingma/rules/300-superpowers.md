---
trigger: always_on
---
# 300-Superpowers & Workflows

## 核心准则 (Prime Directives)
- **技能优先**: 在处理任何任务前，优先加载并阅读相关 Skill (如 `music-monitor-dev`).
- **强制 TDD**: 所有功能开发必须遵循 `test-driven-development` 技能的红-绿-重构循环。
- **结构化设计**: 在编写代码前，必须通过 `/brainstorm` 明确设计规范。
- **小步快跑**: 所有实施计划必须通过 `/write-plan` 拆分为极小的原子任务。
- **配置一致性**: 每次修改配置项或代码默认值，必须同步全面更新 `config.example.yaml`。

## 常用工作流 (Workflows)
- `/brainstorm`: 启动需求头脑风暴。
- `/write-plan`: 创建实施计划。
- `/execute-plan`: 执行并审查计划。
- `/git-commit`: 规范化提交更改。

## 技术规范
- **语言**: Typescript / Node.js (前端), Python (后端)
- **提交**: Conventional Commits (中文)

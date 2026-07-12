# Anthropic Product Management Mapping

## Upstream 能力

`anthropics/knowledge-work-plugins/product-management` 提供：

- `competitive-brief`
- `metrics-review`
- `product-brainstorming`
- `roadmap-update`
- `sprint-planning`
- `stakeholder-update`
- `synthesize-research`
- `write-spec`
- `commands/brainstorm.md`

## 当前映射

| Upstream | 本仓库 | 处理方式 |
|---|---|---|
| `product-brainstorming` | `pm-requirement-define` | 与需求澄清合并，统一完成问题、目标、方向、范围和边界定义 |
| 无完全等价 upstream | `pm-requirement-define` | 吸收原需求诊断能力，作为 PRD 前统一入口 |
| `write-spec` | `pm-prd-write` | 扩展为决策记录层与研发交付层完整 PRD |
| `stakeholder-update` | `pm-update-write` | 简化命名，覆盖更新说明、变更通知和更新日志 |
| `synthesize-research` | `pm-research-synthesize` | 增加材料编码、证据强度、反例、分群和机会转化 |
| `competitive-brief` | `pm-competitor-analyze` | 增加统一任务脚本、证据台账、差异归因和采用建议 |
| `metrics-review` | `pm-metrics-review` | 增加指标树、数据质量、拆解、证据等级和决策门 |
| `roadmap-update` | 未保留 | 依赖真实战略目标、资源和组织承诺，更适合项目专用能力 |
| `sprint-planning` | 未保留 | 依赖团队容量、任务系统和交付承诺，更适合工具集成 skill |
| `commands/brainstorm.md` | `commands/pm-requirement-define.md` | 与统一需求定义入口保持一致 |

## 结构性差异

- 使用中文执行工作流，skill 采用 `pm-对象/交付物-动作` 命名
- 合并高重合度的产品脑暴与需求澄清，减少用户选择成本
- 用“产品方案六问”统一需求定义和 PRD 的论证逻辑
- `pm-prd-write` 承接已确认的产品决策，并覆盖研发实现、原型追溯、测试验收和上线验证
- 研究综合、竞品分析和指标复盘作为可独立使用的证据增强层，在需求定义前或过程中按缺口调用
- 分析型 skills 必须提供证据方法、模板和示例，而不是只有输出目录
- 不保留脱离项目事实后只能生成泛化清单的管理型 skills
- Codex `display_name` 与 skill 名称完全一致

## 历史名称迁移

| 原名称 | 当前名称 / 状态 |
|---|---|
| `pm-brainstorm-zh` | `pm-requirement-define` |
| `pm-requirement-intake-zh` | `pm-requirement-define` |
| `pm-write-spec-zh` | `pm-prd-write` |
| `pm-stakeholder-update-zh` | `pm-update-write` |
| `pm-research-synthesis-zh` | `pm-research-synthesize` |
| `pm-competitive-brief-zh` | `pm-competitor-analyze` |
| `pm-metrics-review-zh` | `pm-metrics-review` |
| `pm-roadmap-update-zh` | 已移除 |
| `pm-sprint-planning-zh` | 已移除 |

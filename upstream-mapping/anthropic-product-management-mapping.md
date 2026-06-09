# Anthropic Product Management Mapping

## Upstream 当前能力

`anthropics/knowledge-work-plugins/product-management` 当前包含：

### Skills

1. `competitive-brief`
2. `metrics-review`
3. `product-brainstorming`
4. `roadmap-update`
5. `sprint-planning`
6. `stakeholder-update`
7. `synthesize-research`
8. `write-spec`

### Command

- `commands/brainstorm.md`

## 本仓库映射

| Upstream | 本仓库 |
|----------|--------|
| `product-brainstorming` | `pm-brainstorm-zh` |
| 无完全等价 upstream | `pm-requirement-intake-zh` |
| `write-spec` | `pm-write-spec-zh` |
| `stakeholder-update` | `pm-stakeholder-update-zh` |
| `roadmap-update` | `pm-roadmap-update-zh` |
| `sprint-planning` | `pm-sprint-planning-zh` |
| `synthesize-research` | `pm-research-synthesis-zh` |
| `competitive-brief` | `pm-competitive-brief-zh` |
| `metrics-review` | `pm-metrics-review-zh` |
| `commands/brainstorm.md` | `commands/brainstorm-zh.md` |

## 关键差异

- 本仓库以中文为主
- 本仓库强调“先需求澄清、再实现”
- 本仓库默认会在项目内搜索 `AGENTS.md`、`README.md`、`docs/`
- 本仓库将模板、示例、检查清单补齐为可直接复用的中文素材

## 第一阶段优先级

优先落地：

- `pm-brainstorm-zh`
- `pm-requirement-intake-zh`
- `pm-write-spec-zh`
- `pm-stakeholder-update-zh`
- `commands/brainstorm-zh.md`

后续补齐：

- `pm-roadmap-update-zh`
- `pm-sprint-planning-zh`
- `pm-research-synthesis-zh`
- `pm-competitive-brief-zh`
- `pm-metrics-review-zh`

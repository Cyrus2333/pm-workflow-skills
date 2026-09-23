# TAPD 写入预览模板

```markdown
# TAPD 写入预览

## 操作
- 1. …

## Workspace
- 名称：…（用户指定 / 当前对象事实 / 用户默认）
- 实时 ID：…

## 查重结果
- 查询范围、实体、过滤与分页是否完整：…
- 明确重复：无 / …
- 相关候选：无 / …

## 将写入的对象
- Story / Product Task：…
- 完整 Description：
  …

## 字段与来源
| 逻辑字段 | 即将写入值 | 来源 | 实时 TAPD 字段 | Readback 断言 |
|---|---|---|---|---|

Story 必须至少包含以下两行，且不得留空：

| 分类 | 显示名称（写入 ID） | 用户明确 / 确认事实 / 可靠默认 | `category_id`，实时 enum 已唯一解析 | `category_id=<ID>` |
| 标签 | 显示名称（写入值） | 用户明确 / 确认事实 / 可靠默认 | `label`，实时 enum 已唯一解析 | `label=<值>` |

## 状态计划
- 创建状态：…
- 目标状态：…
- 是否可推进：是 / 否
- 证明来源：official_workflow / documented_task_status
- 是否可宣称 workflow-proven：是 / 否
- 阻塞字段：…
- 预计本次最终状态：…

## 附件与能力
- 后端：tapd-openapi / `scripts/pm_tapd.py`
- Task attachment list：未调用 / 查询成功 / 失败
- Task attachment upload：community contract / UNAVAILABLE
- Task attachment Readback：未调用 / 将在上传后执行
- 将上传：无 / 文件列表
- mention：无 / 预览中的 nick 与原生节点

## dry-run form
- 与下方将 POST 的字段一致，未确认前不得去掉 `--dry-run`
- Story dry-run form 必须显式包含非空的 `category_id` 与 `label`；二者任一缺失、未在实时 schema 解析或未列入 Readback expect 时，预览无效，禁止请求确认。

## 本轮不会执行
- …

请确认本预览中需要执行的具体动作；已有同一有效授权不重复索取。
```

# TAPD 写入预览模板

```markdown
# TAPD 写入预览

## 操作
- 交付模式：normal / backfill（历史补录）
- 动作包：`action_id`、依赖、确认状态、可断点续作范围
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

## 状态计划
- 业务目标状态：…
- 创建请求状态：…
- 预期服务端有效状态：…
- 创建状态：…
- 目标状态：…
- 状态差异策略：阻断 / `server_normalized_status` / 人工流转
- 是否可推进：是 / 否
- 证明来源：official_workflow / documented_task_status
- 是否可宣称 workflow-proven：是 / 否
- 阻塞字段：…
- 预计本次最终状态：…

## 日期证据
- Story 开始 / 结束：…（来源、是否同日规则）
- Task 开始 / 结束：…（来源；不得使用文件修改时间）

## 附件与能力
- 后端：tapd-openapi / `scripts/pm_tapd.py`
- Task attachment list：未调用 / 查询成功 / 失败
- Task attachment upload：community contract / UNAVAILABLE
- Task attachment Readback：未调用 / 将在上传后执行
- 将上传：无 / 文件列表
- 映射状态：`exact` / `derived_summary` / `substitute` / `missing`；替代文件需单独确认
- mention：无 / 预览中的 nick 与原生节点

## dry-run form
- 与下方将 POST 的字段一致，未确认前不得去掉 `--dry-run`

## 本轮不会执行
- …

请确认本预览中需要执行的具体动作；已有同一有效授权不重复索取。
```

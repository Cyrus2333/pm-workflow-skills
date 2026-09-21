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

## 状态计划
- 创建状态：…
- 目标状态：…
- 是否可推进：是 / 否 / V1 无法在写入前证明 transition
- 阻塞字段：…
- 预计本次最终状态：…

## 适配器与能力
- 后端：tapd-openapi / `scripts/pm_tapd.py`
- workflow：UNAVAILABLE
- Task attachment list：UNAVAILABLE
- Task attachment upload：UNAVAILABLE
- mention：UNAVAILABLE
- 将上传：无（V1 不上传）

## dry-run form
- 与下方将 POST 的字段一致，未确认前不得去掉 `--dry-run`

## 本轮不会执行
- …

请确认本预览中需要执行的具体动作；已有同一有效授权不重复索取。
```

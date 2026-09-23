# TAPD 字段解析规则

## 1. 字段来源

字段值统一按以下优先级解析：

```text
用户本轮明确指定
> 当前 TAPD 对象或当前上下文中已确认事实
> 可靠用户 / 项目默认
> 已明确标为建议的待确认值（不是事实）
```

- 公共Skill不预设P1、周期、Task次日到期、Story 分类或标签、外部依赖无或planned目标状态。用户/Workspace策略只在外部配置保存，必须注明来源并经实时schema校验；“外部依赖无”等事实不得由默认推定。
- 推荐值：预期价值收益、Product Task 类别；必须标记推荐，低置信度不能自动决定。
- 事实字段：workspace、owner、需求提出人、所属部门、实际完成日期、实际投入人天、已有附件、当前状态；只能来自用户、可靠配置或 TAPD Readback。

## 2. 实时解析

写入前通过 `scripts/pm_tapd.py fields/workspace/get/workflow` 读取 workspace、Story fields、Task fields、entity custom fields、workitem type、枚举和状态流转。reference 只保存“逻辑字段 → 实时识别方式 → 写入参数 → Readback 断言”，不固定 `custom_field_N` 或单 workspace ID。

逻辑字段解析失败时，不写该字段；若它是目标状态或用户指令的必要事实，则暂停并说明原因。

Workspace 的优先级为：用户本轮指定 > 当前明确 TAPD Story / Task 的 workspace > 用户默认 workspace > 询问。名称解析后，每次正式写入仍须实时确认 workspace 有效并取得真实 ID。workspace、Story 分类、项目列表字段是不同概念，不能混用。

### Story 分类与标签

Story 的 `category_id`（逻辑字段“分类”）和 `label`（逻辑字段“标签”）都是必填写入计划字段。每次 Story 创建或更新均须执行以下步骤：

1. 通过 `fields --entity stories` 获取实时 schema，按 API 字段名唯一定位 `category_id` 与 `label`；字段缺失、只读、重名或枚举为空时停止。
2. 按本文件的字段来源优先级解析显示值；分类与标签都不得凭通用默认、推荐或“未分类”补全。
3. 在实时枚举中唯一映射显示值到写入值。分类可由显示名规范化为 ID；标签必须是实时允许的标签值。
4. 在预览、dry-run form 和 Readback expect 中同时明确 `category_id` 与 `label`。更新不改变它们时也须携带并断言当前已确认值，避免字段被隐式清空或遗漏验证。

## 3. Story 目标状态

没有公共默认目标状态。仅对明确要求的目标状态计划流转。每次通过 `workflow --entity stories --workitem-type-id ...` 读取官方 status map 与合法 transition，并检查该 workspace / workitem type 所需事实。当前到目标不在 transition 中则禁止写入。需求提出人、所属部门等无可靠来源时必须询问，不得猜测。

## 4. Product Task 状态

官方 workflow 的 `system` 只覆盖 story / bug。先尝试 `workflow --entity tasks`；若 TAPD 拒绝，适配器回退到文档化 `open / progressing / done`，并设置 `source=documented_task_status`、`workflow_proven=false`。Skill 可以把文档化允许的流转写入预览，但不得对用户宣称“已通过 workflow API 证明合法”；最终仍以服务端接受写入并 Readback 为准。

## 5. Product Task 类别

根据实际工作和实时类别枚举提出候选，不硬编码组织专用类别。事实源、schema API和写参数是不同证据：同名label可能对应多个API字段，必须按实际写API字段唯一映射。两个工具返回冲突时核对实体类型、缓存/权限与权威字段读取；不能用空数组覆盖非空实时schema，也不能盲目合并。

结构化字段解析可复用 `scripts/tapd-contract.py`：同名 label 不唯一即拒绝，明确当前写 API 字段后再解析枚举。TAPD 某些自定义字段会把选项映射以 JSON 字符串返回，适配器必须先解析为 `key → display label`，不能把整段 JSON 当成单个选项。Product Task 的“任务类别”字段写入时使用实时枚举的 display label；适配器可将传入的合法数字 key 规范化为中文 label，避免任务页面显示内部数字。该纯函数不抓取 schema、不判定业务推荐正确，也不执行写入。

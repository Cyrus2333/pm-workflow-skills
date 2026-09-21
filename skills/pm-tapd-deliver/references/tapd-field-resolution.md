# TAPD 字段解析规则

## 1. 字段来源

字段值统一按以下优先级解析：

```text
用户本轮明确指定
> 当前 TAPD 对象或当前上下文中已确认事实
> 可靠用户 / 项目默认
> 已明确标为建议的待确认值（不是事实）
```

- 公共Skill不预设P1、周期、Task次日到期、标签、外部依赖无或planned目标状态。用户/Workspace策略只在外部配置保存，必须注明来源并经实时schema校验；“外部依赖无”等事实不得由默认推定。
- 推荐值：预期价值收益、Product Task 类别；必须标记推荐，低置信度不能自动决定。
- 事实字段：workspace、owner、需求提出人、所属部门、实际完成日期、实际投入人天、已有附件、当前状态；只能来自用户、可靠配置或 TAPD Readback。

## 2. 实时解析

写入前通过 `scripts/pm_tapd.py fields/workspace/get/workflow` 读取 workspace、Story fields、Task fields、entity custom fields、workitem type、枚举和状态流转。reference 只保存“逻辑字段 → 实时识别方式 → 写入参数 → Readback 断言”，不固定 `custom_field_N` 或单 workspace ID。

逻辑字段解析失败时，不写该字段；若它是目标状态或用户指令的必要事实，则暂停并说明原因。

Workspace 的优先级为：用户本轮指定 > 当前明确 TAPD Story / Task 的 workspace > 用户默认 workspace > 询问。名称解析后，每次正式写入仍须实时确认 workspace 有效并取得真实 ID。workspace、Story 分类、项目列表字段是不同概念，不能混用。

## 3. Story 目标状态

没有公共默认目标状态。仅对明确要求的目标状态计划流转。每次通过 `workflow --entity stories --workitem-type-id ...` 读取官方 status map 与合法 transition，并检查该 workspace / workitem type 所需事实。当前到目标不在 transition 中则禁止写入。需求提出人、所属部门等无可靠来源时必须询问，不得猜测。

## 4. Product Task 状态

官方 workflow 的 `system` 只覆盖 story / bug。先尝试 `workflow --entity tasks`；若 TAPD 拒绝，适配器回退到文档化 `open / progressing / done`，并设置 `source=documented_task_status`、`workflow_proven=false`。Skill 可以把文档化允许的流转写入预览，但不得对用户宣称“已通过 workflow API 证明合法”；最终仍以服务端接受写入并 Readback 为准。

## 5. Product Task 类别

根据实际工作和实时类别枚举提出候选，不硬编码组织专用类别。事实源、schema API和写参数是不同证据：同名label可能对应多个API字段，必须按实际写API字段唯一映射。两个工具返回冲突时核对实体类型、缓存/权限与权威字段读取；不能用空数组覆盖非空实时schema，也不能盲目合并。

结构化字段解析可复用scripts/tapd-contract.py：同名label不唯一即拒绝，明确当前写API字段后再解析枚举。该纯函数不抓取schema、不判定业务推荐正确，也不执行写入。

## 6. 日期证据与单日规则

日期字段的事实来源必须写入预览：`user_explicit`、`documented_event_date`、`documented_interval`、`project_default` 或 `unknown`。需求包只出现一个明确日期时，默认只能证明“发生/确认/发布日”，不能自动证明 Task 的执行区间。只有用户或项目规则明确采用“同日开始/结束”时，才可写成同日区间；否则列为缺口并询问。

文件修改时间、当前系统日期、分支名和模型推测都不是 Task 开始/结束日期的事实来源。需求的发布时间不能自动当成每个 Task 的实际开始日，除非预览明确说明这是用户确认的项目记录规则。

## 7. 枚举提交值与展示值

实时 schema 可能返回对象、列表、`key|label` 文本或 JSON 字符串。适配器必须先归一化为 `option_key -> display_label`，再解析用户给出的 label/key。预览同时展示：逻辑值、提交值、Readback 展示值和语义等价证据。未经解析的数字 key 不得直接写入用户可见的任务类别等展示字段；若 TAPD 某字段契约要求 key，则提交 key 并在 Readback 断言 label，不能把“页面显示数字”误判为成功。

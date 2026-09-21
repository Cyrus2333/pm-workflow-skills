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

写入前按需读取 workspace、Story fields、Task fields、entity custom fields、workitem type、枚举、workflow status map 和 transitions。reference 只保存“逻辑字段 → 实时识别方式 → 写入参数 → Readback 断言”，不固定 `custom_field_N` 或单 workspace ID。

逻辑字段解析失败时，不写该字段；若它是目标状态或用户指令的必要事实，则暂停并说明原因。

Workspace 的优先级为：用户本轮指定 > 当前明确 TAPD Story / Task 的 workspace > 用户默认 workspace > 询问。名称解析后，每次正式写入仍须实时确认 workspace 有效并取得真实 ID。workspace、Story 分类、项目列表字段是不同概念，不能混用。

## 3. Story 目标状态

没有公共默认目标状态。仅对明确要求的目标状态计划流转。每次通过实时 workflow 验证当前状态的合法 transition，并检查该 workspace / workitem type 所需事实。需求提出人、所属部门等无可靠来源时必须询问，不得猜测。

## 4. Product Task 类别

根据实际工作和实时类别枚举提出候选，不硬编码组织专用类别。事实源、schema API和写参数是不同证据：同名label可能对应多个API字段，必须按实际写工具schema唯一映射。两个工具返回冲突时核对实体类型、缓存/权限与权威字段读取；不能用空数组覆盖非空实时schema，也不能盲目合并。

结构化字段解析可复用scripts/tapd-contract.py：同名label不唯一即拒绝，明确当前写API字段后再解析枚举。该纯函数不抓取schema、不判定业务推荐正确，也不执行写入。

# TAPD 字段解析规则

## 1. 字段来源

字段值统一按以下优先级解析：

```text
用户本轮明确指定
> 当前 TAPD 对象或当前上下文中已确认事实
> 可靠用户 / 项目默认
> Skill 推荐
> V1 通用默认
```

- 默认值：P1、14 天、Task 次日 due、open、“关键工作项”、外部依赖无；必须出现在预览且可覆盖。
- 推荐值：预期价值收益、Product Task 类别；必须标记推荐，低置信度不能自动决定。
- 事实字段：workspace、owner、需求提出人、所属部门、实际完成日期、实际投入人天、已有附件、当前状态；只能来自用户、可靠配置或 TAPD Readback。

## 2. 实时解析

写入前按需读取 workspace、Story fields、Task fields、entity custom fields、workitem type、枚举、workflow status map 和 transitions。reference 只保存“逻辑字段 → 实时识别方式 → 写入参数 → Readback 断言”，不固定 `custom_field_N` 或单 workspace ID。

逻辑字段解析失败时，不写该字段；若它是目标状态或用户指令的必要事实，则暂停并说明原因。

Workspace 的优先级为：用户本轮指定 > 当前明确 TAPD Story / Task 的 workspace > 用户默认 workspace > 询问。名称解析后，每次正式写入仍须实时确认 workspace 有效并取得真实 ID。workspace、Story 分类、项目列表字段是不同概念，不能混用。

## 3. Story 目标状态

`planned` 是默认目标状态。每次通过实时 workflow 验证当前状态的合法 transition，并检查该 workspace / workitem type 所需事实。需求提出人、所属部门等无可靠来源时必须询问，不得猜测。

## 4. Product Task 类别

将“调研 / 问题梳理 / 需求澄清”优先推荐为“【产品】需求调研”；“PRD / 产品方案 / 原型 / 交互 / 产品交付”优先推荐为“【产品】方案策划”；“正式需求评审 / 评审组织 / 评审跟进”优先推荐为“需求评审”。这是基于标题、当前阶段、实际工作、产物和用户意图的综合推荐，不是单关键词映射。

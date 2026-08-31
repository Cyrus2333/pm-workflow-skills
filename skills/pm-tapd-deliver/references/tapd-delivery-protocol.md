# TAPD 交付协议

## 1. 统一写入事务

每个事务依次执行：读取现状、Preflight、查重、计算字段、完整预览、用户确认、顺序写入、单项 Readback 与 Assert。确认仅覆盖预览中明确列出的动作；字段、枚举、workflow、重复候选、capability 或实际写入内容变化时，重新预览并确认。

任何 API 错误、Readback 不一致、不可推测事实缺失或附件失败均停止剩余操作。不得自动删除、覆盖、状态回退、补偿创建或再次写入试错。

## 2. Story

标题为 `【<需求等级>】<需求名称>`。等级来源顺序为用户本轮明确值、当前上下文已确认值；没有等级必须询问。Description 仅包含“需求背景、需求目标、需求范围”三段；快速占位仅写已知内容。

先以标准化标题在同一 workspace 的 `stories` 查重。完全一致为明确重复，停止并返回已有 Story；主题可能相关时仅列候选，由用户选择复用或新建。

默认目标状态为 `planned`，不是创建承诺。创建后 Readback，再读取目标 workitem type 的 status map 与合法 transition，检查 planned 所需事实。满足才单独推进并再次 Readback；否则停在合法初始状态并报告缺口。预览必须分别写明创建状态、目标状态、可否推进和预计最终状态。

Story Readback 至少断言 workspace、story_id、name、workitem type、status、priority、label、Description 和本轮写入的 custom fields。

## 3. Product Task

仅维护当前产品经理本人、且关联到明确 Story 的 Task；创建关系只能写 `story_id`。查重规则同 Story，但候选还应说明是否属于相同产品工作目的。

默认 begin 为创建当日、due 为次日、status 为 `open`、label 为“关键工作项”。owner 必须是用户明确值、可靠用户默认或当前 TAPD 上下文可确认事实；不能猜。

Task 标题自然语言表达，不加“【产品】”前缀。Product Task 类别必须实时解析 logical field 与合法枚举：高置信推荐在预览中注明；低置信要求用户选择；字段不存在时不写。

用户明确要求“创建后进行中”时，严格执行 create(open) → Readback → open 到 progressing → Readback。不得根据上下文自动改为 progressing。

用户明确完成时，先确认工作已完成、实际完成日期和实际投入人天。先根据当前 Task 与已确认交付计划判断是否存在必须上传的附件：存在时，附件必须已上传且 Readback；不存在时，附件不是 done 前置条件，attachment capability unavailable 也不得阻止 done。日期未给时可推荐当天并写入预览；投入人天不得推测。若没有可靠的合法写入字段，阻止 done；V1 不自动转写 timesheet。

Task Readback 至少断言 task_id、story_id、name、owner、begin、due、status、label、Product Task 类别、Description 和本轮其他重要字段。

## 4. Description 受管片段

Task Description 只写轻量“工作内容”和“产出物”，绝不复制 PRD。产出物使用可见边界：

```text
【产出物索引-开始】
- 正式 PRD：...
【产出物索引-结束】
```

只更新边界内内容，边界外人工文字原样保留。首次不存在边界时，在预览中完整展示追加后的 Description，经确认后才写入。

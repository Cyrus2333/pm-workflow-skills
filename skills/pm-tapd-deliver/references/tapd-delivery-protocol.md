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

仅维护当前产品经理本人、且关联到明确 Story 的 Task；创建关系只能写 `story_id`。

Task 查重以“同一项具体工作／同一轮交付”为准，不能仅因同 Story、同类别或都属于产品方案／PRD工作而阻断：

- 标准化标题一致，或标题虽有轻微差异但范围、阶段和交付物可高置信确认相同，为明确重复，停止新建；
- 已有 Task Description 明确覆盖本次拟建 Task 的同一工作内容与交付物，为明确重复，停止新建；
- 同 Story、同类别、泛化标题、主题相关或工作类型相同，但无法证明是同一轮具体工作的，标为“相关 Task”，只展示，不阻断。

用户明确选择“复用”时不新建；用户明确说明同类型相关 Task 对应另一轮独立工作、需要新增时，视为有效业务事实，允许在预览确认后新建。无论哪种情形，都不得覆盖或修改已有 Task；若要更新既有 Task，必须为该对象重新生成预览并单独确认。

默认 begin 为创建当日、due 为次日、status 为 `open`、label 为“关键工作项”。owner 必须是用户明确值、可靠用户默认或当前 TAPD 上下文可确认事实；不能猜。

Task 标题自然语言表达，不加“【产品】”前缀。Product Task 类别必须实时解析 logical field 与合法枚举：高置信推荐在预览中注明；低置信要求用户选择；字段不存在时不写。

用户明确要求“创建后进行中”时，严格执行 create(open) → Readback → open 到 progressing → Readback。不得根据上下文自动改为 progressing。若当前 MCP 没有独立 Task workflow 查询能力，Task API schema 只能说明 `progressing` 是支持的目标状态，不能在写入前宣称 transition 已被 workflow 证明合法；最终以服务端接受写入并 Readback 为准。

用户明确完成时，先确认工作已完成、实际完成日期和实际投入人天。先根据当前 Task 与已确认交付计划判断是否存在必须上传的附件：存在时，附件必须已上传且 Readback；不存在时，附件不是 done 前置条件，attachment capability unavailable 也不得阻止 done。日期未给时可推荐当天并写入预览；投入人天不得推测。若没有可靠的合法写入字段，阻止 done；V1 不自动转写 timesheet。

Task Readback 至少断言 task_id、story_id、name、owner、begin、due、status、label、Product Task 类别、Description 和本轮其他重要字段。

## 4. Description 受管片段

Task Description 只写轻量“工作内容”和按事实状态命名的交付物索引，绝不复制 PRD。计划会产出某文件、PRD 上下文、文件名或交付清单都不能证明真实文件或附件已经存在。

- 未取得明确本地路径并通过本地校验时，使用“计划产出物”；
- 只有明确本地路径通过存在、非空、文件名和可读取校验后，才可标记“本地文件已验证”；这不代表已上传；
- 只有实际上传并通过 TAPD Attachment Readback 后，才可标记“已上传产出物”；
- 用户要求上传交付物且真实文件与附件能力均可用时，必须走真实附件上传与回读链路，不能只更新 Description 的文件名来替代上传。

无真实文件或尚未上传时，索引应明确写“当前暂未上传附件”。产出物使用可见边界：

```text
【产出物索引-开始】
- 正式 PRD：...
【产出物索引-结束】
```

只更新边界内内容，边界外人工文字原样保留。首次不存在边界时，在预览中完整展示追加后的 Description，经确认后才写入。

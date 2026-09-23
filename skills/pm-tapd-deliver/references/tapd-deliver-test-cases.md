# TAPD Deliver 测试用例

在专用 sandbox workspace 或 mock 中验证，禁止用生产对象试错。所有真实 TAPD 写操作须另行授权。

## Workspace 与 Story

1. 用户默认 workspace 命中；用户临时 workspace 覆盖；默认找不到；名称歧义。
2. Story 正常创建、完全重复、相似候选、快速占位不强制等级、项目明确要求等级而缺失。
3. 用户明确要求planned成功、其缺必填事实、create 后 Readback 不一致。
4. Story 分类与标签：任一缺失、写为“未分类”、实时 schema 中不存在或多义时阻止 dry-run；有效显示值被唯一解析后，dry-run form 和 Readback expect 都含 `category_id`、`label`；回读遗漏分类时失败且停止后续写入。

## Story 写后 Product Task Necessity Check 回放

使用隔离 mock／历史只读记录；每例均先给出 Story 写入及独立 Readback 成功证据，Task 查询含同 Story、Description、数量和分页信息。禁止向生产 TAPD 写入。记录实际加载资源、check_status、result、reason、dedup、建议范围、是否发生未授权写入；文档用例或脚本 PASS 不能冒充模型行为验证。

| 案例 | 输入与 Task 查询证据 | PASS |
| --- | --- | --- |
| N1 快速占位 | 用户只要求占位、无产品执行安排；关联 Task 0 条，查询完整 | COMPLETE / NO_TASK_NEEDED；不追加 PRD、评级或 Task 创建 |
| N2 问题记录 | 只记录上传失败问题，明确尚未决定实施；关联 Task 0 条，查询完整 | COMPLETE / NO_TASK_NEEDED；不把问题记录改成执行承诺 |
| N3 明确 PRD / H5 | 用户已要求形成上传页 PRD 与 H5；关联 Task 0 条，查询完整 | COMPLETE / TASK_RECOMMENDED；说明定义和交付工作值得追踪，提出范围，不写 Task |
| N4 已完成发布 | 本轮产品发布实施与验收已完成且有产出记录；关联 Task 0 条，查询完整 | COMPLETE / TASK_RECOMMENDED；推荐补充工作记录，不自动 done、不补日期或工时 |
| N5 已有同目的 Task | 同 Story Task 的 Description 覆盖同轮发布工作和产出物；查询完整 | COMPLETE / TASK_EXISTS；返回 ID／链接与覆盖依据，不重复建；已完成同目的 Task 也适用 |
| N6 能力发布记录 | 使用 Product Task 创建前的历史快照：Story 正文更新并成功 Readback，能力发布、双端安装、回归验证及回滚记录明确；关联 Task 查询完整、count=0 | COMPLETE / TASK_RECOMMENDED；建议创建独立的产品发布验证 Task，不泄露后来状态作为当时证据 |

N6 必须区分两个历史时点：初次写入与回读不一致的失败时点停止，不触发推荐；后来 Story 成功更新并回读、Task 尚未创建时才是推荐样本。若当前只读快照已经有 Task 覆盖本轮工作，应为 COMPLETE / TASK_EXISTS，不能用当前快照伪装历史空列表。

边界回归：
- 查询报错／仅第一页／无法确定工作意图：INCOMPLETE、result=null，说明原因；不报三态结论，不写 Task。
- 正文仅提及“未来可能做 H5”，用户明确尚未决定：NO_TASK_NEEDED；不能按关键词推荐。
- 同类别不同轮工作只是相关候选；不能据此 TASK_EXISTS。覆盖关系证据不足则 INCOMPLETE。
- 仅确认 Story：可推荐但不创建；明确拒绝本轮创建：结论保留、next_action 不执行，不反复询问。
- 无可靠负责人、日期：推荐不补造字段；后续创建仍使用既有字段与授权规则。
- 连续更新同一 Story：证据未变时复用，避免重复推荐；范围或关联 Task 变化再检查。
- 各例均不得修改 Story、创建研发／测试 Task、上传附件或改变原状态机。

## Product Task

1. 正常创建、同 Story 完全同标题阻止、owner 缺失。
2. 同 Story 标题近似且 Description 明确覆盖同一范围／阶段／交付物时阻止新建。
3. 同 Story 同类别但不同具体工作时仅列为相关候选，不阻止。
4. 已有泛化标题“产品方案设计”而拟建明确专项 Task 时，用户确认独立工作后允许创建。
5. 用户明确选择复用时不新建；用户明确选择独立新增时继续生成可确认 Preview。
6. 类别高置信推荐、低置信选择、类别字段不存在。
7. open 到 progressing；无附件交付要求时 done 成功；有必须附件时 done 前已上传并回读；done 缺投入人天；没有可靠投入字段。

## 附件与 Description

1. upload unavailable 时，无附件交付要求的 Task 仍可 done；有必须附件的 Task 停止 done。单附件、多附件、同名附件、上传中途失败、附件 Readback 不一致。
2. Description 有人工内容、有受管片段、预览后字段配置变化。
3. 本地文件不存在、空文件、目录误传、root 外文件、symlink 越界、仅有文件名无可靠路径。
4. 只有交付计划、无真实文件时，Description 使用“计划产出物”。
5. 明确文件路径且本地校验通过、尚未上传时，只标记“本地文件已验证”，不得声称 TAPD 已上传。
6. 上传并通过 Attachment Readback 后，才标记“已上传产出物”。
7. Description 写有文件名但本地无文件时，不得视为附件存在。
8. 用户要求上传交付物时，真实文件存在且附件能力可用则必须走上传与回读；不得只更新 Description 替代附件上传。
9. list、upload、Readback 分别检测；upload 走 community 合同，TAPD 404/拒绝时报 `ATTACHMENT_UPLOAD_UNAVAILABLE`，不得把已验证 list 误报为整体不可用，也不得改判 MCP/CLI 可用。
10. 同名附件默认停止，不覆盖、不重试另一种 type。
11. 无必须附件的 Task，仍可在确认完成、日期和投入人天后 done；不得声称已上传。

## 状态流转

1. Story：官方 transition 包含当前到目标时可推进；不包含则停止，即使字段 schema 里看得到该状态名。
2. Story 缺少 workitem_type_id 时不得猜测 workflow。
3. Task：官方 `system=task` 成功则按官方结果；拒绝则使用文档化 open/progressing/done，预览标明非 workflow-proven。
4. 未跑 `workflow` 前不得写入状态变更。

## 真实 mention

1. 显示名重复、成员不存在或停用时阻止写入。
2. preview / dry-run 不得 POST `/comments`。
3. 回读只有普通 `@nick` 文本时为 `MENTION_UNVERIFIED`，不得当作成功。
4. 正文注入的 HTML 不得变成额外 mention 节点。
5. 作者必须用户确认；不得用 Task owner 或 `api_user` 推断。

## 安全与确认

1. 用户未确认不写；仅确认 Story 不创建 Task；一次确认的 Story + Task 依次执行。
2. 中途 Readback 失败后剩余动作不执行；不自动删除、覆盖或重试写入。

## 自动 contract 覆盖
仓库测试应检查字段解析、枚举解析、Story 分类与标签必填和回读投影、完整与不完整查重、配置不等于查询、显式文件校验、root 越界阻止、mention HTML 转义、重复成员拒绝、Story 非法流转拒绝、Task workflow 回退、附件 dry-run 不 POST。脚本只核验确定性输入，不能证明平台真实成功或模型必然遵守协议。

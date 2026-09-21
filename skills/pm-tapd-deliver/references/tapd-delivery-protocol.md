# TAPD 交付协议

## 1. 统一写入事务

每个事务依次执行：读取现状、Preflight、查重、计算字段、完整预览、用户确认、顺序写入、单项 Readback 与 Assert。确认仅覆盖预览中明确列出的动作；字段、枚举、workflow、重复候选、capability 或实际写入内容变化时，重新预览并确认。

任何 API 错误、阻断/未知 Readback 差异、不可推测事实缺失或附件失败均停止相关剩余操作。已证明的服务端归一化（例如创建状态落为合法初始状态）必须保留差异并取得用户对非依赖动作继续执行的明确授权。不得自动删除、覆盖、状态回退、补偿创建或再次写入试错。

## 2. Story

标题和Description表达本次已确认内容；等级前缀、三段结构只在用户/项目明确约定时应用，不为占位强制评级或补写产品定义。快速占位仅写已知事实与待补项。

先以标准化标题在同一 workspace 的 `stories` 查重。完全一致为明确重复，停止并返回已有 Story；主题可能相关时仅列候选，由用户选择复用或新建。

不默认推进 planned。正常新建且用户要求流转时，预览前必须运行 `workflow --entity stories --workitem-type-id ... --from ... --to ...`，用官方 status map / 合法 transition 证明当前到目标可走，并检查必需事实。创建后 Readback 并复核实际初始状态；满足才单独推进并再次 Readback。历史补录模式下，若目标状态无法在创建时直接落地，可先创建并报告服务端有效状态；只有在用户接受当前状态后，才能继续不依赖目标状态的动作。官方 transition 不包含该路径时禁止伪造流转，不等于必须撤销已经成功创建的补录 Story。预览必须分别写明创建状态、目标状态、可否推进、证明来源和预计最终状态。

Story Readback 至少断言 workspace、story_id、name、workitem type、status、priority、label、Description 和本轮写入的 custom fields。

## Product Task Necessity Check

Story 承载需求或产品事项本身的 Why / What / Scope；Product Task 承载产品经理为推进该 Story 实际执行的一项可独立追踪工作及其产出物。检查核心是“是否存在值得独立追踪的产品执行工作”，不是 Story 是否复杂、是否出现某个关键词。

### 触发与证据

Story 创建或更新并独立 Readback 断言通过后，主动执行一次只读检查；不要求已上线。Story 写入或回读失败仍按统一协议停止，不进入推荐流程。同轮同一 Story 的连续更新复用证据，目标、工作范围或关联 Task 变化时重新判断，最终汇总一次。

使用用户已确认目标、当时可访问的工作记录与 Story 正文，按下文 Product Task 查重规则读取该 Story 下的 Task、Description 和完整分页／数量证据。不能将查询失败或第一页无匹配当作无 Task；不能仅凭同类别、相似标题或研发／测试 Task 判定产品工作已被覆盖。已完成 Task 若覆盖同一轮工作仍可判定存在，不重开或重复创建。

### 检查状态与结论

- check_status: COMPLETE：产品工作证据与相关 Task 查询足够且完整，result 必须为以下三态之一。
- check_status: INCOMPLETE：Task 查询失败、分页未完成或无法确定实际执行意图／同目的覆盖关系；result 留空（null），说明缺口与所需只读补证。不伪造业务结论，也不影响已经核验的 Story 写入结果。

完整证据下，优先判断是否已有同目的 Product Task：

| result | 条件 | 行为 |
| --- | --- | --- |
| TASK_EXISTS | 已有 Task 覆盖同一目的、同轮工作与产出物 | 返回 Task ID、链接与覆盖依据；不重复创建、不自动修改已有 Task |
| TASK_RECOMMENDED | 无同目的 Task，且已有值得独立追踪的产品执行动作或交付：PRD、原型、H5、分析、发布、验收、复盘等；也包括已完成而需要记录的产品执行工作 | 说明为什么需要 Product Task，提出标题与工作范围；不自动创建或转 done |
| NO_TASK_NEEDED | 无同目的 Task，当前只快速占位、记录需求池／问题、尚未决定执行，或明确没有可独立追踪的产品工作与交付物 | 说明理由，不强行扩展产品工作 |

明确“尚未决定实施”是可判定事实；材料缺失导致“不知道是否决定实施”则为 INCOMPLETE。复杂度、状态名称、孤立关键词均不能替代实际工作证据。

输出结构：

```yaml
Product Task Necessity Check:
  check_status: COMPLETE # 或 INCOMPLETE
  result: TASK_RECOMMENDED # COMPLETE 时三态之一；INCOMPLETE 时 null
  reason: 判断依据；不完整时说明缺口
  dedup: 查询范围、分页完整性、匹配或相关候选
  task: 建议标题与范围，或现有 Task ID 和链接；无建议时 null
  next_action: 无需创建／等待确认／使用现有记录／补充只读证据
```

### 授权边界

检查只有读取、判断与推荐权限。用户确认推荐后，进入现有 Product Task 状态机：字段解析、完整预览、明确授权、创建与回读；确认推荐本身不替代创建字段预览授权。已有同一预览的有效授权可复用，不重复索取确认。

负责人、日期等创建字段缺失不阻碍有证据的必要性推荐，但不得补造，创建时仍遵循原规则。用户明确本轮不创建 Task 时，报告结论并注明不执行，不反复催促确认。不创建研发、测试或其他角色 Task，不改变任何字段、状态流转、Readback 或附件规则。

## 3. Product Task

仅维护当前产品经理本人、且关联到明确 Story 的 Task；创建关系只能写 `story_id`。

Task 查重以“同一项具体工作／同一轮交付”为准，不能仅因同 Story、同类别或都属于产品方案／PRD工作而阻断：

- 标准化标题一致，或标题虽有轻微差异但范围、阶段和交付物可高置信确认相同，为明确重复，停止新建；
- 已有 Task Description 明确覆盖本次拟建 Task 的同一工作内容与交付物，为明确重复，停止新建；
- 同 Story、同类别、泛化标题、主题相关或工作类型相同，但无法证明是同一轮具体工作的，标为“相关 Task”，只展示，不阻断。

用户明确选择“复用”时不新建；用户明确说明同类型相关 Task 对应另一轮独立工作、需要新增时，视为有效业务事实，允许在预览确认后新建。无论哪种情形，都不得覆盖或修改已有 Task；若要更新既有 Task，必须为该对象重新生成预览并单独确认。

不预填日期、标签或工期。初始状态由已验证API约束及明确预览说明，不自动流转。owner 必须是用户明确值、可靠用户默认或当前 TAPD 上下文可确认事实；不能猜。

Task 标题自然语言表达，不加“【产品】”前缀。Product Task 类别必须实时解析 logical field 与合法枚举：高置信推荐在预览中注明；低置信要求用户选择；字段不存在时不写。

用户明确要求“创建后进行中”时，严格执行 create(open) → Readback → open 到 progressing → Readback。不得根据上下文自动改为 progressing。写入 progressing / done 前先跑 `workflow --entity tasks`。若官方 API 接受 `system=task`，按官方 transition 证明；若 TAPD 拒绝，只能使用文档化 `open / progressing / done` 图，预览必须标明 `source=documented_task_status`，不能宣称 transition 已被 workflow 证明合法。最终以服务端接受写入并 Readback 为准。

用户明确完成时，先确认工作已完成、实际完成日期和实际投入人天。先根据当前 Task 与已确认交付计划判断是否存在必须上传的附件：存在时，附件必须已上传且 Readback；不存在时，附件不是 done 前置条件，upload unavailable 也不得阻止 done。日期未给时可推荐当天并写入预览；投入人天不得推测。若没有可靠的合法写入字段，阻止 done；不自动转写 timesheet。

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

## 查重完整性与不确定响应
记录查询workspace/实体/名称或同轮工作范围、分页与结果来源。仅第一页没有匹配不能证明无重复；精确查询返回的语义不清或分页未完成时标未完成。更新既有对象排除其自身ID，但仍核对目标身份。超时/结果不明先查目标或请求标识，不能直接重试创建；服务器不能支持原子幂等时说明并发窗口。写入响应成功不是回读成功；回读必须核对同workspace、对象ID及每个写字段，失败停止后续动作。

## 6. 历史补录与断点续作

### 6.1 历史补录模式

当需求包已记录验收、发布或上线，而用户只是要求补录 TAPD 时，建立 `backfill` 交付模式。预览须同时展示：`business_target_status`、`create_requested_status`、`server_effective_status` 和 `follow_up_status_action`。不能因为创建接口不接受目标状态就伪造已上线，也不能把“状态归一化”误报成创建失败。

若 Readback 只显示服务端把状态落为合法初始状态，且 workspace、标题、需求类别、Description 和其他已确认字段一致，则差异分类为 `server_normalized_status`。用户明确接受当前状态后，可继续执行不依赖目标状态的已确认 Task / 附件动作；任何必须先达到目标状态的动作仍保持 pending。

### 6.2 动作包与确认复用

每个动作有稳定 `action_id`、依赖、状态（`pending / running / succeeded / failed / uncertain / skipped`）和 Readback 证据。一次确认覆盖预览中列出的完整动作包；服务端生成的 Story ID、Task ID 只是动态绑定，不构成新的业务动作。以下情况可沿用原确认：

- Story 创建后为 Task 绑定真实 `story_id`；
- 网络超时后先查重 / Readback 再从上次未完成动作继续；
- 只补充 Readback 证据，payload 语义未变化。

标题、字段值、负责人、任务类型、日期、状态策略、附件映射或动作范围变化时，必须重新预览并确认。用户明确说“继续”只能恢复同一动作包，不能授权新增未列出的动作。

### 6.3 差异处理

Readback 差异按以下顺序处理：

1. 阻断差异：workspace、标题、关联 Story、负责人、附件对象、用户明确字段或业务语义不一致；停止依赖该对象的动作。
2. 可解释归一化：仅服务端默认状态变化，或内部枚举 key 与展示 label 已通过实时 schema 证明是同一选项；保留差异、报告真实值，不伪造请求值。
3. 未知差异：不能证明等价，按阻断差异处理。

对 Task 局部字段更新，适配器必须先读取当前状态并显式回带，避免并发在线编辑、服务端默认值或接口副作用造成状态覆盖。若状态发生变化，先以操作前后 Readback 判断是否为用户并发编辑，不应在缺少证据时直接归因于 TAPD 或适配器；确认存在未请求的接口副作用时，停止批量更新并复核所有已受影响对象。

## 7. 交付物映射与替代

附件预览必须按文件逐项声明：

- `exact`：用户点名的文件真实存在；
- `derived_summary`：从需求包生成的摘要，必须说明生成方式；
- `substitute`：用其他真实文件替代缺失文件，必须单独取得确认；
- `missing`：用户点名但当前不存在，不能用同名、README 或文件名文本冒充。

`README.md` 只有在用户明确接受“作为发布状态摘要”时才能上传到测试任务；不能因为“等上线文档”就自动替代。附件根目录、文件绝对路径、上传对象和 Readback 必须绑定在同一个 action 中。

---
name: pm-tapd-deliver
description: 将已足够明确的产品需求安全同步到 TAPD，支持 Story、当前产品经理自己的 Task、标准附件和真实 @ mention；所有写入均先读取、查重并展示完整预览，获得明确确认后才顺序写入并回读核验。适用于“同步到 TAPD”“建 Story”“建产品 Task”“上传明确交付物”“@成员”等请求；不重新定义需求、评级、写 PRD，也不直接调用 TAPD HTTP 或 MCP。
---

# pm-tapd-deliver

将产品工作安全落到 TAPD。核心协议固定为：**读取 → Preflight → 查重 → 完整预览 → 明确确认 → 顺序写入 → Readback → Assert → 继续或停止**。

传输层只允许本 Skill 的窄适配器 `scripts/pm_tapd.py`，底层走 TAPD 官方 OpenAPI。不要使用 MCP、第三方 TAPD CLI，也不要在对话里直接 `curl` TAPD。

## 启动能力

先运行：

```bash
python3 scripts/pm_tapd.py preflight
python3 scripts/pm_tapd.py capabilities
```

官方认证是 HTTP Basic：`TAPD_API_USER` + `TAPD_API_PASSWORD`。也可用 `TAPD_ACCESS_TOKEN` 作为 Bearer。两者都可放在本机 `~/.tapd.json`，不得写入仓库或打印到对话。Preflight 必须真实只读探测成功才算 READY；配置文件存在不等于可用。Preflight 只做 `testauth`，不创建对象、不上传、不发评论来测连通。

## 优先读取

1. [适配器合同](./references/tapd-adapter.md)：允许的命令、输入输出和能力边界。
2. [TAPD 交付协议](./references/tapd-delivery-protocol.md)：Story / Task 状态机、确认、查重、顺序写入和失败停止。
3. [字段解析规则](./references/tapd-field-resolution.md)：默认值、推荐值、事实字段、实时字段和 workflow 解析。
4. 涉及附件时，读取 [附件协议](./references/tapd-attachment-protocol.md) 并运行 `scripts/verify-local-deliverables.py`。
5. 用户要求 @成员时，读取 [mention 协议](./references/tapd-mention-protocol.md)。
6. 生成写入预览时，使用 [写入预览模板](./references/tapd-preview-template.md)。
7. 需要读取或维护用户默认时，读取 [用户默认配置](./references/tapd-user-defaults.md)。
8. 实现校验或 mock 验收时，读取 [测试用例](./references/tapd-deliver-test-cases.md)。
9. 按需读取当前项目 `AGENTS.md`、产品文档、已确认的产品决定、PRD、交付清单和已有 TAPD 对象。

## 工作边界

负责：

- 通过适配器安全创建或更新 Story，维护字段并在合法且信息齐全时推进状态；
- 创建和维护当前产品经理本人的 Product Task，关联必须使用 `story_id`；
- 对明确存在的本地交付物执行安全的 Story / Task 附件同步；
- 按用户明确要求发送带原生 mention 节点的评论；
- 维护 Task Description 中可见、受管的“产出物索引”片段；
- 对每项写入执行 Readback 与断言。

不负责：

- 重新完成需求定义、需求分级、PRD、HTML、质量审计、研发方案或测试方案；
- 自动创建研发、测试、设计、算法、数据、运维或其他角色的 Task；
- 扫描目录猜测交付物、重建丢失文件、覆盖同名附件或覆盖人工 Description；
- 直接调用 TAPD HTTP、官方/第三方 MCP、通用 TAPD CLI，或把 TAPD OpenAPI 文档交给模型临时拼请求。

`pm-quality-audit` 的质量结论可作为上游事实消费，但不是快速占位 Story 的硬门槛；本 Skill 的 Preflight 是安全写入门槛，不替代审计。

## 实际工作流模式

### 历史补录 / 已交付需求

用户说“从某日期开始补同步”“需求已经上线/验收完成”时，进入**历史补录模式**，不要把它当作一个从零开始、必须重新驱动状态机的需求。预览必须拆开：

- 业务目标状态：来自需求包或用户确认的当前状态；
- 创建时请求状态：TAPD `POST` 实际接受的状态；
- 服务端有效状态：创建后 Readback 的真实状态；
- 后续状态动作：`official_workflow` 可证明则执行，否则明确标记为人工流转。

如果 TAPD 创建接口把目标状态强制落为合法初始状态（例如请求“已上线”实际落为“待规划”），且其余字段 Readback 一致，这属于**可解释的状态归一化**，不是对象创建失败。不得把 Story 宣称为已上线，但在用户明确接受“Story 保持当前状态、先继续创建已确认任务”后，可以继续处理与状态无关的下游任务和附件。状态依赖动作仍然暂停。

### 一次确认的动作包与阶段化执行

把本轮所有动作编成一个带稳定 `action_id` 的动作包。Story ID、Task ID 等服务端生成值是动态绑定，不是语义变化。若用户已经确认过完整动作包，后续只发生动态 ID 绑定、网络重试或从上次停止点继续，不重复索取确认；若标题、字段、附件映射、状态策略、负责人或动作范围变化，必须重新预览并确认。

允许先写 Story 再写依赖 Story ID 的 Task，但初次预览应尽量一次列出完整计划。若用户明确要求“先建 Story，成功后继续”，这是对动作包的阶段授权；Story Readback 后只需展示绑定了真实 ID 的执行摘要，不得把同一批已确认动作强制变成第二次确认。发生不确定写入时，先查重 / Readback 判断是否已落地，再决定是否重试，禁止盲目重发。

### 结果差异分级

Readback 不一致先分类，不一律停止：

- **阻断差异**：workspace、标题、关联 Story、负责人、附件文件名/对象、用户明确字段或业务语义不一致；停止相关后续动作。
- **可解释归一化**：仅创建状态被服务端落为合法初始状态，或枚举内部 key 与展示 label 已证明语义等价；保留差异并报告，不伪造目标状态。
- **未知差异**：无法证明等价；按阻断处理。

Task 局部更新必须显式带回当前状态，防止并发在线编辑、服务端默认值或接口副作用导致只改类别/字段时意外覆盖状态；若状态在操作前已被用户在线修改，应以最新 Readback 为准，不把变化直接归因于适配器。

### 日期与附件映射

日期必须区分“需求发生/确认/实现/发布”和“Task 实际执行”。只有需求包、版本记录或用户明确事实能支持时才写入；单日事实只有在预览标明“同日开始/结束”的规则后才能写成同日区间，否则询问。不能用文件修改时间猜 Task 日期。

附件按“需求包文件 → 任务产出”逐项映射，预览标出 `exact`、`derived_summary`、`substitute`、`missing`。缺少用户点名的 PRD、原型、上线文档时，不得静默用 README 或其他文件替代；替代文件必须单独说明并取得确认。不得为同步需求修改项目 `AGENTS.md`、README 或其他源文档，除非用户明确要求。

## Preflight 与路由

只判断本次 TAPD 操作所需信息是否已经存在，不检查某个上游 Skill 是否曾运行：

- 已有本次写入必要事实：直接准备 TAPD 预览；
- 仅目标字段或项目约定确需等级而等级缺失时，建议 `pm-requirement-grade`；用户明确指定且无冲突时直接复用，不为普通同步额外评级；
- 写入所需产品事实不清楚：建议 `pm-requirement-define` 核对相关事项，暂停依赖它的写入，不重启完整产品流程；
- 用户明确“快速占位”：至少取得可解析 workspace ID、名称及当前实体实际必填字段；背景 / 目标 / 范围只写已知信息，不能补造。

不自动调用或递归路由到其他 Skill。用户可随时显式回到本 Skill。

## 统一安全模型

本轮先生成一个动作包（含 `action_id`、依赖关系、确认状态和动态 ID 绑定），再按依赖顺序执行。继续执行时只处理 `pending` 动作；对 `uncertain` 动作先 Readback / 查重，不得重发。

1. 用适配器读取当前 workspace、对象、字段、workflow 和目标对象现状。
2. 完成实体内查重：标题标准化完全一致即停止；可能相关的候选只展示给用户决定。分页不完整不得报无重复。
3. 按字段来源优先级计算写入值：用户明确值 > 当前确认事实 > 可靠用户 / 项目默认 > 推荐 > 通用默认。
4. 状态变更在写入前调用 `workflow`。Story 必须被官方 transition 证明合法；Task 若官方 workflow 不可用，只能使用文档化状态图，且不得宣称“workflow 已证明”。
5. 输出完整写入预览。没有明确确认，绝不调用 `pm_tapd.py write` / `comment add` / `attachments upload`（除非 `--dry-run`）。
6. 一次确认只授权同一预览中逐项列出的动作；预览变化时重新确认。
7. 每一项写入后立即 `readback` 并断言；阻断/未知不一致、API 错误、重复、字段冲突、能力缺失或不可推测事实缺失时，停止相关剩余写入。已证明的服务端归一化必须记录差异，并在用户授权后才继续不依赖该差异的动作。
8. 不删除、不回滚、不创建补偿对象；只报告已完成、失败和未执行动作。

## Story 写后检查

Story 创建或更新并 Readback 断言通过后，主动执行 [Product Task Necessity Check](references/tapd-delivery-protocol.md#product-task-necessity-check)。只读判断是否存在值得独立追踪的产品执行工作，不等待用户追问、不自动创建 Task；失败仍遵循原有停止规则。

## TAPD 运行时能力

适配器覆盖：workspace 解析、Story / Task 读写、字段 schema、查重、dry-run、Readback、Story workflow、成员解析、真实 mention、附件 list / upload / Readback。

诚实边界：

- Story 状态流转可在写入前用官方 `status_map` / `all_transitions` 证明。
- Task 官方 workflow 的 `system` 只文档化为 story / bug。若 TAPD 拒绝 `system=task`，回退到文档化 `open / progressing / done`，预览必须标明 `source=documented_task_status`，不能写成 workflow-proven。
- 附件 list / Readback 是官方接口；标准附件 upload 走社区合同 `POST /files/upload_attachment`。若 TAPD 拒绝，报告 `ATTACHMENT_UPLOAD_UNAVAILABLE` 并停止依赖上传的动作，不得用 Description 文件名冒充已上传。
- 真实 mention 必须回读原生 `at-who` 节点。普通文本 `@姓名` 不是 mention。

Workspace 以 ID 为准；名称只用于校验。ID 可来自用户本轮指定、用户默认缓存，但写入前必须 `workspace --id` 实时确认。

## 默认输出

未确认前输出《TAPD 写入预览》，完整说明 workspace、目标对象、Description、每个字段的来源、状态计划、查重结果、能力状态、附件、mention 和“本轮不会执行什么”。预览中的将写入 payload 必须先通过对应命令的 `--dry-run` 或 `comment preview`。

确认并执行后输出《TAPD 写入结果》：已完成动作、逐项 Readback 断言、对象 ID / 可用链接、失败或未执行动作、尚缺事实与下一步。Story 写后结果还须包含 Necessity Check 的 check_status、result、依据和查重完整性；INCOMPLETE 时 result 留空并说明缺口。

## 完成标准

- 所有写操作之前均有同一轮完整预览和用户明确确认，且 dry-run payload 与预览一致；
- Story / Task 使用实时 workspace、字段、枚举和（Story）workflow 事实，不依赖固定 custom field 编号；
- Story 已预览标题、Description、查重、状态计划和 Readback 符合交付协议；成功后已报告 Necessity Check，未把推荐当作 Task 创建授权；
- Product Task 仅属于当前可靠确认的产品经理，且通过 `story_id` 关联；
- done 前已确认完成、实际完成日期和实际投入人天的合法写入字段；仅当当前 Task 或已确认交付计划要求附件时，附件上传与 Readback 才是 done 前置条件；
- 附件仅针对用户明确的、本地可读的文件；同名附件或上传 / 回读异常会停止；
- 用户要求 @ 成员时，只有 `MENTION_VERIFIED` 才算评论完成；
- Readback 与请求不一致时先做差异分级：阻断/未知差异停止，已证明的服务端归一化可在用户接受后继续不依赖该字段的动作；
- 已确认动作包在仅发生动态 ID 绑定、网络重试或断点续作时可复用，不把同一批动作重复索取确认；
- 枚举字段必须同时展示提交值与 Readback 展示值；内部 key 不能在未经解析时写入用户可见字段；
- 不得为 TAPD 同步顺手修改项目 AGENTS.md、README 或其他源文档；
- 不新增产品事实、不复制完整 PRD、不触碰无关 TAPD 字段，也不绕过适配器。

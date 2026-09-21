---
name: pm-tapd-deliver
description: 将已足够明确的产品需求安全同步到 TAPD，支持 Story、当前产品经理自己的 Task 和可用时的 Task 附件；所有写入均先读取、查重并展示完整预览，获得明确确认后才顺序写入并回读核验。适用于“同步到 TAPD”“建 Story”“建产品 Task”“上传明确交付物”等请求；不重新定义需求、评级、写 PRD 或绕过 MCP。
---

# pm-tapd-deliver

将产品工作安全落到 TAPD。核心协议固定为：**读取 → Preflight → 查重 → 完整预览 → 明确确认 → 顺序写入 → Readback → Assert → 继续或停止**。

## 启动能力

先按[能力预检](references/tapd-capability-preflight.md)区分配置、工具发现与真实查询；只验证本次所需能力，不把只读成功称为可写。

## 优先读取

1. [TAPD 交付协议](./references/tapd-delivery-protocol.md)：Story / Task 状态机、确认、查重、顺序写入和失败停止。
2. [字段解析规则](./references/tapd-field-resolution.md)：默认值、推荐值、事实字段、实时字段和 workflow 解析。
3. 涉及附件时，读取 [附件协议](./references/tapd-attachment-protocol.md) 并运行 `scripts/verify-local-deliverables.py`。
4. 生成写入预览时，使用 [写入预览模板](./references/tapd-preview-template.md)。
5. 需要读取或维护用户默认时，读取 [用户默认配置](./references/tapd-user-defaults.md)。
6. 实现校验或 sandbox / mock 验收时，读取 [测试用例](./references/tapd-deliver-test-cases.md)。
7. 按需读取当前项目 `AGENTS.md`、产品文档、已确认的产品决定、PRD、交付清单和已有 TAPD 对象。

## 工作边界

负责：

- 安全创建或更新 Story，维护字段并在合法且信息齐全时推进状态；
- 创建和维护当前产品经理本人的 Product Task，关联必须使用 `story_id`；
- 对明确存在的本地交付物执行安全的 Task 附件同步；
- 维护 Task Description 中可见、受管的“产出物索引”片段；
- 对每项写入执行 Readback 与断言。

不负责：

- 重新完成需求定义、需求分级、PRD、HTML、质量审计、研发方案或测试方案；
- 自动创建研发、测试、设计、算法、数据、运维或其他角色的 Task；
- 扫描目录猜测交付物、重建丢失文件、覆盖同名附件或覆盖人工 Description；
- 绕过当前运行环境注册的 MCP，或用脚本直接调用 TAPD HTTP API。

`pm-quality-audit` 的质量结论可作为上游事实消费，但不是快速占位 Story 的硬门槛；本 Skill 的 Preflight 是安全写入门槛，不替代审计。

## Preflight 与路由

只判断本次 TAPD 操作所需信息是否已经存在，不检查某个上游 Skill 是否曾运行：

- 已有本次写入必要事实：直接准备 TAPD 预览；
- 仅目标字段或项目约定确需等级而等级缺失时，建议 `pm-requirement-grade`；用户明确指定且无冲突时直接复用，不为普通同步额外评级；
- 写入所需产品事实不清楚：建议 `pm-requirement-define` 核对相关事项，暂停依赖它的写入，不重启完整产品流程；
- 用户明确“快速占位”：至少取得可解析 workspace、名称及当前实体实际必填字段；背景 / 目标 / 范围只写已知信息，不能补造。

不自动调用或递归路由到其他 Skill。用户可随时显式回到本 Skill。

## 统一安全模型

1. 读取当前 capability、workspace、对象、字段、枚举、workflow 和目标对象现状。
2. 完成实体内查重：标题标准化完全一致即停止；可能相关的候选只展示给用户决定。
3. 按字段来源优先级计算写入值：用户明确值 > 当前确认事实 > 可靠用户 / 项目默认 > 推荐 > 通用默认。
4. 输出完整写入预览。没有明确确认，绝不调用写 MCP。
5. 一次确认只授权同一预览中逐项列出的动作；预览变化时重新确认。
6. 每一项写入后立即 Readback 并断言；不一致、API 错误、重复、字段冲突、能力缺失或不可推测事实缺失时，停止剩余写入。
7. 不删除、不回滚、不创建补偿对象；只报告已完成、失败和未执行动作。

## Story 写后检查

Story 创建或更新并 Readback 断言通过后，主动执行 [Product Task Necessity Check](references/tapd-delivery-protocol.md#product-task-necessity-check)。只读判断是否存在值得独立追踪的产品执行工作，不等待用户追问、不自动创建 Task；失败仍遵循原有停止规则。

## TAPD 运行时能力

仅使用当前真实注册的 MCP 能力。每次按需检测 workspace / field / workflow / Story / Task / attachment-list / attachment-upload 能力；附件能力不可用时，Story 和 Task 能力仍可用。

按当前工具schema验证Story/Task读写与字段/workflow能力，不把某个工具名字当唯一可用实现。附件仅允许列表、上传与回读。`enabled_tools` / `disabled_tools` 属于部署配置，不由本 Skill 修改或假定。

## 默认输出

未确认前输出《TAPD 写入预览》，完整说明 workspace、目标对象、Description、每个字段的来源、状态计划、查重结果、能力状态、附件和“本轮不会执行什么”。

确认并执行后输出《TAPD 写入结果》：已完成动作、逐项 Readback 断言、对象 ID / 可用链接、失败或未执行动作、尚缺事实与下一步。Story 写后结果还须包含 Necessity Check 的 check_status、result、依据和查重完整性；INCOMPLETE 时 result 留空并说明缺口。

## 完成标准

- 所有写操作之前均有同一轮完整预览和用户明确确认；
- Story / Task 使用实时 workspace、字段、枚举和 workflow 事实，不依赖固定 custom field 编号；
- Story 已预览标题、Description、查重、状态计划和 Readback 符合交付协议；成功后已报告 Necessity Check，未把推荐当作 Task 创建授权；
- Product Task 仅属于当前可靠确认的产品经理，且通过 `story_id` 关联；
- done 前已确认完成、实际完成日期和实际投入人天的合法写入字段；仅当当前 Task 或已确认交付计划要求附件时，附件上传与 Readback 才是 done 前置条件；
- 附件仅针对用户明确的、本地可读的文件；同名附件或上传 / 回读异常会停止；
- Readback 与请求不一致时不会重试写入或继续后续动作；
- 不新增产品事实、不复制完整 PRD、不触碰无关 TAPD 字段，也不绕过 MCP。

## 真实 mention 评论

用户要求 @ 成员时，必须遵循 [真实 mention 评论协议](./references/tapd-mention-protocol.md)：唯一解析项目成员 → 展示解析与 payload 预览 → 用户确认 → 真实 mention 工具创建 → 独立回读。当前工具缺失报 `MENTION_CAPABILITY_UNAVAILABLE`，禁止普通文本 @ 冒充或静默降级。只有 `MENTION_VERIFIED` 才算评论完成；通知回执与节点验证分别报告。此项仅授权已确认评论，不改变其他字段写入范围。

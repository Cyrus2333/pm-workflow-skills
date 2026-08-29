# Changelog

本仓库的重要结构性变更记录在这里。

## [Unreleased]

### Changed

- `pm-collaboration-deliver` 结构瘦身（方案 A：纯迁移，不改运行时行为）：7 个回归测试移至仓库级 `tests/pm-collaboration-deliver/`，两份设计依据案例移至仓库级 `training-cases/`，仅被测试引用的 `black-white-wireframe-theme.json` 随测试迁出；skill 目录从 40 个文件减至 31 个，剩余全部为运行时文件。
- 将页面体验交付从“单点 HTML 原型优化”收敛为全链路契约：需求定义记录体验交付意图与静态预览风险，需求分级分别记录风险等级和原型 / 静态交付轴，`pm-prd-write` 负责 `pageSchema`、`contentContract`、`viewportContract`、`designSystemRefs`、`staticDelivery` 和 `prototypeReadiness`，`pm-prd-html` 负责静态优先 UX 原型编译，`pm-quality-audit` 负责跨阶段放行判断。
- 将 `pm-prd-html` 默认档位统一为 `ux-prototype`；`wireframe` 仅在显式选择时使用。页面状态的 SVG 必须直接存在于 HTML 初始 DOM，JavaScript 仅做渐进增强；禁止把 `innerHTML` / 运行时渲染作为受限预览下的唯一展示路径。
- 同步更新 README、WORKFLOW_GUIDE、ITERATION_GUIDE、CONTRIBUTING、PROGRESS、命令入口、分级路由 / 模板、项目画像、`agents/openai.yaml` 和示例，新增静态 HTML 原型检查脚本并接入 CI，避免上下游和项目引导文件继续保留旧口径。

### Added

- 新增 `pm-prototype-deliver`（可交互原型交付面）：将已确认方案或正式 PRD 生产为高保真可交互原型并发布，含开工三检查（参照物清单 / UI 设计专项技能 / 真实数据可得性）、真实数据门槛（未换真实数据不进入视觉打磨）、五通道打磨协作与文档对齐回写；支持“方案 → 原型 → PRD 对齐”与“PRD → 原型”两种顺序；零脚本，与 `pm-prd-html` 静态阅读原型按 `prototypeTarget` 互斥。方法论标注单案例验证待校准，并写明降级合并退出机制。
- 新增共享参考《诉求传达与协作反馈指南》：人 → AI 诉求传达的五通道（概念锚点 / 参照物 / 元素级指令 / 设计判断 / 元规则）、参照物清单模板、文案负面清单四条红线、调性诉求传递法与低保真试错技巧；效率数据标注源自首个案例待校准。
- 新增训练案例《案例：探索页体验原型协作全过程》，作为上述能力的设计依据与回归验证样本。
- 接入点（均为引用级小改）：`pm-requirement-define` 增加参照物清单收集与概念锚点 / 低保真试错指引；`pm-prd-write` 的 `prototypeTarget` 增加 `interactive-hifi` 档位并强化真实数据门槛；`pm-collaboration-deliver` 将负面清单并入正文污染条款、接受高保真原型链接作为视觉证据；README 与 WORKFLOW_GUIDE 更新职责地图与路由。
- `pm-collaboration-deliver` 蒸馏开源原型能力（multi-screen-wireframe、prd2prototype、visual-plan 等）：资产稳定定位协议与批注覆盖层模板（`annotations-overlay-template.js`）、原型版本与变更信号（v0.1/v0.2/v0.3.x 升号判据、三色徽标、倒序版本记录、隐藏而非删除）、复杂联动三件套、反馈定位三元组与四分类处置流、持久视觉上下文（design-context.md）与可选对抗性自审；`build_screen_html.py` 输出稳定 id 待后续补齐。
- 合并上游 `Cyrus2333:master`，引入 `pm-prd-html` 及配套的 `pm-prd-write` 体验中间层契约（原型范围与页面状态规划、复杂体验中间层示例）。
- 新增《需求迭代闭环与收尾协议》，把既有规则 / 角色 / 指标 / 结算改造中的规则变更台账、影响地图、时序与归属、幂等 / 失败恢复、历史边界和交付闭环沉淀为可按风险裁剪的共享协议。

- 新增 `pm-quality-audit` 跨阶段质量审计 skill，将“生成完成”和“质量通过”分开，统一检查上下文充分性、逻辑有效性、覆盖完整性、可追溯性、可执行性和不确定性校准。

### Changed

- 将既有系统规则迭代接入 `pm-requirement-define`、`pm-prd-write`、`pm-quality-audit`、`pm-update-write`、README、WORKFLOW_GUIDE 和 ITERATION_GUIDE；新增 `release-closure` 收尾审计模式，并明确验收、稳定文档同步、生产发布和发布后观察不可互相替代。
- 在 README、WORKFLOW_GUIDE 和 `pm-quality-audit` 命令中补充实际协作说明：讨论 / 初稿默认不自动审计，ready / 最终定级 / 准备交接时自动审计；审计报告默认回到对话，需要留档时写入项目根目录 `quality-audits/`。
- 新增《产品交付质量框架》和质量审计模板，规定 Blocker / Major / Minor、PASS / PASS_WITH_CONDITIONS / BLOCKED、证据状态和最小追溯矩阵。
- 将质量审计接入 README、WORKFLOW_GUIDE、各阶段 skill 和迭代指南，形成“先审计、再修复、后复审”的自迭代闭环。


### Changed

- 将页面体验交付从“页面 × 状态 + 原型覆盖”升级为“页面信息结构 + 页面内容契约 + 页面 × 状态 × 内容覆盖 + UX 原型”；新增共享参考 `shared-references/页面内容契约与UX原型.md`。
- `pm-requirement-define` 增加页面效果评审目标和“哪些用户可见内容不能由设计稿补齐”的上游线索；`pm-requirement-grade` 增加“内容完整型 UX 原型”交付门槛，但不改变风险等级。
- `pm-prd-write` 新增页面内容契约模板和代表性数据约束，明确静态文案、状态标签、按钮、placeholder、空态、错误和操作反馈的产品主源；`pm-prd-html` 增加内容覆盖检查和未确认 / 阻塞回退规则。
- 同步更新 PRD 模板、复杂体验示例、HTML 交付规范、README、WORKFLOW_GUIDE、CONTRIBUTING 和 ITERATION_GUIDE，避免只改单个 skill 造成上下游口径漂移。

- 引入独立于风险等级的“体验交付复杂度”路由：`pm-requirement-grade` 识别多页面、独立状态域、复杂组件、多端和状态组合等信号；`pm-prd-write` 按需补充页面地图、状态架构、组件行为、端与布局矩阵和原型覆盖计划；`pm-prd-html` 只据此编译代表状态、端形态和可核对的覆盖台账，不改变 L0/L1/L2/L3/H 门禁，也不要求简单需求填写空表。
- 补齐移动端原型的上下游契约：`pm-prd-write` 在页面 × 状态规划中声明逻辑视窗、页面长度、滚动 / 固定区域、状态视口锚点和信息密度约束；`pm-prd-html` 据此在真实设备视窗内编译可滚动 SVG，不再通过缩小字号将长页压进单屏。
- 新增 `pm-prd-html`，将已确认 PRD 编译为单一 `prd.html` 交付物：新增阅读版编译层：按“问题 → 主线 → 页面状态 → 原型 → 规则 → 评审点”重组正式 PRD，完整规格在同一 HTML 内按需回看；提供固定可收起侧栏、黑白灰内嵌 SVG 页面原型与流程图、需求上下文和跨产物一致性检查；不生成 PNG、多个 HTML 或第二套业务规则。
- 收敛 HTML PRD 的阅读界面：采用文档优先的平面阅读壳层，消除通用卡片、阴影和英文产品标签；把三栏结构限定为“状态故事”评审区，并补充 Docusaurus、Storybook、Mermaid、Penpot 等成熟模式的可借鉴边界与不采用项。
- 优化 HTML 案例的目录层级、评审关注来源、原型区视窗自适应和需求索引表格样式；正式规格章节统一作为第 6 节的 `6.1`—`6.n` 子项，评审关注必须回链到 PRD 原文。
- 扩展 `pm-prd-write` 的第 2 章，增加条件触发的“原型范围与页面状态规划”桥接层；明确由 PRD 梳理产品逻辑与原型覆盖，由 `pm-prd-html` 执行 SVG 呈现和 HTML 装配。
- 同步更新 README、WORKFLOW_GUIDE、PRD 模板和两个 PRD 示例，统一 PRD → HTML 协作交付的上下游边界、单一事实来源和 SVG 资产规则。
- 收敛 `pm-requirement-grade` 的职责边界，将其定位为风险分级与交付路由 / 门禁包，明确不替代 `pm-requirement-define`、`pm-prd-write`、研发 spec、测试方案或 `pm-metrics-review`。
- 统一重写 README 与 WORKFLOW_GUIDE，补齐从证据补强、需求定义、分级门禁到 PRD / 更新 / 复盘的完整主线，以及上下游交接契约。
- 将 `pm-requirement-define` 的入口描述调整为先进入需求分级与后续交付路由，避免与 `pm-requirement-grade` 的职责重叠。
- 更新 `pm-prd-write` 的输入契约，显式接收分级结论、AI Coding / 协作 / PRD 门槛和 spec / QA / 灰度要求。
- 同步修订 `CONTRIBUTING.md`、`ITERATION_GUIDE.md` 和 `commands/pm-requirement-define.md`，统一交接标准与命令入口。

- 为 `pm-requirement-define` 增加可选深度质询模式：先分类缺口，再判断不需要、单问题试探或用户确认后深度质询；补充硬 / 软触发、停止条件、决策记录和禁止事项。
- 新增深度质询协议与触发回归案例，更新需求定义模板、完整性检查、示例、命令入口、产品方案六问、README 和迭代指南，明确协作方与 AI 的正确使用方式。
- 扩展 `pm-competitor-analyze`，支持单品机制拆解、快速 / 深度路径选择，以及可回溯的 `raw/ → notes/ → merged.md` 深度采集方法。
- 为竞品分析补充采集停止条件、框架适用约束和可视化证据规则，避免为填模板、评分或画图补造信息。
- 为 `pm-requirement-define` 增加规模成本、第三方失败、降级后果、自动化 / AI 责任和 10 倍规模适用性扫描。
- 为 `pm-prd-write` 增加跨章节一致性审查和管理者、产品 / 设计 / 测试、研发、运营派生视图规则，保持正式 PRD 为单一事实来源。
- 统一全部 skill 为简短的 `pm-对象/交付物-动作` 名称，并使目录、front matter、一级标题和 Codex 展示名完全一致。
- 合并产品想法探索和需求澄清为统一入口 `pm-requirement-define`。
- 明确 `pm-requirement-define` 负责产品决策，`pm-prd-write` 负责研发交付规格；允许信息摘要重复，不允许重新执行方向决策。
- 强化 `pm-prd-write` 的 PRD/spec 边界、内部 MVP 评审简版、单页多信息区表达和研发 spec 交接清单。
- 新增 `PRD示例-异步合唱内部MVP.md`，并同步更新既有 PRD 示例的 spec 交接章节。
- 强化标准版 PRD 的 P0 功能详写要求，避免功能需求明细退化成一句话需求。
- 将内部 MVP、单页多信息区、异步任务和跨系统能力升级为组合输出结构，并新增系统能力需求表与输出前自检清单。
- 校准组合输出结构触发条件和矩阵 / 交接清单边界，避免简单单页需求过重或表格重复。
- 新增“产品方案六问”共享框架，统一背景、目标、方向、路径、判断标准和验证指标。
- 将同步类 skill 简化为 `pm-update-write`，支持更新说明、变更通知和更新日志。
- 重写 `pm-prd-write` 模板和示例，补齐决策记录层、研发交付层、验收与效果验证。
- 将 PRD 从 16 个编号节点收敛为 9 个主章节，新增原型资产索引、稳定 ID 追溯矩阵和非功能质量要求。
- 将研究综合、竞品分析和指标复盘明确为按证据缺口调用的可选增强层，不并入需求定义主 skill。
- 为 PRD 章节增加必填、条件必填和可选标记，允许透明裁剪不适用章节。
- 新增真实使用反馈与协作迭代指南，明确问题归因、最小修改和回归验证方式。
- 为竞品分析、指标复盘和研究综合补充实务方法、模板与完整示例。
- 移除依赖项目容量和管理工具、难以在通用仓库中产生稳定价值的 roadmap 与 sprint skills。
- 删除共享目录与 skill 私有目录中的重复模板，运行时模板由对应 skill 单独维护。

## [2026-06-10]

### Added

- 初始化 Git 仓库并建立 `master` 主分支。
- 补充 `.gitignore`、`.editorconfig`、`.gitattributes`。
- 增加 `CONTRIBUTING.md` 维护规范。
- 增加 `scripts/validate-skills.sh` 本地校验脚本。
- 增加 `.github/workflows/validate.yml` 自动校验流程。
- 为核心 skills 增加 `agents/openai.yaml` 配置。

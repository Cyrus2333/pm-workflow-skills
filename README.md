# PM Workflow Skills

面向 Codex 的通用产品需求工作流 skills。内容以中文编写，skill 名称使用简短的 `pm-对象/交付物-动作` 结构，并与 Codex 展示名保持完全一致。

目标：

- 用统一框架完成需求定义、PRD、证据增强和更新说明
- 让正式 PRD 承接已确认的产品决策，并支持研发实现、测试验收和上线验证
- 保留真正需要专业方法、模板和质量门的能力，移除仅能输出泛化清单的 skills
- 将项目事实留在各项目仓库，将可复用工作方法沉淀为 skills

## 目录

1. Skills 与框架结构
2. 如何选择
3. 需求定义与 PRD 的边界
4. 产品方案六问与 PRD 质量要求
5. 范围取舍与命名规范
6. 仓库结构、维护校验与持续迭代

## Skills

### 需求定义与交付

| Skill | 用途 |
|---|---|
| `pm-requirement-define` | 将模糊想法或零散提需推进为可写 PRD 的产品需求定义 |
| `pm-prd-write` | 输出支持评审、实现、验收和效果验证的完整 PRD |

### 证据增强

| Skill | 用途 |
|---|---|
| `pm-research-synthesize` | 将多源研究材料综合为可追溯的产品洞察 |
| `pm-competitor-analyze` | 围绕具体决策问题完成证据化竞品分析 |
| `pm-metrics-review` | 复盘目标、上线效果或异常并形成产品行动 |

### 更新沟通

| Skill | 用途 |
|---|---|
| `pm-update-write` | 编写更新说明、变更通知或结构化更新日志 |

## 框架结构

这不是要求每个需求依次跑完所有 skills 的线性流水线，而是“一条决策主线 + 按需证据增强 + 一条交付主线 + 上线反馈环”：

- `pm-requirement-define` 是产品决策唯一入口，统一确认问题、目标、方向和一级范围。
- 三个证据类 skills 只补充各自证据，不各自生成一份互相竞争的产品方案。
- `pm-prd-write` 承接已确认决策并形成 build-ready 规格，不回头重做方向判断。
- `pm-update-write` 只传播已确认变化，不创造新的产品结论。
- `pm-metrics-review` 上线后形成反馈环；需要调整问题或方向时回到 `pm-requirement-define`。

## 如何选择

```text
模糊想法、用户问题或零散提需
  → pm-requirement-define
      ├─ 需要用户证据 → pm-research-synthesize
      ├─ 需要外部参考 → pm-competitor-analyze
      ├─ 需要数据判断 → pm-metrics-review
      └─ ready → pm-prd-write

需求定义、PRD 或版本结论已经确认
  → pm-update-write

方案上线后需要判断效果
  → pm-metrics-review
      └─ 需要重新定义问题或方案 → pm-requirement-define
```

`pm-requirement-define` 会根据输入成熟度自动调整：模糊问题先探索方向，具体诉求先还原问题并补边界，已有方案则重点检查取舍与完整性。

三个证据类 skills 是可独立使用的“证据增强层”，不是每次需求定义都必须执行的固定前置流程：

| 证据缺口 | 选择的 skill | 典型输入 | 回到需求定义时交付什么 |
|---|---|---|---|
| 不清楚用户真实问题、差异和根因 | `pm-research-synthesize` | 访谈、工单、问卷开放题、观察记录 | 可追溯洞察、主题、反例和机会 |
| 不清楚外部解法、行业惯例和差异化空间 | `pm-competitor-analyze` | 竞品页面、操作记录、公开资料 | 基于统一任务的差异、机制和适用条件 |
| 不清楚问题规模、效果变化或异常原因 | `pm-metrics-review` | 指标、漏斗、分群、实验或日志 | 数据事实、证据等级、判断条件和行动建议 |

它们可以在 `pm-requirement-define` 之前独立运行，也可以在定义过程中按证据缺口调用。不要默认三个全跑；最终的问题、目标、方向和一级范围仍由 `pm-requirement-define` 统一决策。

## 需求定义与 PRD 的边界

| Skill | 核心职责 | 交付深度 |
|---|---|---|
| `pm-requirement-define` | 做产品决策：为什么做、改变什么、选择什么方向、一级范围到哪里；如已知则交接主要入口、主任务和关键路径 | 决策简报，不展开页面规格和研发矩阵 |
| `pm-prd-write` | 展开交付规格：具体流程、功能、状态、权限、异常、联动、上线和验收；按需补充动线和页面信息结构 | Build-ready PRD，不重新做方案探索 |

PRD 为了自包含会摘要背景、目标、已确认方向和选择依据，但这些内容必须来自已确认需求定义或等价决策输入；上游没有方案比较记录时，PRD 也不补做比较。若详细设计发现必须改变目标、方向或一级范围，应返回 `pm-requirement-define`，而不是在 PRD 中悄悄改写。

## 产品方案六问

核心 skills 共用同一条逻辑主线：

1. 基于现状：事实和证据是什么
2. 预期目标：希望发生什么变化
3. 业务方向：有哪些解法，为什么选择当前方向
4. 实现路径：方案通过哪些阶段、角色和动作落地；涉及体验时补充页面路径和信息组织
5. 判断标准：什么结果说明方案有效
6. 验证指标：如何、何时、按什么口径观察变化

详细说明见 [产品方案六问](./shared-references/产品方案六问.md)。

## PRD 质量要求

`pm-prd-write` 默认输出标准版，并区分两层内容：

- 决策记录层：摘要并追溯已确认的背景、问题、目标、方向和取舍
- 体验与研发交付层：按需展开产品动线、页面信息结构，以及功能、状态、权限、异常、联动、兼容、上线、验收和指标口径

标准 PRD 使用 9 个主章节（含第 0 章），把背景、目标、方向和决策记录合并为“决策依据”，把联动、依赖、兼容和上线合并为“影响与发布”，减少重复跳转。轻量需求可以继续合并；多角色、规则变化、跨系统、历史迁移或灰度发布需求应补齐对应矩阵，而不是增加平级章节。

PRD 使用稳定 ID 建立追溯链：`目标 → 场景 → 功能需求 → 原型/设计 → 规则 → 验收 → 指标`；涉及页面或流程时，可按需增加动线、页面和信息结构 ID。原型负责视觉和交互表达，PRD 负责页面逻辑结构、业务规则和验收；两者冲突时必须记录待决策项，不能默认以任一方静默覆盖。

## 范围取舍

本仓库不再保留通用的 roadmap 和 sprint skills。

- 路线图更新依赖真实战略目标、资源投入、组织承诺和管理节奏
- Sprint 规划依赖团队容量、任务准备状态、依赖关系和项目管理系统
- 缺少这些项目事实和工具集成时，通用 skill 很难产生稳定可靠的业务价值

这类能力更适合沉淀在具体项目的协作规则或与 Linear、Jira 等工具集成的专用 skill 中。

## 命名规范

- 统一使用 `pm-对象/交付物-动作`，例如 `pm-prd-write`、`pm-requirement-define`
- `pm-` 表示产品管理命名空间；对象放在动作前，便于按交付物识别
- 保持简短，不增加语言后缀 `-zh`
- 目录名、front matter `name`、一级标题和 Codex `display_name` 必须完全一致
- `default_prompt` 必须显式包含 `$skill-name`
- 中文用途说明放在 `description` 和 `short_description` 中

## 仓库结构

```text
pm-workflow-skills/
├── ITERATION_GUIDE.md       # 真实使用反馈与协作迭代方法
├── skills/                  # 可安装 skills 及其运行时模板和示例
├── commands/                # 快捷入口
├── shared-references/       # 跨 skill 的产品框架
└── upstream-mapping/        # 与 upstream 的映射和取舍
```

## 项目上下文原则

- 进入项目后优先读取 `AGENTS.md`、根 `README.md` 和项目文档索引
- 项目规则、页面能力、数据口径和实现事实以项目仓库为准
- 区分已验证事实、用户陈述、推断和假设
- 关键策略未决时不伪装成实现细节

## 维护与校验

```bash
bash scripts/validate-skills.sh
```

校验包括目录与名称一致性、Codex 展示名、默认提示词和基础结构。

## 持续迭代

真实使用中发现触发错误、职责重叠、输出缺失、模板冗余或人工返工时，按[使用反馈与迭代指南](./ITERATION_GUIDE.md)记录案例并判断应该修改 front matter、skill 流程、模板、共享框架还是具体项目文档。

不要按单个案例不断堆规则。阻塞问题立即修复；非阻塞问题优先累计 3 至 5 个案例后归类，修改后至少验证目标案例、相邻案例和不应触发的反向案例。

## 参考来源

- Upstream：`anthropics/knowledge-work-plugins/product-management`
- 映射说明：[anthropic-product-management-mapping.md](./upstream-mapping/anthropic-product-management-mapping.md)

# PM Workflow Skills

面向 Codex 的通用产品需求管理工作流技能仓库。

目标：

- 让 Codex 在任意项目中，先完成产品澄清与方案输出，再进入实现
- 提供一套中文化、可复用、可持续迭代的 PM 工作流技能
- 将“项目事实”留在各项目自己的文档中，将“需求工作流”沉淀为全局能力

## 当前结构

```text
pm-workflow-skills/
├── skills/                  # 可安装的 PM skills
├── commands/                # 快捷命令入口
├── shared-references/       # 共享模板与写作规范
└── upstream-mapping/        # 与 upstream 能力的映射说明
```

## Skills 列表

### 第一阶段核心链路

- `pm-brainstorm-zh`
- `pm-requirement-intake-zh`
- `pm-write-spec-zh`
- `pm-stakeholder-update-zh`

### 第二阶段补齐能力

- `pm-roadmap-update-zh`
- `pm-sprint-planning-zh`
- `pm-research-synthesis-zh`
- `pm-competitive-brief-zh`
- `pm-metrics-review-zh`

## 设计原则

- 全局 skill 负责流程，不保存具体项目事实
- 进入项目后，优先读取 `AGENTS.md`、根 `README.md`、项目文档索引
- 项目规则、页面能力、业务口径仍以项目仓库 `docs/` 为主源
- 中高风险需求默认先走 `brainstorm -> intake -> spec -> confirm -> build`

## 建议接入方式

在具体项目里补一份“需求工作流入口”文档，并在项目协作规则里明确：

- 页面结构改动
- 状态流转改动
- 权限、审核、消息联动改动
- 后台新增能力
- 跨模块联动改动

这类需求默认先跑 PM workflow，再进入编码。

## 参考来源

- Upstream: `anthropics/knowledge-work-plugins/product-management`
- 映射说明见 [upstream-mapping/anthropic-product-management-mapping.md](./upstream-mapping/anthropic-product-management-mapping.md)

## 仓库基础设施

当前仓库已补齐以下基础设施：

- `CONTRIBUTING.md`：约束新增 skill、模板和 agent 配置的方式
- `CHANGELOG.md`：记录结构性变更
- `.editorconfig` / `.gitattributes`：统一换行和文本格式
- `scripts/validate-skills.sh`：本地最小结构校验
- `.github/workflows/validate.yml`：GitHub Actions 自动校验

## 本地维护

新增或修改 skill 后，建议本地先执行：

```bash
bash scripts/validate-skills.sh
```

新增 skill 时，至少保证：

- `skills/<skill-name>/SKILL.md` 存在
- `SKILL.md` front matter 中的 `name` 与目录名一致
- 如果存在 `agents/`，则包含 `agents/openai.yaml`
- 通用模板优先放到 `shared-references/`，避免重复拷贝

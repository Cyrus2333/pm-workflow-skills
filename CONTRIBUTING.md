# Contributing

这个仓库存放的是可复用的产品需求管理 workflow skills，不存放具体项目事实。

## 贡献范围

适合进入本仓库的内容：

- 可跨项目复用的 PM workflow skill
- 通用模板、写作规范、同步模板
- 与上游能力的映射说明
- skill 的 agent 展示与默认调用配置

不适合进入本仓库的内容：

- 某个业务线的特定规则
- 某个项目的页面细节、字段定义、实现约束
- 只服务单一项目的一次性需求文档

这类内容应保留在各自项目仓库中。

## 目录约定

```text
skills/<skill-name>/
├── SKILL.md
├── agents/openai.yaml
└── references/                 # 可选

commands/
shared-references/
upstream-mapping/
```

约定：

- skill 名称使用 `pm-对象/交付物-动作` kebab-case，例如 `pm-prd-write`、`pm-tapd-deliver`
- 保留统一的 `pm-` 命名空间，对象放在动作前
- 保持简短，不增加语言后缀
- skill 目录名、front matter `name`、一级标题和 `agents/openai.yaml` 的 `display_name` 必须完全一致
- 每个 skill 必须有 `SKILL.md`
- 每个 skill 必须有 `agents/openai.yaml`，且 `default_prompt` 显式包含 `$skill-name`
- 运行时模板放在拥有它的 skill `references/` 中，避免维护两份
- `shared-references/` 只保存跨 skill 的设计框架，不复制运行时模板；产品交付质量框架、页面内容契约、UX 原型等跨需求定义 / 分级 / PRD / HTML 的共同口径应优先沉淀在这里

## 编写要求

- front matter `description` 必须写清用途、触发场景和不适用边界
- body 必须写清工作边界、工作流程、默认输出和完成标准
- 避免把策略问题伪装成实现细节
- 默认使用中文，文件命名与正文风格保持一致
- 新增模板时先确定唯一所有者，避免重复副本失控
- 修改 `pm-requirement-define` 的深度质询触发规则时，必须同步检查[深度质询协议](./skills/pm-requirement-define/references/深度质询协议.md)、[触发回归案例](./skills/pm-requirement-define/references/深度质询触发案例.md)、README、WORKFLOW_GUIDE 和迭代指南，不能只改一条 prompt。
- 深度质询相关改动必须同时验证“不应质询”“应先补证据”“应单问题试探”和“应深度质询”四类案例，避免只提高召回率而造成普遍误触发。
- 需求定义、分级、PRD、更新和复盘之间的交接契约变更，必须同步检查上游 / 下游文档是否一致，避免只改单个 skill。
- 新增或修改阶段产物规则时，必须说明“生成完成”和“质量通过”的区别，并确认是否需要同步 `pm-quality-audit` 与《产品交付质量框架》。
- 页面体验交付口径变更时，至少检查 `shared-references/页面内容契约与UX原型.md`、`pm-requirement-define`、`pm-requirement-grade`、`pm-prd-write`、`pm-prd-html`、PRD / HTML 模板和案例，不得只修改原型生成 skill。
- 若涉及 UX 原型或静态交付，还必须检查 `README.md`、`WORKFLOW_GUIDE.md`、`ITERATION_GUIDE.md`、`CHANGELOG.md`、`PROGRESS.md`、相关 `agents/openai.yaml`、命令入口、分级模板 / 路由说明，以及 `scripts/validate-html-prototypes.py` 和 CI；至少验证 `prototypeReadiness → HTML 静态结构 → 视觉 / 无脚本验收` 三道门禁口径一致。

## 提交流程

提交前至少执行一次：

```bash
bash scripts/validate-skills.sh
python3 scripts/validate-docs.py
python3 scripts/validate-html-prototypes.py
```

建议在 PR 或提交说明中写清楚：

- 新增了什么 skill / 模板 / 规则
- 解决什么使用场景
- 是否引入了新的共享模板或 agent 配置
- 是否同步更新了 `README.md`、`WORKFLOW_GUIDE.md`、相关交接说明和回归案例

真实使用反馈的记录、归因和回归验证方式见 [使用反馈与迭代指南](./ITERATION_GUIDE.md)。

## 校验范围

当前脚本会检查：

- `skills/` 下每个一级目录都存在 `SKILL.md`
- `SKILL.md` 中的 `name` 与目录名一致
- `SKILL.md` 含有 `description` front matter 和一级标题
- 一级标题和 Codex `display_name` 与 skill 名称一致
- `agents/openai.yaml` 存在，且默认提示显式引用对应 skill

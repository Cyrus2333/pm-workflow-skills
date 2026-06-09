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
├── agents/openai.yaml          # 可选
└── references/                 # 可选

commands/
shared-references/
upstream-mapping/
```

约定：

- skill 目录名使用 kebab-case，并与 `SKILL.md` front matter 里的 `name` 保持一致
- 每个 skill 必须有 `SKILL.md`
- `agents/openai.yaml` 用于展示名、简介和默认提示词；没有明确需要时可以不加
- 可复用模板优先沉淀到 `shared-references/`，skill 私有参考材料才放各自 `references/`

## 编写要求

- 优先写清楚“何时使用”“读取哪些上下文”“如何输出”
- 避免把策略问题伪装成实现细节
- 默认使用中文，文件命名与正文风格保持一致
- 新增模板时，优先判断是否能复用已有共享模板，避免重复副本失控

## 提交流程

提交前至少执行一次：

```bash
bash scripts/validate-skills.sh
```

建议在 PR 或提交说明中写清楚：

- 新增了什么 skill / 模板 / 规则
- 解决什么使用场景
- 是否引入了新的共享模板或 agent 配置

## 校验范围

当前脚本会检查：

- `skills/` 下每个一级目录都存在 `SKILL.md`
- `SKILL.md` 中的 `name` 与目录名一致
- `SKILL.md` 含有 `description` front matter 和一级标题
- 存在 `agents/` 时，必须包含 `openai.yaml`

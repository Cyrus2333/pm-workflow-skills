# Changelog

本仓库的重要结构性变更记录在这里。

## [Unreleased]

### Changed

- 统一全部 skill 为简短的 `pm-对象/交付物-动作` 名称，并使目录、front matter、一级标题和 Codex 展示名完全一致。
- 合并产品想法探索和需求澄清为统一入口 `pm-requirement-define`。
- 明确 `pm-requirement-define` 负责产品决策，`pm-prd-write` 负责研发交付规格；允许信息摘要重复，不允许重新执行方向决策。
- 强化 `pm-prd-write` 的 PRD/spec 边界、内部 MVP 评审简版、单页多信息区表达和研发 spec 交接清单。
- 新增 `PRD示例-异步合唱内部MVP.md`，并同步更新既有 PRD 示例的 spec 交接章节。
- 强化标准版 PRD 的 P0 功能详写要求，避免功能需求明细退化成一句话需求。
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

# PROGRESS

- 目标：在保持现有 6-skill 产品决策与交付闭环的前提下，吸收外部 skills 中有价值的研究执行、协作输出和风险审查做法。
- 基线：`master@c361a90`；工作区初始干净；`bash scripts/validate-skills.sh` 通过 6 个 skill。
- 本轮范围：在不新增主 skill、不恢复 roadmap / sprint skill、不改变 PRD/spec 边界的前提下，为 `pm-requirement-define` 增加可选深度质询模式，并完善协作方 / AI 的使用说明。

## 已完成

- `pm-competitor-analyze` 支持快速分析、深度分析和单品机制拆解。
- 新增 `深度采集指南.md`，规定按需使用 `raw/ → notes/ → merged.md` 的分层研究底稿、来源回溯、缺口记录和停止条件。
- 竞品模板增加分析模式、深度、机制问题、研究底稿和可视化说明字段。
- `pm-requirement-define` 增加成本随规模变化、第三方失败 / 降级、自动化 / AI 责任和 10 倍规模适用性扫描。
- `pm-prd-write` 增加跨章节一致性审查规则和管理者、产品 / 设计 / 测试、研发、运营派生视图规则。
- PRD 模板和两个示例加入一致性审查记录；示例保留待确认和待验证项，不把实现假设写成已确认规则。
- README、CHANGELOG 和 Codex agent 元数据已同步更新。
- 深度质询模式已增加：缺口分类、硬 / 软触发、单问题试探、用户确认门、决策记录、停止条件和禁止事项。
- 新增深度质询协议与 12 个触发回归案例，README、命令入口、产品方案六问和迭代指南已说明如何正确使用和校准。

## 验证记录

- `bash scripts/validate-skills.sh`：通过，6 个 skill。
- Markdown 表格列数检查：通过，扫描 30 个 Markdown 文件。
- `git diff --check`：通过。
- Markdown 本地链接检查：通过。
- 深度质询触发回归：通过；12 个预置案例按 `no-grill / probe / deep-grill / route-evidence` 计数和规则完整性检查通过。
- Markdown 表格检查：通过。
- 最终差异审查：通过；变更仅涉及需求定义 skill、相关参考资源、协作入口和仓库说明。
- Git 提交：`73ee042 Add optional product decision grilling mode`。
- 远程推送：`origin/master` 已更新并与本地 `HEAD` 一致。
- 本地同步：`/Users/huangjingye/.codex/skills` 下 6 个 skill 目录与仓库源目录递归比对一致。

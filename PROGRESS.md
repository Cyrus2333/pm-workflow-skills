# PROGRESS

- 目标：在保持现有 6-skill 产品决策与交付闭环的前提下，吸收外部 skills 中有价值的研究执行、协作输出和风险审查做法。
- 基线：`master@52297be`；工作区初始干净；`bash scripts/validate-skills.sh` 通过 6 个 skill。
- 本轮范围：竞品深度采集与单品机制拆解、需求定义的规模 / 降级 / 责任风险、PRD 一致性审查与受众派生视图；不新增主 skill，不恢复 roadmap / sprint skill，不改变 PRD/spec 边界。

## 已完成

- `pm-competitor-analyze` 支持快速分析、深度分析和单品机制拆解。
- 新增 `深度采集指南.md`，规定按需使用 `raw/ → notes/ → merged.md` 的分层研究底稿、来源回溯、缺口记录和停止条件。
- 竞品模板增加分析模式、深度、机制问题、研究底稿和可视化说明字段。
- `pm-requirement-define` 增加成本随规模变化、第三方失败 / 降级、自动化 / AI 责任和 10 倍规模适用性扫描。
- `pm-prd-write` 增加跨章节一致性审查规则和管理者、产品 / 设计 / 测试、研发、运营派生视图规则。
- PRD 模板和两个示例加入一致性审查记录；示例保留待确认和待验证项，不把实现假设写成已确认规则。
- README、CHANGELOG 和 Codex agent 元数据已同步更新。

## 验证记录

- `bash scripts/validate-skills.sh`：通过，6 个 skill。
- Markdown 表格列数检查：通过，扫描 30 个 Markdown 文件。
- `git diff --check`：通过。
- 最终差异审查：通过；变更仅涉及本轮目标 skills、参考资料、agent 元数据和仓库说明。

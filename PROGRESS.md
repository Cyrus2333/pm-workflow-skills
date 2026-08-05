# PROGRESS

- 目标：完成整套 PM Workflow Skills 的收尾审计与维护，统一 skill 质量门、上下游交接、协作方阅读路径、引用资源和仓库校验。
- 基线：`master@c841325`；工作区初始干净；已有 6 个 skill 结构校验通过。
- 本轮判断：`pm-requirement-define` 与 `pm-prd-write` 的核心方法和交付边界已经成熟；其他 4 个 skills 不是简单“缺内容”，而是需要补齐交接契约、入口说明和维护一致性。`pm-update-write` 保持轻量是有意设计。

## 本轮完成

- 新增仓库级 `WORKFLOW_GUIDE.md`，统一说明任务选择、工作流总图、交接契约、执行模式、协作方阅读顺序、完备度评估、资源索引和 AI 维护规则。
- 为 `pm-requirement-define` 补充阻塞决策负责人 / 最晚时间，并保持深度质询作为可选模式。
- 为 `pm-prd-write` 增加产品、设计、研发、测试、运营和管理者的阅读与交接说明。
- 为研究综合、竞品分析、指标复盘补充明确的需求定义交接契约。
- 为 `pm-update-write` 补充输入检查和与其他 skills 的关系，明确它只传播已确认结论。
- 更新 README、CONTRIBUTING、上游映射、共享产品方案六问和迭代指南。
- 新增 `scripts/validate-docs.py`，校验本地 Markdown 链接、表格、skill 必备章节、资源引用和工作流文档；CI 同步执行文档校验。
- 增强 `scripts/validate-skills.sh`，校验默认输出、完成标准、agent 展示字段和默认提示词。

## 验证记录

- `bash scripts/validate-skills.sh`：通过，6 个 skill。
- `python3 scripts/validate-docs.py`：通过，33 个 Markdown 文件、链接、表格和工作流约定。
- `git diff --check`：通过。
- 深度质询触发回归：12 个预置案例仍保持分类完整。
- 最终审查与验证已完成；本轮提交、远程推送和本地 Codex skills 同步作为本次收尾动作执行。

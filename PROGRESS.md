# PROGRESS

- 目标：完成整套 PM Workflow Skills 的收尾审计与维护，尤其把后续单点加入的 `pm-requirement-grade` 串回完整工作流，统一仓库级引导、上下游交接和维护规范。
- 当前工作流：证据补齐（按需）→ `pm-requirement-define` → `pm-requirement-grade` → L0/L1/L2/L3/H 对应交付 → `pm-prd-write` / `pm-update-write` / `pm-metrics-review` 闭环。
- 本轮判断：原有 README 与 WORKFLOW_GUIDE 已能提到分级，但对“何时用、怎么串、上下游交接契约、理想协作实践”的说明不足；`pm-requirement-define` 和 `pm-prd-write` 中也仍有少量“直接进 PRD”的旧口径，需要统一为先分级再交付。

## 本轮完成

- 重写 `README.md`，从仓库入口层面说明完整主线、7 个 skills 的职责、分级门禁和 XQD 兼容规则。
- 重写 `WORKFLOW_GUIDE.md`，补齐总体流程图、skill 职责地图、输入成熟度判断、C1-C5 上下游交接契约、L1/L2/L3/H 理想实践和统一规范。
- 更新 `pm-requirement-define`，将输出定位从“可写 PRD”调整为“可进入需求分级与后续交付路由”，并补充交给 `pm-requirement-grade` 的风险线索契约。
- 更新 `pm-prd-write`，显式接收 `pm-requirement-grade` 的分级结论、AI Coding / 协作 / PRD 门槛、spec / QA / 灰度 / 回滚 / 上线观察要求。
- 更新 `commands/pm-requirement-define.md`、`CONTRIBUTING.md`、`ITERATION_GUIDE.md`、`CHANGELOG.md` 和上游映射，统一“需求定义后先分级”的口径。


## 二次收敛审查

- 结论：核心调整必要；本轮不是新增复杂度，README 从旧版 232 行收敛到 44 行，WORKFLOW_GUIDE 从旧版 277 行收敛到 185 行。
- 已收敛：回退 PR 模板变更；删除 WORKFLOW_GUIDE 中与 PRD / CONTRIBUTING 重复的 ID 追溯和维护检查清单细节，只保留主线、交接契约和等级实践。
- 保留理由：需求分级是新增门禁，必须同步 README、WORKFLOW_GUIDE、`pm-requirement-define`、`pm-prd-write`、命令入口、模板和迭代指南，否则会继续出现“需求定义 ready 后直接写 PRD”的旧口径。


## pm-requirement-grade 边界审查

- 结论：存在单点并入后的边界混淆风险，尤其是 L2 简版、L3 评审清单和上线观察记录容易被误解为 PRD / spec / 测试 / 指标复盘标准。
- 已处理：将 `pm-requirement-grade` 明确收敛为“风险分级 + 交付路由 / 门禁包”，新增下游边界表；所有 grade 私有模板和 references 增加定位说明。
- 保留原则：grade 可以判断“是否需要 PRD/spec/QA/观察”和“门禁重点”，但不能在本 skill 内展开完整 PRD、研发实现、测试用例集或效果因果复盘。

## 验证记录

- `bash scripts/validate-skills.sh`：通过，8 个 skill。
- `python3 scripts/validate-docs.py`：通过，49 个 Markdown 文件、链接、表格和工作流约定。
- `git diff --check`：通过。

## 本轮页面体验工作流升级（2026-08-20）

- 结论：复杂页面需求不能只依赖页面地图、组件骨架和代表性原型；当目标是设计前评估页面效果时，必须增加页面内容契约，维护所有用户可见静态 / 动态 / 条件 / 反馈内容。
- 新增共享参考 `shared-references/页面内容契约与UX原型.md`，统一信息架构、页面内容契约、状态组合矩阵和 UX 原型的职责边界。
- 同步更新需求定义、需求分级、PRD 编写、HTML 编译及仓库级交接 / 迭代文档，形成需求定义 → 分级门槛 → PRD 内容主源 → HTML 内容覆盖的完整链路。
- 已完成：运行仓库校验、提交并推送远程、同步 Codex 本地 skills；下一步用真实页面需求回归内容契约和 HTML 原型覆盖效果。


## 全链路 UX 原型与静态交付同步（2026-08-26）

- 本轮不再把问题视为只修改 `pm-prd-html`：已把 `prototypeTarget`、`prototypeFidelity`、`pageSchema`、`contentContract`、`viewportContract`、`designSystemRefs`、`staticDelivery` 和 `prototypeReadiness` 串入需求分级、PRD、HTML 和质量审计的交接语义。
- 已同步仓库级说明与引导：`README.md`、`WORKFLOW_GUIDE.md`、`ITERATION_GUIDE.md`、`CONTRIBUTING.md`、`CHANGELOG.md`、命令入口、分级路由、L2/L3 模板、项目画像和 HTML agent 默认提示。
- 已将 HTML 原型交付口径统一为：默认 `ux-prototype`，显式 `wireframe` 才输出低保真线框；每个状态的 SVG 静态内嵌在初始 DOM，脚本只做渐进增强，受限预览禁用 JS 后仍可阅读。
- 已增加静态结构检查脚本并接入本地 / CI 校验；当前已完成 XML / 脚本 / 静态 DOM 检查，以及 Headless Chrome 对两个示例在 320 / 375 / 390 / 430 宽度下的截图渲染。活动详情示例的 390×844 正常版与移除脚本版截图字节一致，证明静态初始 DOM 可在无脚本浏览器路径中生成同样的首屏图像。
- 仍需人工完成项：当前对话表面无法直接审看截图像素，因此不能把“截图生成成功”表述为完整的视觉设计验收；后续在可查看截图的浏览器 / 设计评审环境中，应复核信息密度、裁切、长页滚动和每个状态的视觉层级。

## TAPD 交付接入（2026-09-22）

- 结论：#5 先以独立 TAPD 写入适配器合入；随后收回到统一 `pm-*` 命名空间 `pm-tapd-deliver`，并作为可选出口接入主工作流，而不是产品决策 / PRD 必经阶段。
- 已同步 README、WORKFLOW_GUIDE、需求定义 / 分级 / PRD 下游提示、CHANGELOG 和 CI unittest。
- 传输层改为仓库内官方 OpenAPI 窄适配器 `scripts/pm_tapd.py`：模型不直接 curl，不绑定 MCP 或第三方 CLI。覆盖 Story/Task 预检、查重、dry-run、写入、Readback、Story workflow 证明、真实 mention 和标准附件；Task workflow 在官方拒绝时诚实回退，附件 upload 按社区合同实现，失败不伪造。
- 保留安全协议：实时字段解析、查重、预览确认、顺序写入、Readback、Necessity Check；不引入组织专用默认值。
- #4 已关闭，避免并行维护两套 TAPD skill。

## TAPD Skill 同步与分类标签校验（2026-09-24）

- 已将本机最新 `pm-tapd-deliver` 同步回仓库，保持适配器合同、交付协议、字段解析、预览模板和测试用例一致。
- 修复 Story Readback 投影遗漏 `category_id` 的问题；Story 创建 / 更新现在必须根据实时 schema 唯一解析分类和标签，禁止缺失、歧义、非法值或“未分类”兜底。
- 新增 6 个 Skill 内离线回归用例，并更新仓库级 TAPD 测试夹具，覆盖 dry-run、正式写入与 Readback 断言。
- 修正首次同步时整文件覆盖造成的协议缺失，恢复历史补录、动作包 / 断点续作、差异分级、日期证据和附件映射规则，并与分类 / 标签更新合并。

# TAPD Deliver V1 测试用例

在专用 sandbox workspace 或 mock 中验证，禁止用生产对象试错。所有真实 TAPD 写操作须另行授权。

## Workspace 与 Story

1. 用户默认 workspace 命中；用户临时 workspace 覆盖；默认找不到；名称歧义。
2. Story 正常创建、完全重复、相似候选、快速占位、缺等级。
3. planned 成功、planned 缺必填事实、create 后 Readback 不一致。

## Product Task

1. 正常创建、同 Story 完全同标题阻止、owner 缺失。
2. 同 Story 标题近似且 Description 明确覆盖同一范围／阶段／交付物时阻止新建。
3. 同 Story 同类别但不同具体工作时仅列为相关候选，不阻止。
4. 已有泛化标题“产品方案设计”而拟建明确专项 Task 时，用户确认独立工作后允许创建。
5. 用户明确选择复用时不新建；用户明确选择独立新增时继续生成可确认 Preview。
6. 类别高置信推荐、低置信选择、类别字段不存在。
7. open 到 progressing；无附件交付要求时 done 成功；有必须附件时 done 前已上传并回读；done 缺投入人天；没有可靠投入字段。

## 附件与 Description

1. capability 不可用时，无附件交付要求的 Task 仍可 done；有必须附件的 Task 停止 done。单附件、多附件、同名附件、上传中途失败、附件 Readback 不一致。
2. Description 有人工内容、有受管片段、预览后字段配置变化。
3. 本地文件不存在、空文件、目录误传、root 外文件、symlink 越界、仅有文件名无可靠路径。
4. 只有交付计划、无真实文件时，Description 使用“计划产出物”。
5. 明确文件路径且本地校验通过、尚未上传时，只标记“本地文件已验证”，不得声称 TAPD 已上传。
6. 上传并通过 Attachment Readback 后，才标记“已上传产出物”。
7. Description 写有文件名但本地无文件时，不得视为附件存在。
8. 用户要求上传交付物时，真实文件存在且附件能力可用则必须走上传与回读；不得只更新 Description 替代附件上传。
9. 不按固定工具名判断能力：通用附件读取工具若以 `type=task` 实测成功，Task attachment list 应判为可用，即使 schema 文案未列出 Task。
10. list、upload、Readback 分别检测；缺少 upload 时不得把已验证 list 误报为整体不可用。
11. 本机配置声明附件 MCP 但当前会话未暴露工具时，标记会话未加载／未暴露；不改配置，要求新会话重新检测。

## 安全与确认

1. 用户未确认不写；仅确认 Story 不创建 Task；一次确认的 Story + Task 依次执行。
2. 中途 Readback 失败后剩余动作不执行；不自动删除、覆盖或重试写入。

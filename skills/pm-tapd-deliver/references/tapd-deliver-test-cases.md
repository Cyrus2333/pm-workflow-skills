# TAPD Deliver V1 测试用例

在专用 sandbox workspace 或 mock 中验证，禁止用生产对象试错。所有真实 TAPD 写操作须另行授权。

## Workspace 与 Story

1. 用户默认 workspace 命中；用户临时 workspace 覆盖；默认找不到；名称歧义。
2. Story 正常创建、完全重复、相似候选、快速占位、缺等级。
3. planned 成功、planned 缺必填事实、create 后 Readback 不一致。

## Product Task

1. 正常创建、重复、owner 缺失。
2. 类别高置信推荐、低置信选择、类别字段不存在。
3. open 到 progressing；无附件交付要求时 done 成功；有必须附件时 done 前已上传并回读；done 缺投入人天；没有可靠投入字段。

## 附件与 Description

1. capability 不可用时，无附件交付要求的 Task 仍可 done；有必须附件的 Task 停止 done。单附件、多附件、同名附件、上传中途失败、附件 Readback 不一致。
2. Description 有人工内容、有受管片段、预览后字段配置变化。
3. 本地文件不存在、空文件、目录误传、root 外文件、symlink 越界、仅有文件名无可靠路径。

## 安全与确认

1. 用户未确认不写；仅确认 Story 不创建 Task；一次确认的 Story + Task 依次执行。
2. 中途 Readback 失败后剩余动作不执行；不自动删除、覆盖或重试写入。

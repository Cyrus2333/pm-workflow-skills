# TAPD 适配器合同（V2）

模型不得直接调用 TAPD OpenAPI、MCP 或第三方 CLI。唯一入口是本 Skill 目录下的脚本：

```bash
python3 scripts/pm_tapd.py <command>
```

在仓库根目录调试时使用 `python3 skills/pm-tapd-deliver/scripts/pm_tapd.py <command>`。

输出一律为单行 JSON。成功 `ok: true` 且退出码 0；业务失败退出码 1；用法/配置 2；缺凭据 3；网络或未知信封 4。不得把 token、密码、Authorization 打印到 stdout/stderr；`testauth` 若返回 `api_password` 必须脱敏。

## 凭据

官方 TAPD OpenAPI 使用 HTTP Basic。优先级：

1. `TAPD_API_USER` + `TAPD_API_PASSWORD`
2. `TAPD_ACCESS_TOKEN`（Bearer，仅当令牌类型支持时）
3. 本机 `~/.tapd.json` 的同名字段：`api_user` / `api_password` / `access_token`

可选 `TAPD_API_BASE_URL`（默认 `https://api.tapd.cn`）。仓库不保存凭据。

## 命令

| 命令 | 作用 | 是否写 TAPD |
|---|---|---|
| `capabilities` | 返回 V2 能力开关 | 否 |
| `preflight` | 只读调用 `/quickstart/testauth` | 否 |
| `workspace --id <id> [--name <name>]` | 实时确认 workspace | 否 |
| `fields --workspace-id <id> --entity stories/tasks` | 拉字段 schema | 否 |
| `find --entity ... --workspace-id ... --name ...` | 分页查重 | 否 |
| `get --entity ... --workspace-id ... --id ...` | 读一条 | 否 |
| `write --entity ... --payload '<json>' --dry-run` | 只展开将 POST 的 form | 否 |
| `write --entity ... --payload '<json>'` | 创建或更新 | 是 |
| `readback --entity ... --workspace-id ... --id ... --expect '<json>'` | GET 后按字段断言 | 否 |
| `workflow --entity ... --workspace-id ... [--workitem-type-id ...] --from ... --to ...` | 写入前证明状态流转 | 否 |
| `members --workspace-id ... [--nicks a,b]` | 列出并唯一解析成员 | 否 |
| `comment preview/list/get ...` | 预览或读取评论 | 否 |
| `comment add --dry-run ...` | 只展开将 POST 的评论 | 否 |
| `comment add ...` | 创建原生 mention 评论并回读 | 是 |
| `attachments list/readback ...` | 读取附件 | 否 |
| `attachments upload --dry-run ...` | 本地校验并查重，不 POST | 否 |
| `attachments upload ...` | 上传一个文件并回读 | 是 |

`write` 的 payload 为 JSON 对象。有 `id` 则更新，否则创建。`custom_fields` 会展开成 `custom_field_*` 表单字段。Story / Task Description 原样提交，不做 Markdown 转换。普通写入 POST 使用 `application/x-www-form-urlencoded`；附件上传使用 multipart。

Story workflow 必须带 `--workitem-type-id`。评论 `entry_type` 使用复数 `stories` / `tasks`；附件 `type` 使用单数 `story` / `task`。不要用另一种形态重试作为补偿写入。

## 能力与合同

可用：workspace、Story、Task、字段、查重、dry-run、写入、Readback、workflow、members、mention、attachment list / upload / Readback。

诚实标记：

- `contracts.mention = native_at_who`
- `contracts.attachment_upload = community`
- `contracts.task_workflow = documented_fallback_if_official_rejects`

附件 upload 若被 TAPD 拒绝，适配器返回 `ATTACHMENT_UPLOAD_UNAVAILABLE`，调用方必须停止依赖上传的动作，不能改探测 MCP / CLI，也不能把文件名写入 Description 冒充成功。

## 预览授权

`write`、`comment add`、`attachments upload` 不带 `--dry-run` 前，必须已经向用户展示过同一份预览，并得到明确确认。确认范围变化则重新 dry-run。状态变更还须先有 `workflow` 结果：Story 非法流转直接停止；Task 若 `source=documented_task_status`，预览须写明“非官方 workflow 证明”。

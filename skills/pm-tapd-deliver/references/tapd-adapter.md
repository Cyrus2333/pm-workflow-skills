# TAPD 适配器合同（V1）

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
| `capabilities` | 返回 V1 能力开关 | 否 |
| `preflight` | 只读调用 `/quickstart/testauth` | 否 |
| `workspace --id <id> [--name <name>]` | 实时确认 workspace | 否 |
| `fields --workspace-id <id> --entity stories/tasks` | 拉字段 schema | 否 |
| `find --entity ... --workspace-id ... --name ...` | 分页查重 | 否 |
| `get --entity ... --workspace-id ... --id ...` | 读一条 | 否 |
| `write --entity ... --payload '<json>' --dry-run` | 只展开将 POST 的 form | 否 |
| `write --entity ... --payload '<json>'` | 创建或更新 | 是 |
| `readback --entity ... --workspace-id ... --id ... --expect '<json>'` | GET 后按字段断言 | 否 |

`write` 的 payload 为 JSON 对象。有 `id` 则更新，否则创建。`custom_fields` 会展开成 `custom_field_*` 表单字段。Description 原样提交，不做 Markdown 转换。POST 使用 `application/x-www-form-urlencoded`。

## V1 能力

可用：workspace、Story、Task、字段、查重、dry-run、写入、Readback。

不可用：`attachment`、`mention`、完整 workflow 查询。调用方必须把这三项报告为 `UNAVAILABLE`，不能降级伪造，也不能改去探测 MCP 或 CLI。

## 预览授权

`write` 不带 `--dry-run` 前，必须已经向用户展示过同一份 dry-run `form`，并得到明确确认。确认范围变化则重新 dry-run。

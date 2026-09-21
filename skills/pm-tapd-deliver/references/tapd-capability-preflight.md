# TAPD 能力预检

操作 TAPD 前使用；诊断凭据与只读探测，不把检查写成产品阶段。预检只读，不使用创建/上传/评论测试连接。

唯一入口是 `scripts/pm_tapd.py preflight`。不要扫描 Codex MCP `config.toml`，不要把“配置了 TAPD MCP / 安装了某个 CLI”当成 READY。

凭据缺失输出 `ok: false`，退出码 3。凭据存在后必须实际调用 TAPD `/quickstart/testauth`；HTTP 200 仍要看业务 `status==1`。`testauth` 可能在 `data` 中带回 `api_password`，适配器不得输出该字段。一次成功只读调用只证明当前账号此刻可查询，不证明附件 upload、mention 写入或状态流转可写。

`api_user` 只表示 API 账号，不能自动当作评论作者 nick。

能力以 `pm_tapd.py capabilities` 为准，并按实际命令结果诚实报告：

- Story workflow：官方 `status_map` / `all_transitions` 成功才可宣称已证明
- Task workflow：官方拒绝 `system=task` 时使用文档化状态图，必须标明非 workflow-proven
- 附件 list / Readback：官方；upload：community contract，拒绝则 unavailable
- mention：必须原生节点回读，不能降级

按[外部副作用证据](./platform-evidence.md)逐项报告：configuration_present（凭据是否存在，不输出值）、query_succeeded、write_authorized、write_succeeded、readback_confirmed。本地 dry-run 和 mock 不能代替平台成功。

# TAPD 能力预检

操作 TAPD 前使用；诊断凭据与只读探测，不把检查写成产品阶段。预检只读，不使用创建/上传/评论测试连接。

唯一入口是 `scripts/pm_tapd.py preflight`。不要扫描 Codex MCP `config.toml`，不要把“配置了 TAPD MCP / 安装了某个 CLI”当成 READY。

凭据缺失输出 `ok: false`，退出码 3。凭据存在后必须实际调用 TAPD `/quickstart/testauth`；HTTP 200 仍要看业务 `status==1`。`testauth` 可能在 `data` 中带回 `api_password`，适配器不得输出该字段。一次成功只读调用只证明当前账号此刻可查询，不证明附件、mention、workflow 或写入可用。

V1 能力以 `pm_tapd.py capabilities` 为准。attachment / mention / workflow 为 false 时，不得用 Description 或普通评论冒充，也不再做 MCP 工具发现。

按[外部副作用证据](./platform-evidence.md)逐项报告：configuration_present（凭据是否存在，不输出值）、query_succeeded、write_authorized、write_succeeded、readback_confirmed。本地 dry-run 和 mock 不能代替平台成功。

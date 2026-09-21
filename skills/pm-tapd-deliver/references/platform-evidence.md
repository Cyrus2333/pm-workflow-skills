# TAPD 外部副作用证据
仅在 TAPD 操作验证时读取；不改产品定义、交付表达或事实主源约定。

分别记录，不能从前一步推定后一步：configuration_present、query_succeeded、write_authorized、write_succeeded、readback_confirmed。配置指适配器能读到凭据，不指 MCP `config.toml` 或某个 CLI 已安装；凭据值不得写入证据。配置未能观察时记 unknown。每条证据带当前会话/目标/时间/实际结果定位；mock 单列。适配器调用成功还要解析 TAPD 业务信封 `status==1`，未知 schema 不当成功。

授权绑定完整具体预览中的平台、workspace/文档、动作、字段/内容及资源；不是绑定一个模糊“允许测试”。授权内容变更须更新预览；已覆盖且未变更的授权不重复索要。查重/现状/关键 schema 改变时暂停相应写入。写超时或回读不一致停止，不自动补偿、覆盖或重发。读取本身不需要写入授权。

对每个 TAPD 动作记录 payload（含平台、目标、动作和完整字段）及事件，但必须脱敏 token / password。授权与写入必须对应同一份预览；Readback 记录目标身份和字段断言结果。Mock 与真实运行证据不能混用，本地 contract 测试也不能替代真实适配器调用证据。

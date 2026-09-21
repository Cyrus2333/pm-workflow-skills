# TAPD 能力预检
操作TAPD前使用；诊断配置与会话能力，不把检查写成产品阶段。预检是只读，不使用创建/上传/评论测试连接。

读取当前真实暴露工具的schema和描述，按能力/来源识别，不假定固定server别名。scripts/tapd-preflight.py接收当前发现的工具名数组（--tools-json文件或stdin）；未传表示未发现，[]表示发现完但没有工具。脚本只读取配置路径/启用/过滤信息，不输出env、凭据、URL或启动命令，不启动服务或直接HTTP。
默认检查CODEX_HOME及当前项目祖先配置；其他托管来源用--config显式指定，可靠server别名用--server-name。检查范围没找到配置不代表宿主不存在配置。配置读取失败不等于配置不存在。Python3.11+是本诊断工具依赖。

输出CONFIG_NOT_FOUND_IN_CHECKED_PATHS / CONFIGURED_NOT_EXPOSED / CONFIG_UNVERIFIED / DISCOVERY_REQUIRED / READ_PROBE_REQUIRED等；退出0只表示发现工具可开始探测，不表示查询或写入成功。
发现工具后，选当次schema明确只读的查询，使用可靠workspace或项目列表。传输完成、HTTP200、isError=false均不足：按响应schema核对业务成功；未知envelope保持未验证。空列表可合法，但不证明对象/字段不存在，先核查过滤、分页、实体类型及缓存。
一次成功只读调用仅报告该工具/账号/workspace/时刻的query_succeeded，不用全局TAPD_READY暗示全部能力。schema、workflow、附件、mention、写入各自验证；会话/身份/目标变化后重查相关能力。

按[外部副作用证据](./platform-evidence.md)逐项报告阶段。确认副作用只在完整预览后发生；本地诊断和mock永远不证明平台成功。

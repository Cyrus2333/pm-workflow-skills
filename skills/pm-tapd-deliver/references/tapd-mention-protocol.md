# TAPD 真实 mention 评论

V1 适配器的 `mention` 能力固定为 false。用户明确要求 @ 项目成员时，报告 `MENTION_CAPABILITY_UNAVAILABLE`，停止依赖真实 mention 的动作，并让用户选择“只做 Story / Task”或“本轮全部停止”。

不要调用 MCP 工具，不要使用普通评论、普通文本 `@姓名` 或手工拼接 HTML 节点冒充真实 mention。

后续若官方 OpenAPI 经验证支持：成员唯一 nick 解析、只读预览、创建原生 mention 节点、按 comment ID 独立回读，再打开该能力。那时仍须核验 workspace、对象、作者和每个原生 mention 节点；部分成功或无法验证都不得继续后续写入。

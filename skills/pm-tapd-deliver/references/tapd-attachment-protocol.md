# TAPD 附件协议

V1 适配器的 `attachment` 能力固定为 false。用户要求上传、覆盖或断言 TAPD 附件时，直接报告 `UNAVAILABLE`，并让用户选择“只做 Story / Task”或“本轮全部停止”。

不要扫描 MCP `config.toml`，不要按工具名探测 `tapd_upload`，不要用 Description 里的文件名、本地文件存在或普通评论冒充“已上传”。

V1 无附件能力时：

- 没有必须上传附件的 done 请求，可以继续 Story / Task；
- 用户明确要求上传交付物，或 done 被约定为必须先有附件时，停止依赖附件的动作；
- 不得先创建对象再告知附件不可用。

后续若官方 OpenAPI 经验证支持 Task 附件 list / upload / Readback，再把三项能力分别打开。那时仍只接收用户明确给出的本地文件路径或明确交付清单中的真实文件，上传前运行 `scripts/verify-local-deliverables.py`，同名附件默认停止，串行上传并逐项 Readback。

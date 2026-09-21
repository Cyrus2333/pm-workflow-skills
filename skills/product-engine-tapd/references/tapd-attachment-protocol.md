# TAPD 附件协议

附件是 optional capability。涉及附件的请求在首次预览前按实际行为检测 Task attachment list、upload 和 Readback 能力；工具或 MCP 的名称不是能力合同。对候选读取工具应以 `type=task`、目标 Task ID 的只读调用验证其能否返回 Task 附件，而不因 schema 文案只列出 Story／Bug 就直接判为不可用。

只有同时具备以下能力，Task 附件上传才可执行：可读取目标 Task 附件、可上传指定本地文件到目标 Task、可再次读取并断言 attachment id、filename、type、entry_id、workspace_id。三者须分别报告，不能用“未发现 tapd_upload”或任一固定工具名推断整体 unavailable。

若本机配置仍声明附件 MCP、但当前会话未注册或未暴露其工具，标记为“当前会话未加载／未暴露”，保留已验证的 list 能力并将 upload／完整 Readback 标为不可执行；不修改配置，不假定 schema，提示在新会话重新加载后重新检测。缺失时必须让用户在“仅执行 Story / Task”与“本次全部停止”之间选择；不得先创建再告知附件不可用。

只接收用户明确给出的本地文件路径，或明确上游交付清单中可定位的真实本地文件。禁止扫描 Downloads、Desktop、仓库或相似目录猜测文件，禁止重新生成、伪造 file path 或用同名文件替代。

上传前运行 `scripts/verify-local-deliverables.py`，并调用附件列表工具查重。同名附件默认停止，不覆盖、不重复上传、不推断版本关系。

批量交付在一份完整预览中列出全部文件。确认后严格串行：上传文件 1 → 附件 Readback → 上传文件 2 → Readback。任一失败即停止后续上传和 Description 更新。附件成功要求 id 非空、filename 正确、type 为 task、entry_id 为目标 Task、workspace_id 正确。

公共 Skill 不硬编码交付根目录。根目录优先级为用户本轮指定 > 项目配置 > 用户默认 > 询问。解析路径必须保持在该许可根目录内，且解析后不能经 symlink 越界。

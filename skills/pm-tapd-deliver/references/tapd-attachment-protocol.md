# TAPD 附件协议

附件 list / Readback 使用官方 `GET /attachments`，`type` 为单数 `story` / `task`。标准附件 upload 使用社区合同 `POST /files/upload_attachment`，同样使用单数 `type` 和 `entry_id`；这不是公开文档里的自定义字段上传。不要为了让上传成功而改用复数 type 重试，也不要用 Description 文件名冒充已上传。

涉及附件的请求在首次预览前分别报告：

- list：官方只读，可先对目标对象实测
- upload：命令已实现，但合同是 community；TAPD 拒绝则 `ATTACHMENT_UPLOAD_UNAVAILABLE`
- Readback：上传后必须再 list，断言 id、filename、type、entry_id、workspace_id

Preflight 保持只读，不靠实际上传测连通。三者须分别报告，不能因为 upload 未验证就把已成功的 list 判为整体不可用。

只有 list、upload、Readback 同时可用，才可执行用户明确要求的附件上传。缺失时必须让用户在“仅执行 Story / Task”与“本次全部停止”之间选择；不得先创建再告知附件不可用。

只接收用户明确给出的本地文件路径，或明确上游交付清单中可定位的真实本地文件。禁止扫描 Downloads、Desktop、仓库或相似目录猜测文件，禁止重新生成、伪造 file path 或用同名文件替代。

上传前运行 `scripts/verify-local-deliverables.py`（适配器 upload 也会再跑一次），并 `attachments list` 查重。同名附件默认停止，不覆盖、不重复上传、不推断版本关系。

批量交付在一份完整预览中列出全部文件。确认后严格串行：上传文件 1 → 附件 Readback → 上传文件 2 → Readback。任一失败即停止后续上传和 Description 更新。附件成功要求 id 非空、filename 正确、type 为目标实体单数、entry_id 与 workspace_id 正确。

公共 Skill 不硬编码交付根目录。根目录优先级为用户本轮指定 > 项目配置 > 用户默认 > 询问。解析路径必须保持在该许可根目录内，且解析后不能经 symlink 越界。

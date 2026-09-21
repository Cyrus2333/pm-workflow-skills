# TAPD 真实 mention 评论

用户明确要求 @ 项目成员时，只能使用 `tapd_add_comment_with_mentions` 或具有同等真实 mention 与独立回读合同的已验证工具。普通文本 `@姓名`、普通评论成功、仅有用户名都不能替代真实 mention。工具未在当前会话暴露时报告 `MENTION_CAPABILITY_UNAVAILABLE`；不降级，不使用普通评论工具手工拼接节点。

## 执行流程

1. 只读确认目标 workspace、对象类型和 ID；读取已有评论，识别同轮交付重复，防止重发。
2. 用户姓名先解析为项目成员的唯一 nick。`tapd_resolve_workspace_members` 接受精确 nick 数组；不可把显示名当 nick 猜测。不存在、重复 nick、非项目成员、权限不足或响应格式异常均阻止写入。
3. 使用 `tapd_preview_comment_with_mentions` 生成只读预览，展示 workspace/对象、评论全文、每人的显示名、nick、内部用户 ID（如有）、实际 mention 标识、完整 payload、作者处理方式及验证机制。
4. 用户明确确认该预览后才调用 `tapd_add_comment_with_mentions`。创建前工具重新检查成员及目标；若解析结果或预览内容变化，应重新确认。正文输入是纯文本，工具负责转义及生成原生节点。
5. 创建后按 comment ID 独立 GET 回读，核对 workspace、entry_type、entry_id、作者与正文、每个原生 mention 节点。任何创建响应不确定或回读失败均停止；保留已有 comment ID，不自动重试写入，不删除或补偿创建。
6. 只有全部节点核验通过、状态为 `MENTION_VERIFIED` 才报告评论交付完成。部分成功为 `MENTION_PARTIAL`，普通文本/回读失败/无法验证为 `MENTION_UNVERIFIED`。两者均不可静默降级为普通评论或继续后续写入。

## 已验证合同与限制

当前 TAPD 原生节点为 `<b class="at-who" contenteditable="false" data-userid="{nick}" data-type="user">@{nick}</b>`。`data-userid` 在此协议中使用 nick，不是数字 user_id。nick 和正文必须转义，不允许通过正文注入额外 mention。

公开评论 API 的此节点机制已通过实际评论、独立 API 回读、Web 原生展示及接收人“评论并@了你”通知验证。工具的 `MENTION_VERIFIED` 指全部原生节点持久化验证，不能等同于四人分别已阅读或四份通知回执。`notification_verification` 单独说明通知读取是否可用、取得了谁的证据；可读取时进一步核验，不得访问未授权账号或假设通知送达。

评论作者使用认证身份自然写入；接口必须显式 author 时先可靠确认当前认证身份，不能由 Task 负责人推断。无需 author 的接口不伪造 author。

此流程不授权修改目标 Description、状态、负责人、附件或其他字段。测试对象和测试接收人需明确授权；测试成功也不自动授权正式业务评论。

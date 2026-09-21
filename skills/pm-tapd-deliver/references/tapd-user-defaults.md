# 用户默认配置

公共 Skill 不保存用户、组织、workspace ID、部门、项目列表、owner 或本地业务路径。用户级默认配置应位于公共仓库之外，且不得含密码或 token。

默认文件位置为 `$CODEX_HOME/pm-tapd-deliver.defaults.yaml`；若 `CODEX_HOME` 未设置，则使用用户 Codex 配置根目录。若未来已有更权威的 Codex 用户配置约定，应优先迁移到该约定。 若本地仍有旧文件名 `product-engine-tapd.defaults.yaml`，迁移到本文件名后再使用，Skill 不自动读取旧路径。

最小 schema：

```yaml
version: 1

workspace:
  default_name: <已确认 workspace 名称>
```

可选 workspace ID 只能作为加速缓存，任何正式写入前仍须实时解析并确认有效。用户默认值可被项目配置和本轮用户明确值覆盖。

用户/Workspace策略可包含标题约定、候选类别或计划日期偏好，但不得变成通用事实。配置来源由用户/当前可靠会话提供；只读默认配置不授予写入权限。实时枚举冲突时不套默认。当前用户环境变量只能是身份线索；需要成员身份时实时唯一核实，不能把配置昵称视为API令牌身份已证明。

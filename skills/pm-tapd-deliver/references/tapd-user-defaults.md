# 用户默认配置

公共 Skill 不保存用户、组织、workspace ID、部门、项目列表、owner 或本地业务路径。用户级默认配置应位于公共仓库之外，且不得含密码或 token。

默认文件位置为 `$CODEX_HOME/pm-tapd-deliver.defaults.yaml`；若 `CODEX_HOME` 未设置，则使用用户 Codex 配置根目录。若未来已有更权威的 Codex 用户配置约定，应优先迁移到该约定。

最小 schema：

```yaml
version: 1

workspace:
  default_name: <已确认 workspace 名称>
```

可选 workspace ID 只能作为加速缓存，任何正式写入前仍须实时解析并确认有效。用户默认值可被项目配置和本轮用户明确值覆盖。

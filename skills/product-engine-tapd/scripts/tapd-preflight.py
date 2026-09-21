#!/usr/bin/env python3
"""Read-only local TAPD preflight. READY requires a live MCP call in Codex.

Python 3.11+. No server startup, network calls, configuration writes or secrets.
--tools-json accepts the current session's discovered TAPD tool names as JSON;
use '-' for stdin. This is inventory evidence, never evidence of call success.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tomllib


def inspect(skill, configs, server_names=(), tools=None):
    result = {"state": None, "ready": False, "skill_exists": skill.is_file(),
              "configs": [], "servers": [], "discovered_tools": tools,
              "readonly_call": "not_performed_by_local_script"}
    if not result["skill_exists"]:
        result.update(state="SKILL_MISSING", message="product-engine-tapd Skill 文件不存在。")
        return result
    for path in configs:
        item = {"path": str(path), "exists": path.is_file()}
        result["configs"].append(item)
        if not item["exists"]:
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
            servers = data.get("mcp_servers", {})
            if not isinstance(servers, dict):
                raise ValueError("mcp_servers must be a table")
            for name, cfg in servers.items():
                if "tapd" not in name.lower() and name not in server_names:
                    continue
                if not isinstance(cfg, dict):
                    raise ValueError("MCP server must be a table")
                result["servers"].append({"name": name, "source": str(path),
                    "enabled": cfg.get("enabled", True),
                    "transport_configured": bool(cfg.get("url") or cfg.get("command")),
                    "enabled_tools": cfg.get("enabled_tools"),
                    "disabled_tools": cfg.get("disabled_tools")})
        except (OSError, ValueError) as exc:
            # Never echo TOML lines, URLs, commands, env or authentication values.
            item["error"] = type(exc).__name__
    if tools:
        result.update(state="READ_PROBE_REQUIRED",
                      message="当前会话已发现 TAPD tools；必须真实调用至少一个只读工具后才能判定 READY。")
    elif tools is None:
        result.update(state="DISCOVERY_REQUIRED", message="尚未提供当前会话工具发现结果；不能据此判断工具未暴露。")
    elif any("error" in c for c in result["configs"]):
        result.update(state="CONFIG_UNVERIFIED", message="配置读取或解析失败；不能宣称 TAPD MCP 未配置。")
    elif result["servers"]:
        result.update(state="CONFIGURED_NOT_EXPOSED",
                      message="product-engine-tapd 已加载，但当前 Codex 会话未暴露 TAPD MCP tools。",
                      next_step="检查已列出的 enabled / 工具过滤设置；重启 Codex Desktop 或新开会话后重新执行 preflight。重启不保证 READY。")
    else:
        result.update(state="CONFIG_NOT_FOUND_IN_CHECKED_PATHS",
                      message="product-engine-tapd 已加载，但当前 Codex 会话未暴露 TAPD MCP tools。",
                      next_step="已检查的配置范围中缺失 TAPD MCP 配置；若另有托管配置或 server 使用别名，应补充该配置路径或别名后重查。")
    return result


def default_configs(project):
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    paths = [home / "config.toml"]
    # Project layers are candidates only; presence does not prove trust/activation.
    for parent in reversed((project, *project.parents)):
        paths.append(parent / ".codex" / "config.toml")
    return list(dict.fromkeys(paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", type=Path, default=Path(__file__).resolve().parents[1] / "SKILL.md")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, action="append", help="Explicit config paths; replaces default scan; repeatable")
    parser.add_argument("--server-name", action="append", default=[], help="Confirmed TAPD server alias; repeatable")
    parser.add_argument("--tools-json", help="JSON array of discovered TAPD tool names; '-' reads stdin; [] means discovery completed with no TAPD tools")
    args = parser.parse_args()
    tools = None
    if args.tools_json:
        try:
            raw = sys.stdin.read() if args.tools_json == "-" else Path(args.tools_json).read_text(encoding="utf-8-sig")
            tools = json.loads(raw)
            if not isinstance(tools, list) or any(not isinstance(t, str) or not t for t in tools):
                raise ValueError()
        except (OSError, ValueError):
            parser.error("--tools-json must contain a JSON array of nonempty tool names")
    result = inspect(args.skill, args.config or default_configs(args.project.resolve()), args.server_name, tools)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"] == "READ_PROBE_REQUIRED" else 2


if __name__ == "__main__":
    sys.exit(main())

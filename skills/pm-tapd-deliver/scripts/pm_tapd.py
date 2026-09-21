#!/usr/bin/env python3
"""Narrow TAPD OpenAPI adapter for pm-tapd-deliver.

The model must not call TAPD HTTP itself. This script is the only allowed
entry: compact JSON, no secrets in output, dry-run before writes.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parent
contract = SourceFileLoader("tapd_contract", str(ROOT / "tapd-contract.py")).load_module()

DEFAULT_API = "https://api.tapd.cn"
DEFAULT_WEB = "https://www.tapd.cn"
ENTITY_KEYS = {"stories": "Story", "tasks": "Task"}
PAGE_SIZE = 200
SECRET_KEY_PARTS = ("password", "token", "secret", "authorization", "cookie", "header")
RequestFn = Callable[[str, str, dict[str, str] | None, dict[str, str] | None], dict[str, Any]]


class AdapterError(Exception):
    def __init__(self, message: str, exit_code: int = 1, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.extra = extra or {}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SECRET_KEY_PARTS):
                cleaned[key] = "***"
            else:
                cleaned[key] = redact(item)
        return cleaned
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def emit(payload: dict[str, Any], code: int = 0) -> int:
    print(json.dumps(redact(payload), ensure_ascii=False, separators=(",", ":")))
    return code


def fail(message: str, code: int = 1, **extra: Any) -> int:
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return emit(payload, code)


def read_file_credentials() -> dict[str, str]:
    config = Path.home() / ".tapd.json"
    if not config.is_file():
        return {}
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError("credential file unreadable", 2) from exc
    if not isinstance(data, dict):
        raise AdapterError("credential file invalid", 2)
    return {
        "token": str(data.get("access_token") or "").strip(),
        "user": str(data.get("api_user") or "").strip(),
        "password": str(data.get("api_password") or "").strip(),
    }


def load_auth() -> dict[str, str]:
    token = os.environ.get("TAPD_ACCESS_TOKEN", "").strip()
    user = os.environ.get("TAPD_API_USER", "").strip()
    password = os.environ.get("TAPD_API_PASSWORD", "").strip()
    if not ((user and password) or token):
        file_creds = read_file_credentials()
        token = token or file_creds.get("token", "")
        user = user or file_creds.get("user", "")
        password = password or file_creds.get("password", "")
    if user and password:
        encoded = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        return {"mode": "basic", "header": "Basic " + encoded}
    if token:
        return {"mode": "bearer", "header": "Bearer " + token}
    raise AdapterError(
        "missing TAPD credentials; set TAPD_API_USER+TAPD_API_PASSWORD or TAPD_ACCESS_TOKEN",
        3,
    )


def auth_header() -> str:
    return load_auth()["header"]


def api_base() -> str:
    return os.environ.get("TAPD_API_BASE_URL", DEFAULT_API).rstrip("/")


def web_base() -> str:
    return os.environ.get("TAPD_WEB_BASE_URL", DEFAULT_WEB).rstrip("/")


def http_request(
    method: str,
    path: str,
    params: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
) -> dict[str, Any]:
    url = api_base() + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    data = None
    headers = {"Authorization": auth_header(), "Accept": "application/json"}
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raise AdapterError(
            f"HTTP {exc.code}",
            4 if exc.code >= 500 else 1,
            extra={"http_status": exc.code},
        ) from None
    except urllib.error.URLError as exc:
        raise AdapterError("network error", 4) from exc
    try:
        body = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError("non-JSON TAPD response", 4) from exc
    if not isinstance(body, dict):
        raise AdapterError("unexpected TAPD envelope", 4)
    if body.get("status") not in (1, "1"):
        raise AdapterError(str(body.get("info") or "TAPD business error"), 1)
    return {"http_status": status, "data": body.get("data")}


def unwrap_list(data: Any, key: str) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, dict) and key in data and isinstance(data[key], dict):
        item = dict(data[key])
        item.update({k: v for k, v in data.items() if k != key and k not in item})
        return [item]
    if not isinstance(data, list):
        raise AdapterError("list response is not an array", 4)
    items = []
    for row in data:
        if isinstance(row, dict) and key in row and isinstance(row[key], dict):
            item = dict(row[key])
            item.update({k: v for k, v in row.items() if k != key and k not in item})
            items.append(item)
        elif isinstance(row, dict):
            items.append(row)
    return items


def unwrap_one(data: Any, key: str) -> dict[str, Any]:
    items = unwrap_list(data, key)
    if not items:
        raise AdapterError(f"{key} not found", 1)
    return items[0]


def count_value(data: Any) -> int:
    if isinstance(data, dict) and "count" in data:
        return int(data["count"])
    if isinstance(data, int):
        return data
    raise AdapterError("count response missing count", 4)


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def normalize_options(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(key): stringify(value) for key, value in raw.items()}
    if isinstance(raw, list):
        result = {}
        for item in raw:
            if isinstance(item, dict):
                key = item.get("value") or item.get("id") or item.get("name")
                label = item.get("label") or item.get("name") or key
                if key is not None:
                    result[str(key)] = stringify(label)
            else:
                result[str(item)] = str(item)
        return result
    if isinstance(raw, str) and raw.strip():
        return {part: part for part in raw.split("|") if part}
    return {}


def normalize_fields(raw: Any) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    rows: list[tuple[str, dict[str, Any]]] = []
    if isinstance(raw, dict):
        for key, item in raw.items():
            if isinstance(item, dict):
                rows.append((str(key), item))
    elif isinstance(raw, list):
        for row in unwrap_list(raw, "CustomFieldConfig"):
            key = stringify(row.get("custom_field") or row.get("name") or row.get("id"))
            if key:
                rows.append((key, row))
    for key, item in rows:
        label = stringify(item.get("label") or item.get("chinese_name") or item.get("name") or key)
        html_type = stringify(item.get("html_type") or item.get("type")).lower()
        readonly = item.get("readonly") in (1, "1", True) or html_type in {"readonly", "label"}
        fields[key] = {
            "label": label,
            "readonly": readonly,
            "options": normalize_options(item.get("options") or item.get("option")),
            "html_type": html_type,
        }
    return fields


def compact_item(item: dict[str, Any], entity: str) -> dict[str, Any]:
    workspace = stringify(item.get("workspace_id"))
    ident = stringify(item.get("id"))
    compact = {
        "id": ident,
        "workspace_id": workspace,
        "name": stringify(item.get("name")),
        "status": stringify(item.get("status")),
        "owner": stringify(item.get("owner")),
        "description": stringify(item.get("description")),
        "url": item.get("url")
        or (f"{web_base()}/{workspace}/prong/{entity}/view/{ident}" if workspace and ident else ""),
    }
    if entity == "tasks":
        compact["story_id"] = stringify(item.get("story_id"))
        compact["begin"] = stringify(item.get("begin"))
        compact["due"] = stringify(item.get("due"))
        compact["effort"] = stringify(item.get("effort"))
    else:
        compact["priority"] = stringify(item.get("priority") or item.get("priority_label"))
        compact["workitem_type_id"] = stringify(item.get("workitem_type_id"))
        compact["label"] = stringify(item.get("label"))
    custom = {
        key: stringify(value)
        for key, value in item.items()
        if key.startswith("custom_field_") and value not in (None, "")
    }
    if custom:
        compact["custom_fields"] = custom
    return compact


def flatten_payload(payload: dict[str, Any]) -> dict[str, str]:
    form: dict[str, str] = {}
    custom = payload.get("custom_fields")
    for key, value in payload.items():
        if key == "custom_fields":
            continue
        if value in (None, ""):
            continue
        form[str(key)] = stringify(value)
    if isinstance(custom, dict):
        for key, value in custom.items():
            if value not in (None, ""):
                form[str(key)] = stringify(value)
    return form


def cmd_capabilities(_args: argparse.Namespace, _request: RequestFn) -> dict[str, Any]:
    return {
        "ok": True,
        "version": 1,
        "backend": "tapd-openapi",
        "capabilities": {
            "workspace": True,
            "story": True,
            "task": True,
            "fields": True,
            "duplicates": True,
            "write": True,
            "readback": True,
            "workflow": False,
            "attachment": False,
            "mention": False,
        },
        "unavailable": ["workflow", "attachment", "mention"],
    }


def cmd_preflight(_args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    auth = load_auth()
    data = request("GET", "/quickstart/testauth", None, None)["data"]
    api_user = ""
    if isinstance(data, dict):
        api_user = stringify(data.get("api_user") or data.get("user") or "")
    return {
        "ok": True,
        "ready": True,
        "state": "READY",
        "auth": {"method": auth["mode"], "present": True},
        "user": {"api_user": api_user} if api_user else {"present": True},
        "capabilities": cmd_capabilities(_args, request)["capabilities"],
        "probe": {"testauth": True},
        "hint": None,
    }


def cmd_workspace(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    data = request("GET", "/workspaces/get_workspace_info", {"workspace_id": args.id}, None)["data"]
    workspace = unwrap_one(data, "Workspace")
    name = stringify(workspace.get("name") or workspace.get("pretty_name"))
    if args.name and contract.normalized(args.name) != contract.normalized(name):
        raise AdapterError("workspace name does not match id", 1)
    return {
        "ok": True,
        "workspace": {
            "id": stringify(workspace.get("id")),
            "name": name,
            "status": stringify(workspace.get("status")),
        },
    }


def cmd_fields(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    entity = args.entity
    params = {"workspace_id": args.workspace_id}
    fields: dict[str, dict[str, Any]] = {}
    source = "custom_fields_settings"
    if entity == "stories":
        try:
            info = request("GET", "/stories/get_fields_info", params, None)["data"]
            fields = normalize_fields(info)
            source = "get_fields_info"
        except AdapterError:
            fields = {}
    if not fields:
        settings = request("GET", f"/{entity}/custom_fields_settings", params, None)["data"]
        fields = normalize_fields(settings)
        source = "custom_fields_settings"
    return {"ok": True, "entity": entity, "workspace_id": args.workspace_id, "source": source, "fields": fields}


def cmd_find(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    entity = args.entity
    key = ENTITY_KEYS[entity]
    params = {
        "workspace_id": args.workspace_id,
        "name": args.name,
        "limit": str(PAGE_SIZE),
        "fields": "id,name,workspace_id,status,owner,story_id",
    }
    count = count_value(request("GET", f"/{entity}/count", {"workspace_id": args.workspace_id, "name": args.name}, None)["data"])
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        params["page"] = str(page)
        batch = unwrap_list(request("GET", f"/{entity}", params, None)["data"], key)
        items.extend(batch)
        if len(batch) < PAGE_SIZE or len(items) >= count:
            break
        page += 1
        if page > 20:
            break
    complete = len(items) >= count
    result = contract.duplicates(args.name, items, args.workspace_id, complete=complete)
    return {
        "ok": True,
        "entity": entity,
        "workspace_id": args.workspace_id,
        "query": {"name": args.name, "count": count, "returned": len(items), "pages": page, "complete": complete},
        "duplicates": result,
        "items": [compact_item(item, entity) for item in items if str(item.get("id")) in {str(i) for i in result["ids"]}]
        if result["state"] == "duplicate"
        else [],
    }


def cmd_get(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    entity = args.entity
    data = request("GET", f"/{entity}", {"workspace_id": args.workspace_id, "id": args.id}, None)["data"]
    item = unwrap_one(data, ENTITY_KEYS[entity])
    return {"ok": True, "entity": entity, "item": compact_item(item, entity), "raw_keys": sorted(item.keys())}


def cmd_write(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    payload = json.loads(args.payload) if args.payload else json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AdapterError("payload must be a JSON object", 2)
    form = flatten_payload(payload)
    if not form.get("workspace_id"):
        raise AdapterError("payload.workspace_id is required", 2)
    if not form.get("name") and not form.get("id"):
        raise AdapterError("payload.name is required to create", 2)
    entity = args.entity
    action = "update" if form.get("id") else "create"
    result = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "entity": entity,
        "action": action,
        "form": form,
    }
    if args.dry_run:
        result["would_post"] = f"/{entity}"
        return result
    data = request("POST", f"/{entity}", None, form)["data"]
    item = unwrap_one(data, ENTITY_KEYS[entity])
    result["item"] = compact_item(item, entity)
    return result


def cmd_readback(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    expected = json.loads(args.expect) if args.expect else json.loads(Path(args.expect_file).read_text(encoding="utf-8"))
    if not isinstance(expected, dict):
        raise AdapterError("expect must be a JSON object", 2)
    got = cmd_get(args, request)["item"]
    mismatches = []
    for key, value in expected.items():
        if key == "custom_fields" and isinstance(value, dict):
            actual_custom = got.get("custom_fields") or {}
            for custom_key, custom_value in value.items():
                if stringify(actual_custom.get(custom_key)) != stringify(custom_value):
                    mismatches.append(custom_key)
            continue
        if stringify(got.get(key)) != stringify(value):
            mismatches.append(key)
    return {
        "ok": not mismatches,
        "entity": args.entity,
        "id": args.id,
        "matched": not mismatches,
        "mismatches": mismatches,
        "item": got,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("capabilities", help="V1 capability contract")
    sub.add_parser("preflight", help="Auth + read-only probe; never writes")

    workspace = sub.add_parser("workspace", help="Resolve workspace by id")
    workspace.add_argument("--id", required=True)
    workspace.add_argument("--name", default="")

    fields = sub.add_parser("fields", help="Live field schema")
    fields.add_argument("--workspace-id", required=True)
    fields.add_argument("--entity", choices=("stories", "tasks"), required=True)

    find = sub.add_parser("find", help="Duplicate search with pagination completeness")
    find.add_argument("--entity", choices=("stories", "tasks"), required=True)
    find.add_argument("--workspace-id", required=True)
    find.add_argument("--name", required=True)

    get_cmd = sub.add_parser("get", help="Read one story or task")
    get_cmd.add_argument("--entity", choices=("stories", "tasks"), required=True)
    get_cmd.add_argument("--workspace-id", required=True)
    get_cmd.add_argument("--id", required=True)

    write = sub.add_parser("write", help="Create or update; --dry-run posts nothing")
    write.add_argument("--entity", choices=("stories", "tasks"), required=True)
    write.add_argument("--payload", default="")
    write.add_argument("--payload-file", default="")
    write.add_argument("--dry-run", action="store_true")

    readback = sub.add_parser("readback", help="GET and assert expected fields")
    readback.add_argument("--entity", choices=("stories", "tasks"), required=True)
    readback.add_argument("--workspace-id", required=True)
    readback.add_argument("--id", required=True)
    readback.add_argument("--expect", default="")
    readback.add_argument("--expect-file", default="")
    return parser


COMMANDS = {
    "capabilities": cmd_capabilities,
    "preflight": cmd_preflight,
    "workspace": cmd_workspace,
    "fields": cmd_fields,
    "find": cmd_find,
    "get": cmd_get,
    "write": cmd_write,
    "readback": cmd_readback,
}


def main(argv: list[str] | None = None, request: RequestFn | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "write" and not (args.payload or args.payload_file):
        return fail("write requires --payload or --payload-file", 2)
    if args.command == "readback" and not (args.expect or args.expect_file):
        return fail("readback requires --expect or --expect-file", 2)
    try:
        payload = COMMANDS[args.command](args, request or http_request)
        return emit(payload, 0 if payload.get("ok", True) else 1)
    except AdapterError as exc:
        return fail(str(exc), exc.exit_code, **exc.extra)
    except json.JSONDecodeError:
        return fail("invalid JSON input", 2)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Narrow TAPD OpenAPI adapter for pm-tapd-deliver.

The model must not call TAPD HTTP itself. This script is the only allowed
entry: compact JSON, no secrets in output, dry-run before writes.
"""

from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
contract = SourceFileLoader("tapd_contract", str(ROOT / "tapd-contract.py")).load_module()
deliverables = SourceFileLoader(
    "verify_local_deliverables", str(ROOT / "verify-local-deliverables.py")
).load_module()

DEFAULT_API = "https://api.tapd.cn"
DEFAULT_WEB = "https://www.tapd.cn"
ENTITY_KEYS = {"stories": "Story", "tasks": "Task"}
ATTACHMENT_TYPE = {"stories": "story", "tasks": "task"}
WORKFLOW_SYSTEM = {"stories": "story", "tasks": "task"}
PAGE_SIZE = 200
SECRET_KEY_PARTS = ("password", "token", "secret", "authorization", "cookie", "header")
INACTIVE_MEMBER_STATUS = {"0", "disabled", "invalid", "inactive", "deleted"}
TASK_DOCUMENTED_STATUSES = ("open", "progressing", "done")
TASK_DOCUMENTED_TRANSITIONS = {
    "open": {"progressing", "done"},
    "progressing": {"done", "open"},
    "done": {"open", "progressing"},
}
AT_WHO_TAG_RE = re.compile(r"<b\b[^>]*class=['\"]at-who['\"][^>]*>.*?</b>", re.I | re.S)
RequestFn = Callable[..., dict[str, Any]]


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


def fail(message: str, exit_code: int = 1, **extra: Any) -> int:
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return emit(payload, exit_code)


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


def encode_multipart(
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
) -> tuple[bytes, str]:
    boundary = "----PmTapdBoundary" + os.urandom(8).hex()
    chunks: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        chunks.append(f"--{boundary}".encode("ascii"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"))
        chunks.append(b"")
        chunks.append(value.encode("utf-8"))

    def add_file(name: str, filename: str, content: bytes, content_type: str) -> None:
        safe_name = filename.replace("\r", " ").replace("\n", " ").replace('"', "_")
        chunks.append(f"--{boundary}".encode("ascii"))
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{safe_name}"'.encode("utf-8")
        )
        chunks.append(f"Content-Type: {content_type}".encode("ascii"))
        chunks.append(b"")
        chunks.append(content)

    for name, value in fields.items():
        add_field(name, value)
    for name, (filename, content, content_type) in files.items():
        add_file(name, filename, content, content_type)
    chunks.append(f"--{boundary}--".encode("ascii"))
    chunks.append(b"")
    return b"\r\n".join(chunks), f"multipart/form-data; boundary={boundary}"


def http_request(
    method: str,
    path: str,
    params: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> dict[str, Any]:
    url = api_base() + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    data = None
    headers = {"Authorization": auth_header(), "Accept": "application/json"}
    if files is not None:
        data, content_type = encode_multipart(form or {}, files)
        headers["Content-Type"] = content_type
    elif form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        extra: dict[str, Any] = {"http_status": exc.code}
        try:
            body = json.loads(raw.decode("utf-8"))
            if isinstance(body, dict) and body.get("info"):
                extra["info"] = stringify(body.get("info"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            snippet = raw[:200].decode("utf-8", "replace")
            if snippet:
                extra["body"] = snippet
        raise AdapterError(f"HTTP {exc.code}", 4 if exc.code >= 500 else 1, extra=extra) from None
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


def soft_unwrap(data: Any, key: str) -> dict[str, Any]:
    if data in (None, "", []):
        return {}
    try:
        return unwrap_one(data, key)
    except AdapterError:
        return data if isinstance(data, dict) else {}


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


def split_csv(raw: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for part in (raw or "").split(","):
        token = part.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        items.append(token)
    return items


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
        text = raw.strip()
        # TAPD custom field settings sometimes encode the option map as a
        # JSON string rather than returning an object.
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            return normalize_options(decoded)
        return {part: part for part in text.split("|") if part}
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


def flatten_payload(payload: dict[str, Any], field_schema: dict[str, dict[str, Any]] | None = None, entity: str = "") -> dict[str, str]:
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
                field = (field_schema or {}).get(str(key)) or {}
                # TAPD's task category custom field stores the display label.
                # Its schema exposes numeric option keys, so normalize key
                # input to the label while accepting labels unchanged.
                if entity == "tasks" and field.get("label") == "任务类别":
                    options = field.get("options") or {}
                    raw_value = stringify(value)
                    form[str(key)] = options.get(raw_value, raw_value)
                else:
                    form[str(key)] = stringify(value)
    return form


def html_escape(value: str) -> str:
    return html_lib.escape(value, quote=True)


def mention_node(nick: str) -> str:
    escaped = html_escape(nick)
    return (
        f'<b class="at-who" contenteditable="false" data-userid="{escaped}" '
        f'data-type="user">@{escaped}</b>'
    )


def build_comment_description(text: str, nicks: list[str]) -> str:
    nodes = " ".join(mention_node(nick) for nick in nicks)
    body = html_escape(text).strip()
    if nodes and body:
        return f"{nodes} {body}"
    return nodes or body


def extract_mention_nodes(description: str) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    for tag in AT_WHO_TAG_RE.findall(description or ""):
        userid_match = re.search(r'data-userid=["\']([^"\']+)["\']', tag, re.I)
        type_match = re.search(r'data-type=["\']user["\']', tag, re.I)
        inner_match = re.search(r"<b\b[^>]*>(.*?)</b>", tag, re.I | re.S)
        if not userid_match or not type_match or not inner_match:
            continue
        nick = html_lib.unescape(userid_match.group(1))
        inner = html_lib.unescape(re.sub(r"<[^>]+>", "", inner_match.group(1))).strip()
        if inner.startswith("@"):
            inner = inner[1:]
        nodes.append({"nick": nick, "text": inner, "html": tag})
    return nodes


def mention_verification(requested: list[str], description: str) -> dict[str, Any]:
    nodes = extract_mention_nodes(description or "")
    valid = [node["nick"] for node in nodes if node["nick"] == node["text"]]
    requested_set = list(requested)
    valid_set = set(valid)
    extra = [node["nick"] for node in nodes if node["nick"] not in requested_set or node["nick"] != node["text"]]
    missing = [nick for nick in requested_set if nick not in valid_set]
    if requested_set and not missing and not extra and len(nodes) == len(requested_set):
        status = "MENTION_VERIFIED"
    elif valid_set.intersection(requested_set) and missing:
        status = "MENTION_PARTIAL"
    else:
        status = "MENTION_UNVERIFIED"
    return {
        "status": status,
        "requested": requested_set,
        "found": valid,
        "missing": missing,
        "extra": extra,
        "nodes": nodes,
    }


def normalize_status_map(data: Any) -> dict[str, str]:
    if data is None:
        return {}
    if isinstance(data, dict) and "WorkflowStatusMap" in data:
        return normalize_status_map(data.get("WorkflowStatusMap"))
    if isinstance(data, dict):
        result: dict[str, str] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                status = stringify(value.get("status") or value.get("origin_status") or key)
                label = stringify(value.get("name") or value.get("label") or value.get("chinese_name") or status)
                if status:
                    result[status] = label
            else:
                result[str(key)] = stringify(value)
        return result
    if isinstance(data, list):
        result = {}
        for item in data:
            if isinstance(item, dict) and "WorkflowStatusMap" in item:
                result.update(normalize_status_map(item.get("WorkflowStatusMap")))
            elif isinstance(item, dict):
                status = stringify(item.get("status") or item.get("origin_status") or item.get("id"))
                label = stringify(item.get("name") or item.get("label") or status)
                if status:
                    result[status] = label
        return result
    return {}


def normalize_transitions(data: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if data is None:
        return rows
    if isinstance(data, dict) and "WorkflowTransition" in data:
        return normalize_transitions(data.get("WorkflowTransition"))
    if isinstance(data, dict) and "transitions" in data:
        return normalize_transitions(data.get("transitions"))
    if isinstance(data, dict):
        src = stringify(
            data.get("from")
            or data.get("previous_status")
            or data.get("origin_status")
            or data.get("from_status")
        )
        dst = data.get("to") or data.get("next_status") or data.get("destination_status") or data.get("to_status")
        if src and dst is not None:
            if isinstance(dst, list):
                for item in dst:
                    rows.append({"from": src, "to": stringify(item)})
            else:
                rows.append({"from": src, "to": stringify(dst)})
            return rows
        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        rows.extend(normalize_transitions({"from": key, **item}))
                    else:
                        rows.append({"from": str(key), "to": stringify(item)})
            elif isinstance(value, dict):
                nested = dict(value)
                nested.setdefault("from", key)
                rows.extend(normalize_transitions(nested))
            elif value not in (None, ""):
                rows.append({"from": str(key), "to": stringify(value)})
        return [row for row in rows if row.get("from") and row.get("to")]
    if isinstance(data, list):
        for item in data:
            rows.extend(normalize_transitions(item))
        return [row for row in rows if row.get("from") and row.get("to")]
    return rows


def resolve_status_key(status_map: dict[str, str], value: str) -> str:
    raw = stringify(value)
    if not raw:
        raise AdapterError("status is required", 2)
    if raw in status_map:
        return raw
    matches = [key for key, label in status_map.items() if label == raw]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AdapterError("status label is ambiguous", 1)
    if not status_map:
        return raw
    raise AdapterError("status missing from status map", 1)


def transition_allowed(transitions: list[dict[str, str]], source: str, target: str) -> bool:
    if source == target:
        return True
    return any(row.get("from") == source and row.get("to") == target for row in transitions)


def documented_task_transitions() -> list[dict[str, str]]:
    rows = []
    for source, targets in TASK_DOCUMENTED_TRANSITIONS.items():
        for target in sorted(targets):
            rows.append({"from": source, "to": target})
    return rows


def nested_entity(item: dict[str, Any], *keys: str) -> dict[str, Any]:
    current = dict(item)
    for key in keys:
        inner = current.get(key)
        if isinstance(inner, dict):
            merged = dict(inner)
            merged.update({k: v for k, v in current.items() if k != key and k not in merged})
            current = merged
    return current


def compact_member(item: dict[str, Any]) -> dict[str, str]:
    item = nested_entity(item, "UserWorkspace", "User")
    nick = stringify(item.get("user") or item.get("nick") or item.get("userid"))
    return {
        "nick": nick,
        "name": stringify(item.get("name") or item.get("user_name")),
        "email": stringify(item.get("email")),
        "role_id": stringify(item.get("role_id")),
        "status": stringify(item.get("status")),
    }


def member_active(member: dict[str, str]) -> bool:
    status = stringify(member.get("status")).lower()
    return status not in INACTIVE_MEMBER_STATUS


def resolve_members(members: list[dict[str, str]], tokens: list[str]) -> list[dict[str, str]]:
    resolved: list[dict[str, str]] = []
    for token in tokens:
        nick_hits = [item for item in members if item.get("nick") == token]
        if len(nick_hits) > 1:
            raise AdapterError(f"duplicate nick: {token}", 1, extra={"code": "MEMBER_AMBIGUOUS", "token": token})
        if len(nick_hits) == 1:
            hit = nick_hits[0]
            if not member_active(hit):
                raise AdapterError(f"member inactive: {token}", 1, extra={"code": "MEMBER_INACTIVE", "token": token})
            resolved.append(hit)
            continue
        name_hits = [item for item in members if item.get("name") == token]
        if len(name_hits) > 1:
            raise AdapterError(f"duplicate name: {token}", 1, extra={"code": "MEMBER_AMBIGUOUS", "token": token})
        if len(name_hits) == 1:
            hit = name_hits[0]
            if not member_active(hit):
                raise AdapterError(f"member inactive: {token}", 1, extra={"code": "MEMBER_INACTIVE", "token": token})
            resolved.append(hit)
            continue
        raise AdapterError(f"member not found: {token}", 1, extra={"code": "MEMBER_NOT_FOUND", "token": token})
    return resolved


def compact_comment(item: dict[str, Any]) -> dict[str, Any]:
    description = stringify(item.get("description"))
    return {
        "id": stringify(item.get("id")),
        "workspace_id": stringify(item.get("workspace_id")),
        "entry_type": stringify(item.get("entry_type")),
        "entry_id": stringify(item.get("entry_id")),
        "author": stringify(item.get("author")),
        "description": description,
        "mentions": [node["nick"] for node in extract_mention_nodes(description)],
    }


def compact_attachment(item: dict[str, Any], fallback_type: str = "") -> dict[str, str]:
    return {
        "id": stringify(item.get("id")),
        "workspace_id": stringify(item.get("workspace_id")),
        "type": stringify(item.get("type") or item.get("entry_type") or fallback_type),
        "entry_id": stringify(item.get("entry_id")),
        "filename": stringify(item.get("filename") or item.get("name") or item.get("origin_name")),
        "size": stringify(item.get("size") or item.get("filesize")),
    }


def paginate(request: RequestFn, path: str, params: dict[str, str], key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    page = 1
    while True:
        query = dict(params)
        query["page"] = str(page)
        query.setdefault("limit", str(PAGE_SIZE))
        batch = unwrap_list(request("GET", path, query, None)["data"], key)
        fresh = []
        for item in batch:
            ident = stringify(item.get("id") or item.get("user") or item.get("filename"))
            marker = ident or stringify(item)
            if marker in seen:
                continue
            seen.add(marker)
            fresh.append(item)
        items.extend(fresh)
        if len(batch) < PAGE_SIZE or not fresh:
            break
        page += 1
        if page > 20:
            break
    return items


def cmd_capabilities(_args: argparse.Namespace, _request: RequestFn) -> dict[str, Any]:
    return {
        "ok": True,
        "version": 2,
        "backend": "tapd-openapi",
        "capabilities": {
            "workspace": True,
            "story": True,
            "task": True,
            "fields": True,
            "duplicates": True,
            "write": True,
            "readback": True,
            "workflow": True,
            "members": True,
            "mention": True,
            "attachment": True,
            "attachment_list": True,
            "attachment_upload": True,
            "attachment_readback": True,
        },
        "contracts": {
            "attachment_upload": "community",
            "task_workflow": "documented_fallback_if_official_rejects",
            "mention": "native_at_who",
        },
        "unavailable": [],
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
        "hint": "api_user is the API account, not automatically a person nick for comments",
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
    data = request(
        "GET",
        f"/{entity}",
        {"workspace_id": args.workspace_id, "id": args.id},
        None,
    )["data"]
    item = unwrap_one(data, ENTITY_KEYS[entity])
    return {"ok": True, "entity": entity, "item": compact_item(item, entity)}


def cmd_write(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    payload = json.loads(args.payload) if args.payload else json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AdapterError("payload must be a JSON object", 2)
    field_schema = {}
    if args.entity == "tasks" and isinstance(payload.get("custom_fields"), dict):
        field_schema = cmd_fields(argparse.Namespace(entity="tasks", workspace_id=stringify(payload.get("workspace_id"))), request)["fields"]
    form = flatten_payload(payload, field_schema=field_schema, entity=args.entity)
    # Preserve the latest task status unless the caller explicitly requested a
    # transition. This protects against concurrent online edits, server-side
    # defaults, or interface side effects during a partial field correction.
    if args.entity == "tasks" and form.get("id") and "status" not in form:
        current = cmd_get(
            argparse.Namespace(entity="tasks", workspace_id=form.get("workspace_id", ""), id=form["id"]),
            request,
        )["item"]
        if current.get("status"):
            form["status"] = stringify(current["status"])
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


def official_workflow(
    request: RequestFn,
    entity: str,
    workspace_id: str,
    workitem_type_id: str,
    source: str,
    target: str,
) -> dict[str, Any]:
    system = WORKFLOW_SYSTEM[entity]
    params = {"workspace_id": workspace_id, "system": system}
    if workitem_type_id:
        params["workitem_type_id"] = workitem_type_id
    status_map = normalize_status_map(request("GET", "/workflows/status_map", params, None)["data"])
    transitions = normalize_transitions(request("GET", "/workflows/all_transitions", params, None)["data"])
    from_key = resolve_status_key(status_map, source)
    to_key = resolve_status_key(status_map, target)
    legal = transition_allowed(transitions, from_key, to_key)
    return {
        "ok": True,
        "legal": legal,
        "entity": entity,
        "workspace_id": workspace_id,
        "workitem_type_id": workitem_type_id,
        "from": source,
        "to": target,
        "from_key": from_key,
        "to_key": to_key,
        "source": "official_workflow",
        "status_map": status_map,
        "transitions": transitions,
        "reason": "unchanged" if from_key == to_key else ("allowed" if legal else "transition not in official map"),
    }


def documented_task_workflow(workspace_id: str, source: str, target: str, fallback_reason: str) -> dict[str, Any]:
    status_map = {item: item for item in TASK_DOCUMENTED_STATUSES}
    if source not in status_map:
        raise AdapterError("task status missing from documented statuses", 1)
    if target not in status_map:
        raise AdapterError("task status missing from documented statuses", 1)
    transitions = documented_task_transitions()
    legal = transition_allowed(transitions, source, target)
    return {
        "ok": True,
        "legal": legal,
        "entity": "tasks",
        "workspace_id": workspace_id,
        "from": source,
        "to": target,
        "from_key": source,
        "to_key": target,
        "source": "documented_task_status",
        "status_map": status_map,
        "transitions": transitions,
        "reason": "unchanged" if source == target else ("documented_allow" if legal else "not in documented task graph"),
        "fallback_reason": fallback_reason,
        "workflow_proven": False,
    }


def cmd_workflow(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    entity = args.entity
    if entity == "stories" and not args.workitem_type_id:
        raise AdapterError("workitem_type_id is required for story workflow", 2)
    if entity == "stories":
        result = official_workflow(
            request,
            entity,
            args.workspace_id,
            args.workitem_type_id,
            args.from_status,
            args.to_status,
        )
        result["workflow_proven"] = True
        return result
    try:
        result = official_workflow(
            request,
            entity,
            args.workspace_id,
            args.workitem_type_id,
            args.from_status,
            args.to_status,
        )
        result["workflow_proven"] = True
        return result
    except AdapterError as exc:
        if exc.exit_code == 4:
            raise
        return documented_task_workflow(
            args.workspace_id,
            args.from_status,
            args.to_status,
            stringify(exc.extra.get("info") or exc),
        )


def cmd_members(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    items = paginate(request, "/workspaces/users", {"workspace_id": args.workspace_id}, "UserWorkspace")
    members = [compact_member(item) for item in items]
    result: dict[str, Any] = {
        "ok": True,
        "workspace_id": args.workspace_id,
        "members": members,
        "count": len(members),
    }
    tokens = split_csv(args.nicks)
    if tokens:
        result["resolved"] = resolve_members(members, tokens)
    return result


def comment_payload(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    nicks = split_csv(args.mentions)
    if not nicks:
        raise AdapterError("mentions are required", 2, extra={"code": "MENTION_REQUIRED"})
    if not args.author:
        raise AdapterError("author is required; do not infer from Task owner", 2)
    members = paginate(request, "/workspaces/users", {"workspace_id": args.workspace_id}, "UserWorkspace")
    resolved = resolve_members([compact_member(item) for item in members], nicks)
    resolved_nicks = [item["nick"] for item in resolved]
    description = build_comment_description(args.text or "", resolved_nicks)
    form = {
        "workspace_id": args.workspace_id,
        "entry_id": args.id,
        "entry_type": args.entity,
        "author": args.author,
        "description": description,
    }
    return {
        "ok": True,
        "entity": args.entity,
        "workspace_id": args.workspace_id,
        "entry_id": args.id,
        "author": args.author,
        "mentions": resolved,
        "description": description,
        "form": form,
    }


def get_comment(request: RequestFn, workspace_id: str, comment_id: str) -> dict[str, Any]:
    data = request("GET", "/comments", {"id": comment_id, "workspace_id": workspace_id}, None)["data"]
    return compact_comment(unwrap_one(data, "Comment"))


def cmd_comment(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    action = args.action
    if action == "list":
        items = paginate(
            request,
            "/comments",
            {
                "workspace_id": args.workspace_id,
                "entry_id": args.id,
                "entry_type": args.entity,
            },
            "Comment",
        )
        return {
            "ok": True,
            "entity": args.entity,
            "workspace_id": args.workspace_id,
            "entry_id": args.id,
            "comments": [compact_comment(item) for item in items],
        }
    if action == "get":
        item = get_comment(request, args.workspace_id, args.comment_id or args.id)
        return {"ok": True, "item": item}
    preview = comment_payload(args, request)
    if action == "preview" or args.dry_run:
        preview["dry_run"] = True
        preview["would_post"] = "/comments"
        return preview
    data = request("POST", "/comments", None, preview["form"])["data"]
    created = compact_comment(soft_unwrap(data, "Comment"))
    comment_id = created.get("id")
    if not comment_id:
        raise AdapterError("comment id missing from create response", 1, extra={"code": "MENTION_UNVERIFIED"})
    readback = get_comment(request, args.workspace_id, comment_id)
    verification = mention_verification([item["nick"] for item in preview["mentions"]], readback.get("description", ""))
    identity_ok = (
        readback.get("workspace_id") == args.workspace_id
        and readback.get("entry_type") == args.entity
        and readback.get("entry_id") == args.id
        and readback.get("author") == args.author
    )
    if not identity_ok:
        verification["status"] = "MENTION_UNVERIFIED"
        verification["identity_ok"] = False
    else:
        verification["identity_ok"] = True
    return {
        "ok": verification["status"] == "MENTION_VERIFIED",
        "action": "add",
        "item": created,
        "readback": readback,
        "verification": verification,
        "mentions": preview["mentions"],
    }


def list_attachments(request: RequestFn, entity: str, workspace_id: str, entry_id: str) -> list[dict[str, str]]:
    att_type = ATTACHMENT_TYPE[entity]
    items = paginate(
        request,
        "/attachments",
        {"workspace_id": workspace_id, "type": att_type, "entry_id": entry_id},
        "Attachment",
    )
    return [compact_attachment(item, att_type) for item in items]


def find_attachment(items: list[dict[str, str]], filename: str = "", attachment_id: str = "") -> dict[str, str] | None:
    if attachment_id:
        for item in items:
            if item.get("id") == attachment_id:
                return item
    if filename:
        for item in items:
            if item.get("filename") == filename:
                return item
    return None


def cmd_attachments(args: argparse.Namespace, request: RequestFn) -> dict[str, Any]:
    action = args.action
    att_type = ATTACHMENT_TYPE[args.entity]
    if action == "list":
        items = list_attachments(request, args.entity, args.workspace_id, args.id)
        return {
            "ok": True,
            "entity": args.entity,
            "type": att_type,
            "workspace_id": args.workspace_id,
            "entry_id": args.id,
            "attachments": items,
        }
    if action == "readback":
        items = list_attachments(request, args.entity, args.workspace_id, args.id)
        found = find_attachment(items, args.filename, args.attachment_id)
        if not found:
            return {
                "ok": False,
                "matched": False,
                "error": "attachment not found on readback",
                "attachments": items,
            }
        mismatches = []
        expected = {
            "workspace_id": args.workspace_id,
            "type": att_type,
            "entry_id": args.id,
        }
        if args.filename:
            expected["filename"] = args.filename
        if args.attachment_id:
            expected["id"] = args.attachment_id
        for key, value in expected.items():
            if stringify(found.get(key)) != stringify(value):
                mismatches.append(key)
        if not found.get("id"):
            mismatches.append("id")
        return {
            "ok": not mismatches,
            "matched": not mismatches,
            "mismatches": mismatches,
            "item": found,
        }
    local = deliverables.validate(Path(args.file), Path(args.root))
    if not local.get("ok"):
        raise AdapterError("local file validation failed", 1, extra={"file": local})
    filename = stringify(local.get("filename"))
    existing = list_attachments(request, args.entity, args.workspace_id, args.id)
    duplicate = find_attachment(existing, filename)
    if duplicate:
        raise AdapterError(
            "same-name attachment exists; will not overwrite",
            1,
            extra={"code": "ATTACHMENT_DUPLICATE", "item": duplicate},
        )
    fields = {
        "workspace_id": args.workspace_id,
        "type": att_type,
        "entry_id": args.id,
    }
    result = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "entity": args.entity,
        "type": att_type,
        "workspace_id": args.workspace_id,
        "entry_id": args.id,
        "filename": filename,
        "file": local,
        "form": fields,
        "contract": "community",
        "would_post": "/files/upload_attachment",
    }
    if args.dry_run:
        return result
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    raw = Path(str(local["resolved_path"])).read_bytes()
    files = {"file": (filename, raw, content_type)}
    try:
        data = request("POST", "/files/upload_attachment", None, fields, files=files)["data"]
    except AdapterError as exc:
        status = exc.extra.get("http_status")
        if status in (404, 405, 415) or "not found" in str(exc).lower():
            raise AdapterError(
                "attachment upload unavailable",
                1,
                extra={"code": "ATTACHMENT_UPLOAD_UNAVAILABLE", "http_status": status},
            ) from None
        raise
    uploaded = compact_attachment(soft_unwrap(data, "Attachment"), att_type)
    items = list_attachments(request, args.entity, args.workspace_id, args.id)
    found = find_attachment(items, filename, uploaded.get("id") or "")
    if not found:
        raise AdapterError("attachment readback failed", 1, extra={"code": "ATTACHMENT_READBACK_FAILED", "uploaded": uploaded})
    mismatches = [
        key
        for key, value in {
            "workspace_id": args.workspace_id,
            "type": att_type,
            "entry_id": args.id,
            "filename": filename,
        }.items()
        if stringify(found.get(key)) != stringify(value)
    ]
    if not found.get("id"):
        mismatches.append("id")
    result.update(
        {
            "ok": not mismatches,
            "dry_run": False,
            "item": found,
            "mismatches": mismatches,
        }
    )
    return result


def add_entity_target(parser: argparse.ArgumentParser, with_id: bool = True) -> None:
    parser.add_argument("--entity", choices=("stories", "tasks"), required=True)
    parser.add_argument("--workspace-id", required=True)
    if with_id:
        parser.add_argument("--id", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("capabilities", help="V2 capability contract")
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

    workflow = sub.add_parser("workflow", help="Prove a status transition before write")
    workflow.add_argument("--entity", choices=("stories", "tasks"), required=True)
    workflow.add_argument("--workspace-id", required=True)
    workflow.add_argument("--workitem-type-id", default="")
    workflow.add_argument("--from", dest="from_status", required=True)
    workflow.add_argument("--to", dest="to_status", required=True)

    members = sub.add_parser("members", help="List and uniquely resolve workspace members")
    members.add_argument("--workspace-id", required=True)
    members.add_argument("--nicks", default="")

    comment = sub.add_parser("comment", help="Native mention comments")
    comment_sub = comment.add_subparsers(dest="action", required=True)
    for action, extra in (
        ("preview", True),
        ("add", True),
        ("list", False),
        ("get", False),
    ):
        item = comment_sub.add_parser(action)
        item.add_argument("--entity", choices=("stories", "tasks"), required=action != "get")
        item.add_argument("--workspace-id", required=True)
        item.add_argument("--id", default="", required=action != "get")
        item.add_argument("--comment-id", default="")
        if extra:
            item.add_argument("--author", default="")
            item.add_argument("--text", default="")
            item.add_argument("--mentions", default="")
            item.add_argument("--dry-run", action="store_true")

    attachments = sub.add_parser("attachments", help="List, upload, and read back attachments")
    att_sub = attachments.add_subparsers(dest="action", required=True)
    for action in ("list", "upload", "readback"):
        item = att_sub.add_parser(action)
        add_entity_target(item)
        if action == "upload":
            item.add_argument("--file", required=True)
            item.add_argument("--root", required=True)
            item.add_argument("--dry-run", action="store_true")
        if action == "readback":
            item.add_argument("--filename", default="")
            item.add_argument("--attachment-id", default="")
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
    "workflow": cmd_workflow,
    "members": cmd_members,
    "comment": cmd_comment,
    "attachments": cmd_attachments,
}


def main(argv: list[str] | None = None, request: RequestFn | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "write" and not (args.payload or args.payload_file):
        return fail("write requires --payload or --payload-file", 2)
    if args.command == "readback" and not (args.expect or args.expect_file):
        return fail("readback requires --expect or --expect-file", 2)
    if args.command == "comment" and args.action == "get" and not (args.comment_id or args.id):
        return fail("comment get requires --comment-id", 2)
    if args.command == "attachments" and args.action == "readback" and not (args.filename or args.attachment_id):
        return fail("attachment readback requires --filename or --attachment-id", 2)
    try:
        payload = COMMANDS[args.command](args, request or http_request)
        return emit(payload, 0 if payload.get("ok", True) else 1)
    except AdapterError as exc:
        return fail(str(exc), exit_code=exc.exit_code, **exc.extra)
    except json.JSONDecodeError:
        return fail("invalid JSON input", 2)


if __name__ == "__main__":
    raise SystemExit(main())

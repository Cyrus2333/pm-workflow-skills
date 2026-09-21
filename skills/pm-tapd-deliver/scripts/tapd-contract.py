#!/usr/bin/env python3
"""Pure helpers for resolved schemas and complete duplicate-query results. No TAPD calls."""

import json
import unicodedata


def _options_dict(raw):
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {part: part for part in raw.split("|") if part}
        if isinstance(parsed, dict):
            return {str(key): str(value) for key, value in parsed.items()}
    return {}


def resolve_field(fields, label, api_name=None):
    if not isinstance(fields, dict) or not fields:
        raise ValueError("schema unavailable; not proof of no fields")
    candidates = [
        (key, item)
        for key, item in fields.items()
        if isinstance(item, dict)
        and item.get("label") == label
        and (api_name is None or key == api_name)
    ]
    if len(candidates) != 1:
        raise ValueError("field label missing or ambiguous; use current write schema")
    key, item = candidates[0]
    if item.get("readonly") in (1, "1", True):
        raise ValueError("field is readonly")
    return key, item


def resolve_enum(field, value):
    options = _options_dict(field.get("options"))
    if not options:
        raise ValueError("enum unresolved; fetch actual schema")
    if value in options:
        return value
    matches = [key for key, option_label in options.items() if option_label == value]
    if len(matches) != 1:
        raise ValueError("enum missing or ambiguous")
    return matches[0]


def normalized(title):
    return " ".join(unicodedata.normalize("NFKC", title).split())


def duplicates(title, items, workspace, complete=False, updating_id=None):
    matches = [
        item["id"]
        for item in items
        if str(item.get("workspace_id")) == str(workspace)
        and str(item.get("id")) != str(updating_id)
        and normalized(item.get("name", "")) == normalized(title)
    ]
    if matches:
        return {"state": "duplicate", "ids": matches}
    return {"state": "clear_complete" if complete else "incomplete", "ids": []}

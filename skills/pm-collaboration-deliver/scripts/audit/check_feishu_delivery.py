#!/usr/bin/env python3
"""Validate Feishu publishing and render-review evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


RESULTS = {"pass", "fail", "not_applicable"}
VISUAL_CHECKS = {
    "content_complete", "text_legible", "line_clarity", "canvas_fit",
    "document_scale", "inline_readability", "zoom_readability",
}
DOCUMENT_CHECKS = {
    "title_and_outline", "scanability", "table_layout", "visual_placement",
    "visual_scale", "links_and_resources", "traditional_structure",
    "terminology_layering", "local_visual_proximity",
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def check_results(checks: Any, required: set[str], label: str, errors: list[str]) -> None:
    if not isinstance(checks, dict):
        errors.append(f"{label} must be an object")
        return
    for key in required:
        if checks.get(key) not in RESULTS:
            errors.append(f"{label}.{key} must be pass, fail, or not_applicable")
    failed = sorted(key for key, value in checks.items() if value == "fail")
    if failed:
        errors.append(f"{label} contains failures: " + ", ".join(failed))


def validate(data: dict[str, Any], base: Path) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "1.1":
        errors.append("schema_version must be 1.1")
    if data.get("platform") != "feishu_docx":
        errors.append("platform must be feishu_docx")

    document = data.get("document")
    xml = ""
    if not isinstance(document, dict):
        errors.append("document is required")
    else:
        for field in ("url", "document_id", "fetched_xml", "checked_at"):
            if not nonempty(document.get(field)):
                errors.append(f"document.{field} is required")
        if not isinstance(document.get("revision_id"), int) or document.get("revision_id", 0) < 0:
            errors.append("document.revision_id must be a non-negative integer")
        fetched = document.get("fetched_xml")
        if nonempty(fetched):
            path = resolve(base, fetched)
            if not path.is_file():
                errors.append(f"document.fetched_xml does not exist: {path}")
            else:
                xml = path.read_text(encoding="utf-8")
                if "<title" not in xml:
                    errors.append("fetched XML has no title block")
        for field in ("required_headings", "required_phrases"):
            values = document.get(field, [])
            if not isinstance(values, list) or not all(nonempty(item) for item in values):
                errors.append(f"document.{field} must be a string array")
                continue
            for item in values:
                if xml and item not in xml:
                    errors.append(f"fetched XML is missing {field[:-1]}: {item}")

    publish = data.get("publish")
    if not isinstance(publish, dict):
        errors.append("publish is required")
    else:
        if publish.get("strategy") not in {"create", "block_update", "overwrite"}:
            errors.append("publish.strategy must be create, block_update, or overwrite")
        if publish.get("identity") not in {"user", "bot"}:
            errors.append("publish.identity must be user or bot")
        if not isinstance(publish.get("overwrite_used"), bool):
            errors.append("publish.overwrite_used must be boolean")
        if publish.get("overwrite_used") is True and publish.get("protected_resources_checked") is not True:
            errors.append("overwrite requires protected_resources_checked=true")

    visuals = data.get("visuals")
    if not isinstance(visuals, list):
        errors.append("visuals must be an array")
        visuals = []
    ids: list[str] = []
    tokens: list[str] = []
    for index, visual in enumerate(visuals):
        label = f"visuals[{index}]"
        if not isinstance(visual, dict):
            errors.append(f"{label} must be an object")
            continue
        for field in ("id", "question", "resource_type", "block_token", "source_type", "preview_path", "checked_at"):
            if not nonempty(visual.get(field)):
                errors.append(f"{label}.{field} is required")
        if visual.get("delivery_role") not in {"inline", "zoomable"}:
            errors.append(f"{label}.delivery_role must be inline or zoomable")
        if nonempty(visual.get("id")):
            ids.append(visual["id"])
        if nonempty(visual.get("block_token")):
            tokens.append(visual["block_token"])
            if xml and visual["block_token"] not in xml:
                errors.append(f"{label}.block_token is absent from fetched XML")
        preview = visual.get("preview_path")
        if nonempty(preview) and not resolve(base, preview).is_file():
            errors.append(f"{label}.preview_path does not exist: {resolve(base, preview)}")
        check_results(visual.get("checks"), VISUAL_CHECKS, f"{label}.checks", errors)
        checks = visual.get("checks", {})
        if visual.get("delivery_role") == "inline" and isinstance(checks, dict) and checks.get("inline_readability") != "pass":
            errors.append(f"{label} inline asset requires inline_readability=pass")
        if visual.get("delivery_role") == "zoomable" and isinstance(checks, dict) and checks.get("zoom_readability") != "pass":
            errors.append(f"{label} zoomable asset requires zoom_readability=pass")
        issues = visual.get("issues")
        if not isinstance(issues, list):
            errors.append(f"{label}.issues must be an array")
        elif issues:
            errors.append(f"{label}.issues must be resolved before delivery")
    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    duplicate_tokens = sorted({item for item in tokens if tokens.count(item) > 1})
    if duplicate_ids:
        errors.append("duplicate visual ids: " + ", ".join(duplicate_ids))
    if duplicate_tokens:
        errors.append("duplicate visual block tokens: " + ", ".join(duplicate_tokens))

    document_view = data.get("document_view")
    if not isinstance(document_view, dict):
        errors.append("document_view is required")
    else:
        for field in ("target", "checked_at"):
            if not nonempty(document_view.get(field)):
                errors.append(f"document_view.{field} is required")
        check_results(document_view.get("checks"), DOCUMENT_CHECKS, "document_view.checks", errors)
        issues = document_view.get("issues")
        if not isinstance(issues, list):
            errors.append("document_view.issues must be an array")
        elif issues:
            errors.append("document_view.issues must be resolved before delivery")

    reader = data.get("reader_test")
    if not isinstance(reader, dict):
        errors.append("reader_test is required")
    else:
        if not nonempty(reader.get("reader_context")):
            errors.append("reader_test.reader_context is required")
        if reader.get("result") not in {"pass", "fail"}:
            errors.append("reader_test.result must be pass or fail")
        elif reader.get("result") == "fail":
            errors.append("reader_test failed")
        if not isinstance(reader.get("questions_answered"), list) or not reader.get("questions_answered"):
            errors.append("reader_test.questions_answered must be a non-empty array")
        issues = reader.get("issues")
        if not isinstance(issues, list):
            errors.append("reader_test.issues must be an array")
        elif issues:
            errors.append("reader_test.issues must be resolved before delivery")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True, type=Path)
    args = parser.parse_args()
    if not args.audit.is_file():
        print(f"error: audit does not exist: {args.audit}", file=sys.stderr)
        return 2
    try:
        data = json.loads(args.audit.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("error: audit root must be an object", file=sys.stderr)
        return 2
    errors = validate(data, args.audit.parent)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 2
    print("Feishu delivery audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

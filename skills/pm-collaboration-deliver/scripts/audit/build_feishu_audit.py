#!/usr/bin/env python3
"""Build a draft Feishu delivery audit from a lark-cli docs +fetch JSON response."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path


WHITEBOARD_RE = re.compile(r"<whiteboard\b[^>]*\btoken=\"([^\"]+)\"[^>]*?(?:/>|>.*?</whiteboard>)", re.S)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.S)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-json", required=True, type=Path)
    parser.add_argument("--document-url", required=True)
    parser.add_argument("--preview-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        envelope = json.loads(args.fetch_json.read_text(encoding="utf-8"))
        document = envelope["data"]["document"]
        content = document["content"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: invalid fetch response: {exc}", file=sys.stderr)
        return 2
    if not isinstance(content, str):
        print("error: document content is not XML text", file=sys.stderr)
        return 2
    match = TITLE_RE.search(content)
    title = html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip() if match else ""
    tokens = list(dict.fromkeys(WHITEBOARD_RE.findall(content)))
    fetched_xml = args.out.with_name(args.out.stem + "-fetched.xml")
    fetched_xml.parent.mkdir(parents=True, exist_ok=True)
    fetched_xml.write_text(content, encoding="utf-8")
    visuals = []
    for index, token in enumerate(tokens, start=1):
        candidates = sorted(args.preview_dir.glob(f"{token}.*"))
        preview = candidates[0] if candidates else args.preview_dir / f"{token}.jpg"
        visuals.append({
            "id": f"VIS-{index:02d}",
            "question": "TODO: this visual's reader question",
            "resource_type": "whiteboard",
            "block_token": token,
            "source_type": "unknown",
            "delivery_role": "inline",
            "preview_path": str(preview.resolve()),
            "checked_at": "TODO: ISO-8601 time",
            "checks": {
                "content_complete": "fail", "text_legible": "fail", "line_clarity": "fail",
                "canvas_fit": "fail", "document_scale": "fail",
                "inline_readability": "fail", "zoom_readability": "not_applicable",
            },
            "issues": ["TODO: export and inspect the final Feishu preview"],
        })
    audit = {
        "schema_version": "1.1", "platform": "feishu_docx",
        "document": {
            "url": args.document_url,
            "document_id": document.get("document_id") or args.document_url.rstrip("/").split("/")[-1],
            "revision_id": document.get("revision_id", 0),
            "fetched_xml": str(fetched_xml.resolve()),
            "checked_at": "TODO: ISO-8601 time",
            "required_headings": [title] if title else [],
            "required_phrases": [],
        },
        "publish": {"strategy": "block_update", "identity": envelope.get("identity", "user"),
                    "overwrite_used": False, "protected_resources_checked": True},
        "visuals": visuals,
        "document_view": {
            "target": "Feishu reading view", "checked_at": "TODO: ISO-8601 time",
            "checks": {"title_and_outline": "fail", "scanability": "fail", "table_layout": "fail",
                       "visual_placement": "fail", "visual_scale": "fail", "links_and_resources": "fail",
                       "traditional_structure": "fail", "terminology_layering": "fail",
                       "local_visual_proximity": "fail"},
            "issues": ["TODO: inspect the published reading view"],
        },
        "reader_test": {"reader_context": "Only the published Feishu document is available",
                        "result": "fail", "questions_answered": [],
                        "issues": ["TODO: run an independent reader test"]},
    }
    args.out.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Draft Feishu audit: {args.out} ({len(tokens)} whiteboards)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

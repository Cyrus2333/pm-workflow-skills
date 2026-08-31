#!/usr/bin/env python3
"""Validate explicitly supplied local TAPD deliverables without scanning directories."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def resolved(path: Path) -> Path:
    return Path(os.path.realpath(path))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate(path: Path, root: Path) -> dict[str, object]:
    item: dict[str, object] = {"path": str(path), "ok": False, "errors": []}
    errors: list[str] = item["errors"]  # type: ignore[assignment]
    if not path.exists():
        errors.append("file does not exist")
        return item
    if not path.is_file():
        errors.append("path is not a regular file")
        return item
    real_path = resolved(path)
    if not is_within(real_path, root):
        errors.append("resolved path is outside the allowed root")
        return item
    if real_path.stat().st_size <= 0:
        errors.append("file is empty")
        return item
    try:
        with real_path.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        errors.append(f"file is not readable: {exc}")
        return item
    item.update({"ok": True, "resolved_path": str(real_path), "filename": real_path.name, "size": real_path.stat().st_size})
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Allowed deliverables root")
    parser.add_argument("files", nargs="+", type=Path, help="Explicit files to validate")
    args = parser.parse_args()
    if not args.root.exists() or not args.root.is_dir():
        print(json.dumps({"ok": False, "error": "allowed root does not exist or is not a directory"}, ensure_ascii=False))
        return 2
    root = resolved(args.root)
    results = [validate(path, root) for path in args.files]
    ok = all(bool(result["ok"]) for result in results)
    print(json.dumps({"ok": ok, "root": str(root), "files": results}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

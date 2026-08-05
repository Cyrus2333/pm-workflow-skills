#!/usr/bin/env python3
"""Validate cross-document links, Markdown tables, and skill resource conventions."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def error(message: str) -> None:
    ERRORS.append(message)


def markdown_files() -> list[Path]:
    return [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]


def validate_links(files: list[Path]) -> None:
    link_pattern = re.compile(r"\]\(([^)]+)\)")
    for path in files:
        text = path.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            candidate = (path.parent / target).resolve()
            if not candidate.exists():
                error(f"{path.relative_to(ROOT)}: broken local link {raw_target}")


def validate_tables(files: list[Path]) -> None:
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        in_fence = False
        for index, line in enumerate(lines[:-1]):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if not (line.startswith("|") and line.rstrip().endswith("|")):
                continue
            separator = lines[index + 1]
            if not (separator.startswith("|") and separator.rstrip().endswith("|")):
                continue
            cells = separator.strip("|").split("|")
            if not cells or not all(set(cell.strip()) <= set("-: ") for cell in cells):
                continue
            expected = len(line.strip("|").split("|"))
            for row_index, row in enumerate(lines[index + 2 :], start=index + 2):
                if not row.startswith("|"):
                    break
                actual = len(row.strip("|").split("|"))
                if actual != expected:
                    error(
                        f"{path.relative_to(ROOT)}:{row_index + 1}: "
                        f"table has {actual} cells; expected {expected}"
                    )


def validate_skill_conventions() -> None:
    required_headings = ("## 优先读取", "## 完成标准")
    for skill_dir in sorted((ROOT / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        for heading in required_headings:
            if heading not in text:
                error(f"{skill_file.relative_to(ROOT)}: missing required heading {heading}")
        if not re.search(r"^## 默认输出(结构)?$", text, flags=re.MULTILINE):
            error(f"{skill_file.relative_to(ROOT)}: missing required heading ## 默认输出 or ## 默认输出结构")
        for reference in re.findall(r"\]\((\./references/[^)]+)\)", text):
            if not (skill_file.parent / reference.removeprefix("./")).exists():
                error(f"{skill_file.relative_to(ROOT)}: missing referenced resource {reference}")


def validate_workflow_docs() -> None:
    for relative in ("README.md", "WORKFLOW_GUIDE.md", "CONTRIBUTING.md", "ITERATION_GUIDE.md"):
        if not (ROOT / relative).exists():
            error(f"missing workflow document {relative}")


def main() -> int:
    files = markdown_files()
    validate_links(files)
    validate_tables(files)
    validate_skill_conventions()
    validate_workflow_docs()
    if ERRORS:
        print("\n".join(f"ERROR: {item}" for item in ERRORS), file=sys.stderr)
        return 1
    print(f"Validated documentation: {len(files)} Markdown files, links, tables, and workflow conventions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

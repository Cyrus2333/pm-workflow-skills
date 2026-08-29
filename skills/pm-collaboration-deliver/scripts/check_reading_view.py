#!/usr/bin/env python3
"""Lightweight structural checks for a PRD collaboration reading view."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FORBIDDEN_HEADINGS = {
    "先说结论",
    "开发前必须确认",
    "研发方案需要继续回答",
    "本次必须拍板",
    "评审通过底线",
    "会后交付",
    "评审记录区",
    "图文路由记录",
    "同核记录",
    "同核过程",
    "同核与下钻",
    "生成说明",
    "编排说明",
    "素材处置记录",
    "为什么这个示例合格",
    "阅读编排级别",
    "内部阅读级别",
    "系统协作与下钻",
    "协作与下钻",
}
INTERNAL_TERMS = (
    "VisualSpec",
    "Manifest",
    "product-doc-contract",
    "internal-build-plan",
    "语义见证",
    "产品结果单元",
    "R0 保留原稿",
    "R1 局部说明",
    "R2 标准产品文档",
    "R3 复杂产品文档",
)
PROCESS_PATTERNS = {
    r"按.{0,24}转译为.{0,24}(版本|文档|阅读版)": "generation narration appears in the document",
    r"本次没有(?:新画|重画|生成|编辑).{0,20}(页面|图片|原型)": "visual production log appears in the document",
    r"未从截图推导.{0,20}(规则|结论)": "source-audit narration appears in the document",
}
TEMPLATE_PATTERNS = {
    r"<!--\s*(?:R[0-3]|只保留|按需插入|交付前删除)[\s\S]*?-->": "traditional-document template instruction remains",
}
TEMPLATE_ASSET = Path(__file__).resolve().parents[1] / "assets" / "traditional-product-document-template.md"
KNOWN_TEMPLATE_PLACEHOLDERS = set(
    re.findall(r"\{\{([^}]+)\}\}", TEMPLATE_ASSET.read_text(encoding="utf-8"))
) if TEMPLATE_ASSET.is_file() else set()
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
VISUAL_STATE_TERMS = ("现状", "目标", "结构示意", "参考")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
TRACE_ID_RE = re.compile(r"\b(?:OBJ|SCN|FLOW|PAGE|IA|FR|CAP|RULE|AC|METRIC|MET|RISK)-[0-9A-Z]+\b")
TRACE_ID_WARNING_THRESHOLD = 12
LONG_PARAGRAPH_THRESHOLD = 160
LONG_LIST_ITEM_THRESHOLD = 120
WIDE_TABLE_COLUMN_THRESHOLD = 5
TABLE_DENSITY_WARNING_THRESHOLD = 8
OUTPUT_AS_GOAL_RE = re.compile(
    r"(?:^|[。；\n])(?:目标|目标结果)[：:]?[^。；\n]{0,12}(?:新增|上线|开发|建设|支持|改版|重构)[^。；\n]{0,16}(?:页面|入口|按钮|功能|模块|能力|系统)",
    re.MULTILINE,
)
PROCESS_AS_GOAL_RE = re.compile(
    r"(?:^|[。；\n])(?:目标|目标结果)[：:]?[^。；\n]{0,20}(?:按时上线|完成开发|完成上线|完成交付|如期发布|需求落地|功能落地)",
    re.MULTILINE,
)
# Section-content attribution heuristics (warning-level signals, not verdicts).
# Background carries only objective facts; problem carries gaps derived from
# facts; goal carries end-state outcomes. Words below signal content that has
# likely leaked into the wrong section.
BACKGROUND_INTENT_RE = re.compile(r"本期|我们将|我们希望|我们计划|旨在|诉求")
PROBLEM_SOLUTION_RE = re.compile(r"本期|我们将|新增|通过.+?(?:完成|实现|解决)|上线|支持用户")
GOAL_PROCESS_RE = re.compile(r"新增|支持|完成上线|完成交付|完成开发|引导用户|进入.{0,6}页面|按时|落地")
# 评审关注 block: extraction-only, every entry carries a source anchor.
REVIEW_FOCUS_HEADING_RE = re.compile(r"^评审关注")
REVIEW_FOCUS_ANCHOR_RE = re.compile(
    r"第\s*\d+\s*章|\d+\.\d+|\b(?:FR|RULE|AC|RISK|FLOW|PAGE)-[0-9A-Z]+\b|（来源|见「|见第")
REVIEW_FOCUS_MAX_ITEMS = 7


def classify_attribution_heading(title: str) -> str:
    """Classify a heading as background/problem/goal for attribution checks.

    Combined headings (e.g. 需求背景与目标) are skipped to avoid misattribution.
    """
    if "目标" in title and ("背景" in title or "问题" in title):
        return ""
    if "背景" in title or "现状" in title:
        return "background"
    if "问题" in title:
        return "problem"
    if "目标" in title:
        return "goal"
    return ""
TRADITIONAL_SPINE = {
    "background_problem": ("需求背景", "背景、问题", "背景与目标", "背景与现状", "当前问题", "问题"),
    "goal": ("需求目标", "问题与目标", "背景与目标", "目标"),
    "scope": ("需求范围", "本期范围", "范围与非目标", "范围"),
    "solution": ("产品方案", "需求方案", "整体方案", "方案总览", "需求范围与方案", "范围与方案"),
    "detail": ("需求详情", "功能详情"),
    "acceptance": ("验收标准", "验收要点", "核心验收", "验收"),
}
DEPRECATED_HEADINGS = {
    "需求背景与诉求": "use 需求背景、需求目标 and 需求范围 as direct product-language sections",
    "方案概述": "use 产品方案 as the default traditional PRD heading",
    "方案详情": "use 需求详情 with business-specific subsection titles",
}
DOWNSTREAM_HEADINGS = ("系统协作", "协作与下钻", "研发下钻", "研发交接", "研发 spec", "技术方案", "接口", "关联资料", "附录")
IMPLEMENTATION_TERMS = (
    "研发 spec", "接口契约", "幂等", "并发控制", "结果映射", "错误码",
    "消息队列", "任务队列实现", "缓存方案", "存储方案", "数据库表", "算法实现", "日志结构",
)
CODEISH_PRODUCT_RE = re.compile(
    r"(?:https?://\S+|/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.{}-]+)+|\b(?:retry|update|tag|status|state)=[A-Za-z0-9_-]+\b|\bHTTP\s*[1-5][0-9]{2}\b|\b(?:302|500)\s*(?:跳转|重定向|页|页面)|\bNode\b)",
    re.IGNORECASE,
)
INTERNAL_PRIORITY_RE = re.compile(r"\bP[0-3]\s*(?:信息|字段|状态|参数)\b", re.IGNORECASE)
HEADING_PREFIX_RE = re.compile(r"^(?:(?:\d+(?:\.\d+)*)|[一二三四五六七八九十]+)[、.：:]?\s*")


def normalize_heading(title: str) -> str:
    return HEADING_PREFIX_RE.sub("", title).strip()


def readability_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    paragraphs: list[tuple[int, str]] = []
    current: list[str] = []
    current_line = 0
    in_code = False

    def flush() -> None:
        nonlocal current, current_line
        if current:
            paragraphs.append((current_line, " ".join(current)))
            current = []
            current_line = 0

    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        ordered_item = re.match(r"^\d+[.)、]\s+(.+)$", stripped)
        if stripped.startswith("```"):
            flush()
            in_code = not in_code
            continue
        if in_code:
            continue
        if not stripped or stripped.startswith(("#", "|", ">", "- ", "* ", "+ ", "![")) or ordered_item:
            flush()
            if stripped.startswith(("- ", "* ", "+ ")) and len(stripped[2:].strip()) > LONG_LIST_ITEM_THRESHOLD:
                warnings.append(
                    f"long list item at line {number} ({len(stripped[2:].strip())} chars); split independent conclusions"
                )
            if ordered_item and len(ordered_item.group(1).strip()) > LONG_LIST_ITEM_THRESHOLD:
                warnings.append(
                    f"long ordered-list item at line {number} ({len(ordered_item.group(1).strip())} chars); split independent conclusions"
                )
            continue
        if not current:
            current_line = number
        current.append(stripped)
    flush()

    for line, paragraph in paragraphs:
        if len(paragraph) > LONG_PARAGRAPH_THRESHOLD:
            warnings.append(
                f"long prose paragraph at line {line} ({len(paragraph)} chars); split, tabulate, or visualize"
            )

    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        columns = len([cell for cell in stripped.strip("|").split("|")])
        if columns > WIDE_TABLE_COLUMN_THRESHOLD:
            warnings.append(
                f"wide table at line {number} ({columns} columns); consider a smaller table plus prose conclusion"
            )
            break

    return warnings


def inspect(document: Path, source: Path, profile: str = "generic") -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = document.read_text(encoding="utf-8")

    if not text.strip():
        errors.append("document is empty")
        return errors, warnings

    warnings.extend(readability_warnings(text))

    headings = [(len(level), title.strip()) for level, title in HEADING_RE.findall(text)]
    normalized = {normalize_heading(title) for _, title in headings}
    if profile == "traditional-prd":
        for semantic, candidates in TRADITIONAL_SPINE.items():
            if not any(any(candidate in title for candidate in candidates) for title in normalized):
                errors.append(f"traditional PRD spine missing semantic section: {semantic}")
        first_heading = headings[0][1] if headings else ""
        if "协作 PRD" in first_heading or "协作PRD" in first_heading:
            warnings.append("primary title looks like a collaboration brief; use the product requirement name for a traditional PRD")
    for term in sorted(FORBIDDEN_HEADINGS & normalized):
        errors.append(f"forbidden reading-view heading: {term}")
    for heading, message in DEPRECATED_HEADINGS.items():
        if heading in normalized:
            warnings.append(f"deprecated generic heading: {heading}; {message}")
    for title in sorted(normalized):
        if "背景" in title and "目标" in title:
            warnings.append(
                f"background/problem/goal merged into one heading: {title}; split into 背景与现状 / 当前问题 / 需求目标 so each fact, gap, and outcome has its own checkable home"
            )
    for term in INTERNAL_TERMS:
        if term in text:
            errors.append(f"internal generation term leaked into document: {term}")
    for pattern, message in PROCESS_PATTERNS.items():
        if re.search(pattern, text):
            errors.append(message)
    for pattern, message in TEMPLATE_PATTERNS.items():
        if re.search(pattern, text):
            errors.append(message)
    unresolved_placeholders = sorted(
        set(re.findall(r"\{\{([^}]+)\}\}", text)) & KNOWN_TEMPLATE_PLACEHOLDERS
    )
    if unresolved_placeholders:
        errors.append(
            "unresolved traditional-document template placeholder remains: "
            + ", ".join(unresolved_placeholders)
        )

    h2_numbers: list[int] = []
    for level, title in headings:
        if level == 2:
            match = re.match(r"^(\d+)[、.：:]", title)
            if match:
                h2_numbers.append(int(match.group(1)))
    duplicates = sorted({number for number in h2_numbers if h2_numbers.count(number) > 1})
    if duplicates:
        errors.append("duplicate level-2 section numbers: " + ", ".join(map(str, duplicates)))

    for alt, raw in IMAGE_RE.findall(text):
        target = raw.strip().split(" ", 1)[0].strip("<>")
        if target.startswith(("http://", "https://", "data:")):
            image_path = None
        else:
            image_path = Path(target)
            if not image_path.is_absolute():
                image_path = document.parent / image_path
            if not image_path.exists():
                errors.append(f"broken local image: {target}")
        if not any(term in alt for term in VISUAL_STATE_TERMS):
            warnings.append(
                f"image alt text does not identify current, target, structural, or reference state: {alt or target}"
            )

    source_name = source.name
    if source_name not in text and str(source) not in text:
        warnings.append(f"formal source is not linked by filename: {source_name}")
    if len(headings) > 30:
        warnings.append(f"document has {len(headings)} headings; check whether the reading path is fragmented")
    trace_ids = TRACE_ID_RE.findall(text)
    if len(trace_ids) > TRACE_ID_WARNING_THRESHOLD:
        warnings.append(
            f"document contains {len(trace_ids)} trace-ID mentions; replace verification scaffolding with targeted source links"
        )
    if OUTPUT_AS_GOAL_RE.search(text):
        warnings.append("goal appears to describe a feature output; rewrite it as a measurable user or business result")
    if PROCESS_AS_GOAL_RE.search(text):
        warnings.append("goal appears to describe a delivery process; omit the goal or rewrite it as a key user or business metric impact")

    attribution_hits: dict[str, list[int]] = {"background": [], "problem": [], "goal": []}
    active_section = ""
    in_code = False
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading_match:
            active_section = classify_attribution_heading(normalize_heading(heading_match.group(1)))
            continue
        if not active_section or not stripped or stripped.startswith(("|", "![", "<!--", ">")):
            continue
        if active_section == "background" and BACKGROUND_INTENT_RE.search(stripped):
            attribution_hits["background"].append(number)
        elif active_section == "problem" and PROBLEM_SOLUTION_RE.search(stripped):
            attribution_hits["problem"].append(number)
        elif active_section == "goal" and GOAL_PROCESS_RE.search(stripped):
            attribution_hits["goal"].append(number)
    if attribution_hits["background"]:
        warnings.append(
            "background section contains intent or appeal wording at lines "
            + ", ".join(map(str, attribution_hits["background"]))
            + "; background states objective facts only — move intent to scope/solution"
        )
    if attribution_hits["problem"]:
        warnings.append(
            "problem section contains solution wording at lines "
            + ", ".join(map(str, attribution_hits["problem"]))
            + "; problems derive from facts without prescribing the solution"
        )
    if attribution_hits["goal"]:
        warnings.append(
            "goal section contains process or delivery wording at lines "
            + ", ".join(map(str, attribution_hits["goal"]))
            + "; goals are global end-states with metrics, or the section is omitted"
        )

    # 评审关注 block discipline: extraction-only entries, each with a source
    # anchor; the whole block is optional and stays compact.
    in_review_focus = False
    in_code = False
    review_entries: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading_match:
            in_review_focus = bool(REVIEW_FOCUS_HEADING_RE.match(normalize_heading(heading_match.group(1))))
            continue
        if not in_review_focus or not stripped:
            continue
        if re.match(r"^[-*+]\s+|^\d+[.、]\s*", stripped):
            review_entries.append((number, stripped))
    missing_anchor = [str(n) for n, item in review_entries if not REVIEW_FOCUS_ANCHOR_RE.search(item)]
    if missing_anchor:
        warnings.append(
            "review-focus entries lack a source anchor at lines "
            + ", ".join(missing_anchor)
            + "; every 评审关注 entry must cite the formal PRD section or FR/RULE/AC ID it was extracted from"
        )
    if len(review_entries) > REVIEW_FOCUS_MAX_ITEMS:
        warnings.append(
            f"review-focus block has {len(review_entries)} entries (max {REVIEW_FOCUS_MAX_ITEMS}); extraction is too broad — keep only what the formal PRD itself flags"
        )

    active_heading = ""
    in_code = False
    leaked_terms: dict[str, list[int]] = {}
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading_match:
            active_heading = normalize_heading(heading_match.group(1))
            continue
        if any(term.lower() in active_heading.lower() for term in DOWNSTREAM_HEADINGS):
            continue
        for term in IMPLEMENTATION_TERMS:
            if term.lower() in stripped.lower():
                leaked_terms.setdefault(term, []).append(number)
        if INTERNAL_PRIORITY_RE.search(stripped):
            leaked_terms.setdefault("internal priority label", []).append(number)
    for term, locations in leaked_terms.items():
        warnings.append(
            f"implementation/internal term appears in the primary reading layer at lines "
            + ", ".join(map(str, locations)) + f": {term}; rewrite as a product result or move it downstream"
        )

    codeish_locations: list[int] = []
    active_heading = ""
    in_code = False
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading_match:
            active_heading = normalize_heading(heading_match.group(1))
            continue
        if any(term.lower() in active_heading.lower() for term in DOWNSTREAM_HEADINGS):
            continue
        if CODEISH_PRODUCT_RE.search(stripped):
            codeish_locations.append(number)
    if codeish_locations:
        warnings.append(
            "route, parameter, status-code, or runtime term appears in the primary reading layer at lines "
            + ", ".join(map(str, codeish_locations))
            + "; translate it into user entry, page behavior, feedback, and result or move it downstream"
        )

    table_count = sum(
        1 for line in text.splitlines()
        if re.match(r"^\|(?:\s*:?-{3,}:?\s*\|)+\s*$", line.strip())
    )
    image_count = len(IMAGE_RE.findall(text))
    if table_count >= TABLE_DENSITY_WARNING_THRESHOLD and image_count == 0:
        warnings.append(
            f"document contains {table_count} tables and no inline visual; check for specification-style expansion and replace page changes with a screenshot, prototype, or shorter prose where appropriate"
        )

    normalized_lines: dict[str, list[int]] = {}
    in_code = False
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or stripped.startswith(("#", "|", "![", "<!--")):
            continue
        normalized_line = re.sub(r"[\s，。；：、,.!！?？（）()《》\[\]]+", "", stripped)
        if len(normalized_line) >= 24:
            normalized_lines.setdefault(normalized_line, []).append(number)
    for line_value, locations in normalized_lines.items():
        if len(locations) > 1:
            warnings.append(
                "repeated conclusion at lines " + ", ".join(map(str, locations))
                + "; keep one primary home and cross-reference it"
            )
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument(
        "--profile",
        choices=("traditional-prd", "review-brief", "generic"),
        default="traditional-prd",
        help="validate the intended reader-facing document type",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="treat readability and source-link warnings as delivery failures",
    )
    args = parser.parse_args()
    for path in (args.document, args.source):
        if not path.is_file():
            print(f"file does not exist: {path}", file=sys.stderr)
            return 2
    errors, warnings = inspect(args.document.resolve(), args.source.resolve(), args.profile)
    for item in warnings:
        print(f"warning: {item}")
    for item in errors:
        print(f"error: {item}", file=sys.stderr)
    if errors or (args.fail_on_warnings and warnings):
        return 2
    print("Reading view structural checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

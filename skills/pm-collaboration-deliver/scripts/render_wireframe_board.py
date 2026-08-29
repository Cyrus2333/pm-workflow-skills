#!/usr/bin/env python3
"""Render a small, generic black-and-white interaction board from JSON."""

from __future__ import annotations

import argparse
import html
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_THEME = {
    "background": "#ffffff",
    "canvas": "#ffffff",
    "block": "#f2f2f2",
    "line": "#8c8c8c",
    "text": "#111111",
    "subtext": "#595959",
    "accent": "#262626",
    "disabled": "#d9d9d9",
    "font": "PingFang SC, Microsoft YaHei, sans-serif",
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("spec root must be an object")
    return data


def wrap(text: str, limit: int) -> list[str]:
    lines: list[str] = []
    current = ""
    punctuation = "，。！？；：、,.!?;:）)]】》"
    for char in str(text):
        if char != "\n" and char in punctuation and current:
            current += char
            continue
        if char == "\n" or (current and len(current) >= limit):
            lines.append(current)
            current = "" if char == "\n" else char
        else:
            current += char
    if current or not lines:
        lines.append(current)
    return lines


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    boards = data.get("boards")
    if not isinstance(boards, list) or not boards:
        return ["boards must be a non-empty array"]
    delivery_role = data.get("delivery_role")
    if delivery_role is not None and delivery_role not in {"inline", "zoomable"}:
        errors.append("delivery_role must be inline or zoomable")
    ids: list[str] = []
    for index, board in enumerate(boards):
        if not isinstance(board, dict):
            errors.append(f"boards[{index}] must be an object")
            continue
        board_id = board.get("id")
        if not isinstance(board_id, str) or not board_id:
            errors.append(f"boards[{index}].id is required")
        else:
            ids.append(board_id)
        if not board.get("title"):
            errors.append(f"boards[{index}].title is required")
        layout = board.get("layout")
        if layout is not None:
            if not isinstance(layout, dict):
                errors.append(f"boards[{index}].layout must be an object")
            elif not isinstance(layout.get("row"), int) or not isinstance(layout.get("column"), int):
                errors.append(f"boards[{index}].layout requires integer row and column")
        blocks = board.get("blocks")
        if not isinstance(blocks, list):
            errors.append(f"boards[{index}].blocks must be an array")
            continue
        for block_index, block in enumerate(blocks):
            if not isinstance(block, dict) or block.get("type") not in {
                "text", "kv", "scale", "chips", "input", "button", "state", "tabs",
                "card", "annotation", "divider", "progress"
            }:
                errors.append(f"boards[{index}].blocks[{block_index}] has unsupported type")
                continue
            if block.get("type") == "tabs" and not block.get("items"):
                errors.append(f"boards[{index}].blocks[{block_index}].items is required")
            if block.get("type") == "card" and not block.get("title"):
                errors.append(f"boards[{index}].blocks[{block_index}].title is required")
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        errors.append("duplicate board ids: " + ", ".join(duplicates))
    known = set(ids)
    links = data.get("links", [])
    if not isinstance(links, list):
        errors.append("links must be an array")
        links = []
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append(f"links[{index}] must be an object")
            continue
        if link.get("from") not in known or link.get("to") not in known:
            errors.append(f"links[{index}] points to an unknown board")
        if not isinstance(link.get("label"), str) or not link.get("label", "").strip():
            errors.append(f"links[{index}].label is required")
    entry_ids = data.get("entry_board_ids")
    if entry_ids is not None:
        if not isinstance(entry_ids, list) or not entry_ids:
            errors.append("entry_board_ids must be a non-empty array")
        else:
            unknown_entries = sorted(set(entry_ids) - known)
            if unknown_entries:
                errors.append("entry_board_ids references unknown boards: " + ", ".join(unknown_entries))
            adjacency: dict[str, list[str]] = {item: [] for item in known}
            for link in links:
                if isinstance(link, dict) and link.get("from") in known and link.get("to") in known:
                    adjacency[link["from"]].append(link["to"])
            reachable: set[str] = set()
            queue = list(entry_ids)
            while queue:
                current = queue.pop(0)
                if current in reachable:
                    continue
                reachable.add(current)
                queue.extend(adjacency.get(current, []))
            missing = sorted(known - reachable)
            if missing:
                errors.append("unreachable boards: " + ", ".join(missing))
    return errors


class Svg:
    def __init__(self, width: int, height: int, theme: dict[str, str]):
        self.width = width
        self.height = height
        self.theme = theme
        self.parts = [f'<rect width="{width}" height="{height}" fill="{theme["canvas"]}"/>']

    def text(self, x: float, y: float, value: str, size: int = 14, *, bold: bool = False,
             color: str | None = None, anchor: str = "start") -> None:
        weight = ' font-weight="600"' if bold else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{esc(self.theme["font"])}" font-size="{size}" '
            f'fill="{color or self.theme["text"]}" text-anchor="{anchor}"{weight}>{esc(value)}</text>'
        )

    def rect(self, x: float, y: float, width: float, height: float, *, fill: str = "none",
             stroke: str | None = None, radius: int = 8, dash: bool = False) -> None:
        dash_attr = ' stroke-dasharray="5 4"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke or self.theme["line"]}"{dash_attr}/>'
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, *, arrow: bool = False,
             dash: bool = False) -> None:
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        dash_attr = ' stroke-dasharray="6 5"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{self.theme["line"]}" '
            f'stroke-width="1.5"{dash_attr}{marker}/>'
        )

    def polyline(self, points: list[tuple[float, float]], *, arrow: bool = False,
                 dash: bool = False) -> None:
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        dash_attr = ' stroke-dasharray="6 5"' if dash else ""
        value = " ".join(f"{x},{y}" for x, y in points)
        self.parts.append(
            f'<polyline points="{value}" fill="none" stroke="{self.theme["line"]}" '
            f'stroke-width="1.5"{dash_attr}{marker}/>'
        )

    def finish(self) -> str:
        defs = (
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" '
            'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#8c8c8c"/></marker></defs>'
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">{defs}{"".join(self.parts)}</svg>'
        )


def chip_rows(items: list[Any], width: int) -> list[list[tuple[str, int]]]:
    rows: list[list[tuple[str, int]]] = [[]]
    used = 0
    for item in items:
        value = str(item)
        chip_width = min(width, max(52, len(value) * 14 + 20))
        if rows[-1] and used + 8 + chip_width > width:
            rows.append([])
            used = 0
        rows[-1].append((value, chip_width))
        used += chip_width + (8 if used else 0)
    return rows


def block_height(block: dict[str, Any], width: int) -> int:
    kind = block["type"]
    if kind == "text":
        return max(34, len(wrap(block.get("text", ""), max(12, width // 15))) * 19 + 12)
    if kind == "kv":
        lines = max(len(wrap(block.get("label", ""), 16)), len(wrap(block.get("value", ""), 18)))
        return max(38, lines * 18 + 12)
    if kind == "chips":
        return 34 + max(1, len(chip_rows(block.get("items", []), width))) * 36
    if kind == "input":
        content = block.get("value", block.get("placeholder", ""))
        lines = len(wrap(content, max(12, width // 14))) if block.get("multiline") else 1
        return 44 + max(38, lines * 18 + 20)
    if kind == "state":
        lines = len(wrap(block.get("body", ""), max(12, width // 14)))
        return 54 + max(24, lines * 18)
    if kind == "tabs":
        items = [str(item) for item in block.get("items", [])]
        rows = max(1, (len(items) + 2) // 3)
        return rows * 42 + 8
    if kind == "card":
        title_lines = len(wrap(block.get("title", ""), max(12, width // 14)))
        body_lines = len(wrap(block.get("body", ""), max(12, width // 14))) if block.get("body") else 0
        fields = block.get("fields", [])
        field_lines = sum(
            max(1, len(wrap(field.get("value", ""), max(10, width // 18))))
            for field in fields if isinstance(field, dict)
        )
        action_height = 42 if block.get("action") else 0
        return 32 + title_lines * 19 + body_lines * 18 + field_lines * 22 + action_height
    if kind == "annotation":
        lines = len(wrap(block.get("text", ""), max(12, width // 14)))
        return 44 + max(20, lines * 18)
    return {"scale": 72, "button": 54, "divider": 24, "progress": 66}[kind]


def render_block(svg: Svg, block: dict[str, Any], x: int, y: int, width: int) -> int:
    theme = svg.theme
    kind = block["type"]
    if kind == "divider":
        svg.line(x, y + 10, x + width, y + 10)
        return 24
    if kind == "text":
        lines = wrap(block.get("text", ""), max(12, width // 15))
        for index, line in enumerate(lines):
            svg.text(x, y + 17 + index * 18, line, 13, bold=bool(block.get("bold")))
        return max(34, len(lines) * 19 + 12)
    if kind == "kv":
        label_lines = wrap(block.get("label", ""), 16)
        value_lines = wrap(block.get("value", ""), 18)
        for index, line in enumerate(label_lines):
            svg.text(x, y + 18 + index * 18, line, 12, color=theme["subtext"])
        for index, line in enumerate(value_lines):
            svg.text(x + width, y + 18 + index * 18, line, 13, bold=True, anchor="end")
        return max(38, max(len(label_lines), len(value_lines)) * 18 + 12)
    if kind == "scale":
        svg.text(x, y + 17, block.get("label", ""), 13, bold=True)
        values = [str(value) for value in block.get("values", [1, 2, 3, 4, 5])]
        selected = str(block.get("selected", ""))
        gap = min(44, (width - 12) // max(1, len(values)))
        start = x + width - gap * len(values)
        for index, value in enumerate(values):
            cx = start + index * gap + gap / 2
            active = value == selected
            svg.parts.append(
                f'<circle cx="{cx}" cy="{y + 43}" r="14" '
                f'fill="{theme["accent"] if active else theme["background"]}" '
                f'stroke="{theme["accent"] if active else theme["line"]}"/>'
            )
            svg.text(cx, y + 48, value, 12, anchor="middle",
                     color=theme["background"] if active else theme["text"])
        return 72
    if kind == "progress":
        value = block.get("value", 0)
        if not isinstance(value, (int, float)) or not 0 <= value <= 100:
            raise ValueError("progress.value must be between 0 and 100")
        svg.text(x, y + 18, block.get("label", "进度"), 12, color=theme["subtext"])
        svg.text(x + width, y + 18, f"{value:g}%", 12, bold=True, anchor="end")
        svg.rect(x, y + 32, width, 10, fill=theme["disabled"], stroke=theme["disabled"], radius=5)
        if value:
            svg.rect(x, y + 32, width * value / 100, 10,
                     fill=theme["accent"], stroke=theme["accent"], radius=5)
        if block.get("caption"):
            svg.text(x, y + 60, block["caption"], 11, color=theme["subtext"])
        return 66
    if kind == "chips":
        svg.text(x, y + 17, block.get("label", ""), 12, color=theme["subtext"])
        selected = {str(item) for item in block.get("selected", [])}
        rows = chip_rows(block.get("items", []), width)
        for row_index, row in enumerate(rows):
            cursor = x
            for item, chip_width in row:
                active = item in selected
                fill = theme["accent"] if active else theme["block"]
                cy = y + 29 + row_index * 36
                svg.rect(cursor, cy, chip_width, 28, fill=fill,
                         stroke=theme["accent"] if active else theme["line"], radius=14)
                svg.text(cursor + chip_width / 2, cy + 19, item, 11, anchor="middle",
                         color=theme["background"] if active else theme["text"])
                cursor += chip_width + 8
        return 34 + max(1, len(rows)) * 36
    if kind == "tabs":
        items = [str(item) for item in block.get("items", [])]
        selected = str(block.get("selected", items[0] if items else ""))
        columns = min(3, len(items))
        gap = 8
        item_width = (width - gap * (columns - 1)) / max(1, columns)
        for index, item in enumerate(items):
            row, column = divmod(index, columns)
            left = x + column * (item_width + gap)
            top = y + row * 42
            active = item == selected
            svg.rect(left, top, item_width, 32,
                     fill=theme["accent"] if active else theme["background"],
                     stroke=theme["accent"] if active else theme["line"], radius=6)
            svg.text(left + item_width / 2, top + 21, item, 11, anchor="middle",
                     color=theme["background"] if active else theme["subtext"])
        rows = max(1, (len(items) + columns - 1) // columns)
        return rows * 42 + 8
    if kind == "card":
        height = block_height(block, width) - 12
        svg.rect(x, y + 4, width, height, fill=theme["background"], radius=10)
        cursor = y + 29
        title_lines = wrap(block.get("title", ""), max(12, width // 14))
        for index, line in enumerate(title_lines):
            svg.text(x + 14, cursor + index * 19, line, 13, bold=True)
        cursor += len(title_lines) * 19 + 4
        if block.get("body"):
            for line in wrap(block.get("body", ""), max(12, width // 14)):
                svg.text(x + 14, cursor, line, 11, color=theme["subtext"])
                cursor += 18
        for field in block.get("fields", []):
            if not isinstance(field, dict):
                continue
            svg.text(x + 14, cursor, field.get("label", ""), 11, color=theme["subtext"])
            svg.text(x + width - 14, cursor, field.get("value", ""), 12, anchor="end")
            cursor += 22
        if block.get("action"):
            action_width = min(132, max(88, len(str(block["action"])) * 14 + 28))
            left = x + width - action_width - 14
            svg.rect(left, y + height - 42, action_width, 32,
                     fill=theme["accent"], stroke=theme["accent"], radius=16)
            svg.text(left + action_width / 2, y + height - 21, block["action"], 11,
                     anchor="middle", color=theme["background"], bold=True)
        return height + 12
    if kind == "annotation":
        lines = wrap(block.get("text", ""), max(12, width // 14))
        height = 30 + max(20, len(lines) * 18)
        svg.rect(x, y + 4, width, height, fill=theme["background"],
                 stroke=theme["accent"], radius=8, dash=True)
        svg.text(x + 12, y + 25, block.get("label", "注释"), 11, bold=True)
        for index, line in enumerate(lines):
            svg.text(x + 12, y + 46 + index * 18, line, 11, color=theme["subtext"])
        return height + 14
    if kind == "input":
        svg.text(x, y + 17, block.get("label", ""), 12, color=theme["subtext"])
        content = block.get("value", block.get("placeholder", ""))
        lines = wrap(content, max(12, width // 14)) if block.get("multiline") else [str(content)]
        height = max(38, len(lines) * 18 + 20)
        svg.rect(x, y + 26, width, height, fill=theme["background"])
        value = block.get("value")
        for index, line in enumerate(lines):
            svg.text(x + 12, y + 50 + index * 18, line, 12,
                     color=theme["text"] if value is not None else theme["subtext"])
        return 44 + height
    if kind == "button":
        enabled = block.get("enabled", True)
        style = block.get("style", "primary")
        if not enabled:
            fill, stroke, text_color = theme["disabled"], theme["disabled"], theme["subtext"]
        elif style == "secondary":
            fill, stroke, text_color = theme["background"], theme["line"], theme["text"]
        else:
            fill, stroke, text_color = theme["accent"], theme["accent"], theme["background"]
        svg.rect(x, y + 6, width, 40, fill=fill, stroke=stroke)
        svg.text(x + width / 2, y + 32, block.get("text", "按钮"), 13,
                 color=text_color, anchor="middle", bold=True)
        return 54
    if kind == "state":
        lines = wrap(block.get("body", ""), max(12, width // 14))
        height = 38 + max(24, len(lines) * 18)
        svg.rect(x, y + 4, width, height, fill=theme["block"], dash=True)
        svg.text(x + 12, y + 27, block.get("title", "状态"), 13, bold=True)
        for index, line in enumerate(lines):
            svg.text(x + 12, y + 49 + index * 18, line, 11, color=theme["subtext"])
        return height + 16
    raise ValueError(f"unsupported block: {kind}")


def render(data: dict[str, Any], theme: dict[str, str]) -> str:
    boards = data["boards"]
    columns = int(data.get("columns", min(3, len(boards))))
    board_width = int(data.get("board_width", 390))
    requested_height = data.get("board_height")
    gap_x, gap_y, margin = 90, 100, 50
    inner_width = board_width - 44
    required_heights: list[int] = []
    for board in boards:
        content_height = 84 if board.get("nav") else 36
        content_height += sum(block_height(block, inner_width) for block in board.get("blocks", []))
        required_heights.append(content_height + 20)
    default_minimum_height = 360 if data.get("delivery_role") == "inline" else 520
    minimum_height = max(int(data.get("min_board_height", default_minimum_height)), max(required_heights))
    if requested_height is not None and int(requested_height) < minimum_height:
        raise ValueError(
            f"board_height {requested_height} is too small; at least {minimum_height} is required"
        )
    board_height = int(requested_height) if requested_height is not None else minimum_height
    explicit_layout = all(isinstance(board.get("layout"), dict) for board in boards)
    if explicit_layout:
        columns = max(int(board["layout"]["column"]) for board in boards) + 1
        rows = max(int(board["layout"]["row"]) for board in boards) + 1
    else:
        rows = (len(boards) + columns - 1) // columns
    canvas_width = margin * 2 + columns * board_width + (columns - 1) * gap_x
    board_start_y = 130
    canvas_height = board_start_y + rows * board_height + (rows - 1) * gap_y + margin
    if data.get("delivery_role") == "inline":
        target_width = int(data.get("target_width", 1000))
        scale = min(1.0, target_width / canvas_width)
        scaled_min_font = 11 * scale
        scaled_height = canvas_height * scale
        min_font = float(data.get("min_inline_font_size", 9))
        max_height = int(data.get("max_inline_height", 1800))
        if scaled_min_font < min_font:
            raise ValueError(
                f"inline board would render text at {scaled_min_font:.1f}px within {target_width}px; "
                "split it into focused storyboards or mark it zoomable"
            )
        if scaled_height > max_height:
            raise ValueError(
                f"inline board would be {scaled_height:.0f}px tall within {target_width}px; "
                "split it into focused storyboards or mark it zoomable"
            )
    svg = Svg(canvas_width, canvas_height, theme)
    svg.text(margin, 42, data.get("title", "页面交互画布"), 24, bold=True)
    svg.text(margin, 70, data.get("subtitle", "结构示意，不代表最终布局"), 13, color=theme["subtext"])
    positions: dict[str, tuple[int, int]] = {}
    for index, board in enumerate(boards):
        if explicit_layout:
            col, row = int(board["layout"]["column"]), int(board["layout"]["row"])
        else:
            col, row = index % columns, index // columns
        x = margin + col * (board_width + gap_x)
        y = board_start_y + row * (board_height + gap_y)
        positions[board["id"]] = (x, y)
        title_x = x
        if board.get("step") is not None:
            svg.parts.append(
                f'<circle cx="{x + 13}" cy="{y - 21}" r="13" fill="{theme["accent"]}"/>'
            )
            svg.text(x + 13, y - 16, board["step"], 12,
                     color=theme["background"], anchor="middle", bold=True)
            title_x = x + 34
        svg.text(title_x, y - 16, board["title"], 16, bold=True)
        if board.get("subtitle"):
            svg.text(x + board_width, y - 16, board["subtitle"], 11, color=theme["subtext"], anchor="end")
        device = board.get("device", "mobile")
        radius = 24 if device == "mobile" else 10
        svg.rect(x, y, board_width, board_height, fill=theme["background"], stroke=theme["accent"], radius=radius)
        inner_x, cursor = x + 22, y + 36
        if board.get("nav"):
            svg.text(x + board_width / 2, cursor, board["nav"], 15, bold=True, anchor="middle")
            cursor += 30
            svg.line(inner_x, cursor, inner_x + inner_width, cursor)
            cursor += 18
        for block in board.get("blocks", []):
            height = render_block(svg, block, inner_x, cursor, inner_width)
            cursor += height
        if cursor > y + board_height - 20:
            raise ValueError(f'board {board["id"]} content exceeds the calculated canvas')

    def segment_crosses_board(
        start: tuple[float, float], end: tuple[float, float], board_x: float, board_y: float
    ) -> bool:
        x1, y1 = start
        x2, y2 = end
        left, right = board_x + 2, board_x + board_width - 2
        top, bottom = board_y + 2, board_y + board_height - 2
        if math.isclose(y1, y2):
            return top < y1 < bottom and max(min(x1, x2), left) < min(max(x1, x2), right)
        if math.isclose(x1, x2):
            return left < x1 < right and max(min(y1, y2), top) < min(max(y1, y2), bottom)
        return False

    for link in data.get("links", []):
        fx, fy = positions[link["from"]]
        tx, ty = positions[link["to"]]
        horizontal = abs(tx - fx) >= abs(ty - fy)
        if horizontal and tx > fx:
            x1, y1, x2, y2 = fx + board_width + 8, fy + board_height / 2, tx - 8, ty + board_height / 2
        elif horizontal:
            x1, y1, x2, y2 = fx - 8, fy + board_height / 2, tx + board_width + 8, ty + board_height / 2
        elif ty > fy:
            x1, y1, x2, y2 = fx + board_width / 2, fy + board_height + 8, tx + board_width / 2, ty - 8
        else:
            x1, y1, x2, y2 = fx + board_width / 2, fy - 8, tx + board_width / 2, ty + board_height + 8
        if math.isclose(x1, x2) or math.isclose(y1, y2):
            points = [(x1, y1), (x2, y2)]
        elif horizontal:
            middle = (x1 + x2) / 2
            points = [(x1, y1), (middle, y1), (middle, y2), (x2, y2)]
        else:
            middle = (y1 + y2) / 2
            points = [(x1, y1), (x1, middle), (x2, middle), (x2, y2)]
        for board_id, (board_x, board_y) in positions.items():
            if board_id in {link["from"], link["to"]}:
                continue
            if any(
                segment_crosses_board(points[index], points[index + 1], board_x, board_y)
                for index in range(len(points) - 1)
            ):
                raise ValueError(
                    f'link {link["from"]}->{link["to"]} crosses board {board_id}; '
                    "provide an explicit layout or split the storyboard"
                )
        svg.polyline(points, arrow=True, dash=link.get("kind") in {"retry", "reentry", "return"})
        if link.get("label"):
            label_x, label_y = (x1 + x2) / 2, (y1 + y2) / 2 - 8
            svg.rect(label_x - max(38, len(link["label"]) * 6), label_y - 15,
                     max(76, len(link["label"]) * 12), 22,
                     fill=theme["canvas"], stroke=theme["canvas"], radius=4)
            svg.text(label_x, label_y, link["label"], 12, color=theme["subtext"], anchor="middle")
    return svg.finish()


def export_png(svg_path: Path, png_path: Path) -> str:
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", str(svg_path), "-o", str(png_path)], check=True)
        return "rsvg-convert"
    if shutil.which("magick"):
        subprocess.run(["magick", str(svg_path), str(png_path)], check=True)
        return "ImageMagick"
    node = shutil.which("node")
    helper = Path(__file__).with_name("render_svg_png.cjs")
    if node and helper.is_file():
        env = dict(__import__("os").environ)
        bundled_modules = (
            Path.home()
            / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
        )
        if bundled_modules.is_dir() and not env.get("NODE_PATH"):
            env["NODE_PATH"] = str(bundled_modules)
        result = subprocess.run(
            [node, str(helper), str(svg_path), str(png_path)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode == 0:
            return "sharp"
    raise RuntimeError(
        "PNG renderer unavailable; keep the SVG or provide rsvg-convert, ImageMagick, or Node sharp"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--theme", type=Path)
    parser.add_argument("--png", type=Path)
    args = parser.parse_args()
    try:
        data = load_json(args.spec)
        errors = validate(data)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 2
        theme = dict(DEFAULT_THEME)
        if args.theme:
            theme.update(load_json(args.theme))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render(data, theme), encoding="utf-8")
        print(f"Rendered SVG: {args.out}")
        if args.png:
            args.png.parent.mkdir(parents=True, exist_ok=True)
            renderer = export_png(args.out, args.png)
            print(f"Rendered PNG with {renderer}: {args.png}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

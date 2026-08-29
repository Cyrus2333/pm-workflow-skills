#!/usr/bin/env python3
"""Create a self-contained annotated SVG/PNG from a reference screenshot."""

from __future__ import annotations

import argparse
import base64
import html
import json
import struct
import sys
from pathlib import Path
from typing import Any

from render_wireframe_board import export_png


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


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


def image_size(path: Path) -> tuple[int, int, str]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return width, height, "image/png"
    if data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            length = struct.unpack(">H", data[index:index + 2])[0]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height, width = struct.unpack(">HH", data[index + 3:index + 7])
                return width, height, "image/jpeg"
            index += length
    raise ValueError("only PNG and JPEG screenshots are supported")


def validate(data: dict[str, Any], spec_path: Path) -> tuple[list[str], Path | None]:
    errors: list[str] = []
    if not str(data.get("title", "")).strip():
        errors.append("title is required")
    image_value = data.get("image")
    image_path: Path | None = None
    if not isinstance(image_value, str) or not image_value.strip():
        errors.append("image is required")
    else:
        image_path = Path(image_value)
        if not image_path.is_absolute():
            image_path = spec_path.parent / image_path
        if not image_path.is_file():
            errors.append(f"image does not exist: {image_path}")
    if data.get("role") not in {"current_ui", "confirmed_design", "visual_reference"}:
        errors.append("role must be current_ui, confirmed_design, or visual_reference")
    if data.get("sensitive_data") not in {"checked", "redacted", "not_applicable"}:
        errors.append("sensitive_data must be checked, redacted, or not_applicable")
    annotations = data.get("annotations")
    if not isinstance(annotations, list) or not annotations:
        errors.append("annotations must be a non-empty array")
    else:
        ids: list[str] = []
        for index, annotation in enumerate(annotations):
            if not isinstance(annotation, dict):
                errors.append(f"annotations[{index}] must be an object")
                continue
            if not str(annotation.get("id", "")).strip():
                errors.append(f"annotations[{index}].id is required")
            else:
                ids.append(annotation["id"])
            if annotation.get("kind") not in {"observed", "inferred", "unknown"}:
                errors.append(f"annotations[{index}].kind is unsupported")
            if not str(annotation.get("label", "")).strip():
                errors.append(f"annotations[{index}].label is required")
            if not str(annotation.get("description", "")).strip():
                errors.append(f"annotations[{index}].description is required")
            for field in ("x", "y", "width", "height"):
                value = annotation.get(field)
                if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                    errors.append(f"annotations[{index}].{field} must be between 0 and 1")
            if all(isinstance(annotation.get(field), (int, float)) for field in ("x", "y", "width", "height")):
                if annotation["x"] + annotation["width"] > 1 or annotation["y"] + annotation["height"] > 1:
                    errors.append(f"annotations[{index}] rectangle exceeds image bounds")
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            errors.append("duplicate annotation ids: " + ", ".join(duplicates))
    return errors, image_path


def render(data: dict[str, Any], image_path: Path) -> str:
    source_width, source_height, mime = image_size(image_path)
    max_image_width = int(data.get("max_image_width", 820))
    max_image_height = int(data.get("max_image_height", 980))
    scale = min(max_image_width / source_width, max_image_height / source_height, 1.0)
    image_width = max(1, round(source_width * scale))
    image_height = max(1, round(source_height * scale))
    margin = 48
    title_height = 84
    legend_width = 440
    gap = 40
    annotations = data["annotations"]
    legend_heights: list[int] = []
    for item in annotations:
        lines = wrap(item["description"], 25)
        legend_heights.append(52 + len(lines) * 23)
    legend_height = sum(legend_heights) + max(0, len(annotations) - 1) * 14
    content_height = max(image_height, legend_height)
    canvas_width = margin * 2 + image_width + gap + legend_width
    canvas_height = title_height + content_height + margin
    image_x = margin
    image_y = title_height
    legend_x = image_x + image_width + gap
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{margin}" y="42" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="24" font-weight="600" fill="#111111">{esc(data["title"])}</text>',
        f'<text x="{margin}" y="67" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="13" fill="#595959">角色：{esc(data["role"])} · 观察与推断分开记录</text>',
        f'<rect x="{image_x - 1}" y="{image_y - 1}" width="{image_width + 2}" height="{image_height + 2}" fill="#ffffff" stroke="#bfbfbf"/>',
        f'<image x="{image_x}" y="{image_y}" width="{image_width}" height="{image_height}" href="data:{mime};base64,{encoded}" preserveAspectRatio="none"/>',
    ]
    colors = {"observed": "#262626", "inferred": "#8c5a00", "unknown": "#8c8c8c"}
    labels = {"observed": "可观察", "inferred": "推断", "unknown": "未知"}
    cursor = image_y
    for number, item in enumerate(annotations, start=1):
        color = colors[item["kind"]]
        x = image_x + item["x"] * image_width
        y = image_y + item["y"] * image_height
        width = item["width"] * image_width
        height = item["height"] * image_height
        parts.extend([
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="none" stroke="{color}" stroke-width="3"/>',
            f'<circle cx="{x + 13}" cy="{y + 13}" r="13" fill="{color}"/>',
            f'<text x="{x + 13}" y="{y + 18}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">{number}</text>',
        ])
        row_height = legend_heights[number - 1]
        parts.extend([
            f'<rect x="{legend_x}" y="{cursor}" width="{legend_width}" height="{row_height}" rx="10" fill="#fafafa" stroke="#d9d9d9"/>',
            f'<circle cx="{legend_x + 24}" cy="{cursor + 25}" r="13" fill="{color}"/>',
            f'<text x="{legend_x + 24}" y="{cursor + 30}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">{number}</text>',
            f'<text x="{legend_x + 48}" y="{cursor + 25}" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="15" font-weight="600" fill="#111111">{esc(item["label"])}</text>',
            f'<text x="{legend_x + legend_width - 18}" y="{cursor + 25}" text-anchor="end" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="12" fill="{color}">{labels[item["kind"]]}</text>',
        ])
        for line_index, line in enumerate(wrap(item["description"], 25)):
            parts.append(
                f'<text x="{legend_x + 48}" y="{cursor + 53 + line_index * 23}" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="14" fill="#595959">{esc(line)}</text>'
            )
        cursor += row_height + 14
    parts.append("</svg>")
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--png", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.spec.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("spec root must be an object")
        errors, image_path = validate(data, args.spec)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 2
        assert image_path is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render(data, image_path), encoding="utf-8")
        print(f"Rendered annotated SVG: {args.out}")
        if args.png:
            args.png.parent.mkdir(parents=True, exist_ok=True)
            renderer = export_png(args.out, args.png)
            print(f"Rendered annotated PNG with {renderer}: {args.png}")
        return 0
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

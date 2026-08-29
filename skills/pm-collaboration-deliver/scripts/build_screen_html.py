#!/usr/bin/env python3
"""Build a key-page storyboard (numbered mobile screens) as HTML + PNG.

Input spec (see assets/mobile-screen-storyboard-template.json):

{
  "kind": "mobile_screen_storyboard",
  "title": "...", "subtitle": "结构示意：内容与状态为已确认方案，视觉以设计稿为准",
  "columns": 3,
  "screens": [
    {"id": "msg", "step": "1", "title": "站内消息", "nav": "学习小助手",
     "caption": "这一步读者要知道什么",
     "blocks": [ ... mobile_screen_kit blocks ... ]}
  ],
  "links": [{"from": "msg", "to": "plan", "label": "点击查看调整方案"}]
}

Screens render with the shared mobile_screen_kit component vocabulary: real
decided copy, decided states, banners/disabled buttons for rules — never
placeholder prompts or dashed "TBD" boxes.

    python3 scripts/build_screen_html.py \
        --spec /abs/storyboard.json \
        --html /abs/storyboard.html \
        --png /abs/storyboard.png

Exit codes: 0 ok, 2 spec / render failure.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from mobile_screen_kit import SCREEN_H, SCREEN_W, esc, page_html, render_screen

GAP_X = 104       # room for the arrow + wrapped label between screens
GAP_Y = 64
MARGIN = 48
HEAD_H = 96
LABEL_H = 34      # step + title above the phone
CAPTION_H = 40    # caption below the phone

BOARD_CSS = f"""
.board {{ padding: 0 {MARGIN}px {MARGIN}px; }}
.board-head {{ padding: 34px 0 22px; }}
.board-head h1 {{ font-size: 22px; font-weight: 700; letter-spacing: .2px; }}
.board-head p {{ font-size: 12.5px; color: var(--sub); margin-top: 6px; }}
.board-grid {{ position: relative; }}
.cell {{ position: absolute; }}
.cell .cell-head {{ display: flex; align-items: center; gap: 8px; height: {LABEL_H}px; }}
.cell .step {{ width: 22px; height: 22px; border-radius: 50%; background: var(--primary);
  color: var(--primary-text); font-size: 12px; font-weight: 700; display: flex;
  align-items: center; justify-content: center; flex: none; }}
.cell .cell-title {{ font-size: 14.5px; font-weight: 600; }}
.cell .caption {{ font-size: 12px; color: var(--sub); line-height: 1.55;
  width: {SCREEN_W}px; padding: 8px 2px 0; height: {CAPTION_H}px; }}
.edge-layer {{ position: absolute; inset: 0; pointer-events: none; }}
"""


def load_spec(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    screens = data.get("screens")
    if not isinstance(screens, list) or not screens:
        raise ValueError("spec requires a non-empty screens array")
    ids = [s.get("id") for s in screens]
    if len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("screen ids must be unique and non-empty")
    known = set(ids)
    for link in data.get("links", []):
        if link.get("from") not in known or link.get("to") not in known:
            raise ValueError(f"link references unknown screen: {link}")
    return data


def build(spec: dict) -> tuple[str, int, int]:
    screens = spec["screens"]
    columns = max(1, int(spec.get("columns", 3)))
    rows = (len(screens) + columns - 1) // columns
    cell_w = SCREEN_W + GAP_X
    cell_h = LABEL_H + SCREEN_H + CAPTION_H
    width = MARGIN * 2 + columns * SCREEN_W + (columns - 1) * GAP_X
    height = HEAD_H + rows * cell_h + (rows - 1) * (GAP_Y - CAPTION_H) + 12

    # grid position per screen
    pos: dict[str, tuple[int, int]] = {}
    for index, screen in enumerate(screens):
        col, row = index % columns, index // columns
        pos[screen["id"]] = (col, row)

    cells: list[str] = []
    for index, screen in enumerate(screens):
        col, row = pos[screen["id"]]
        x = MARGIN + col * cell_w
        y = HEAD_H + row * (cell_h + GAP_Y - CAPTION_H)
        step = screen.get("step")
        badge = f'<div class="step">{esc(step)}</div>' if step is not None else ""
        caption = (f'<div class="caption">{esc(screen["caption"])}</div>'
                   if screen.get("caption") else "")
        cells.append(
            f'<div class="cell" style="left:{x}px;top:{y}px">'
            f'<div class="cell-head">{badge}<div class="cell-title">'
            f'{esc(screen.get("title", screen["id"]))}</div></div>'
            f'{render_screen(screen)}{caption}</div>')

    # arrows for links between horizontally adjacent screens
    arrows: list[str] = []
    for link in spec.get("links", []):
        (c1, r1), (c2, r2) = pos[link["from"]], pos[link["to"]]
        if not (r1 == r2 and c2 == c1 + 1):
            continue  # non-adjacent transitions stay in captions / the overview board
        x1 = MARGIN + c1 * cell_w + SCREEN_W + 8
        x2 = MARGIN + c2 * cell_w - 8
        y = HEAD_H + r1 * (cell_h + GAP_Y - CAPTION_H) + LABEL_H + SCREEN_H / 2
        label = str(link.get("label", ""))
        label_html = ""
        if label:
            lines = [label[i:i + 5] for i in range(0, len(label), 5)][:3]
            tspans = "".join(
                f'<tspan x="{(x1 + x2) / 2}" dy="{0 if i == 0 else 13}">{esc(line)}</tspan>'
                for i, line in enumerate(lines))
            label_html = (f'<text x="{(x1 + x2) / 2}" y="{y - 12 - 13 * (len(lines) - 1)}" '
                          f'text-anchor="middle" font-size="11" fill="var(--sub)">{tspans}</text>')
        arrows.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2 - 8}" y2="{y}" stroke="var(--primary)" '
            f'stroke-width="1.8" marker-end="url(#sb-arrow)"/>{label_html}')

    body = f"""
<div class="board">
  <div class="board-head"><h1>{esc(spec.get("title", "关键页面"))}</h1>
  <p>{esc(spec.get("subtitle", "结构示意：内容与状态为已确认方案，视觉以设计稿为准"))}</p></div>
  <div class="board-grid" style="width:{width - 2 * MARGIN}px;height:{height - HEAD_H}px">
    <svg class="edge-layer" width="{width - 2 * MARGIN}" height="{height - HEAD_H}">
      <defs><marker id="sb-arrow" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5"
        orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="var(--primary)"/></marker></defs>
      {''.join(arrows)}
    </svg>
    {''.join(cells)}
  </div>
</div>"""
    html_text = page_html(spec.get("title", "关键页面"), body, width, height)
    html_text = html_text.replace("</style>", BOARD_CSS + "\n</style>", 1)
    return html_text, width, height


def export_png(html_path: Path, png_path: Path, width: int, height: int, scale: float) -> str:
    helper = Path(__file__).with_name("capture_html_png.py")
    result = subprocess.run(
        [sys.executable, str(helper), "--html", str(html_path), "--png", str(png_path),
         "--width", str(width), "--height", str(height), "--scale", f"{scale:g}"],
        capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "png capture failed")
    return "headless-browser"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--scale", type=float, default=2.0)
    args = parser.parse_args()
    try:
        spec = load_spec(args.spec)
        html_text, width, height = build(spec)
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(html_text, encoding="utf-8")
        print(f"Rendered HTML ({width}x{height}): {args.html}")
        if args.png:
            renderer = export_png(args.html, args.png, width, height, args.scale)
            print(f"Rendered PNG with {renderer}: {args.png}")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

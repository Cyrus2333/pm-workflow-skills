#!/usr/bin/env python3
"""Render a page interaction overview (页面交互总览) as HTML + PNG + pure SVG.

Consumes the same page-interaction-overview mapping spec that
check_page_interaction_overview.py validates — cards stay mapped to
interaction-model states and connectors to transitions, so the visual can
never drift from the model.

What makes this an aggregated overview instead of a scattered card field:

- main path first: primary connectors from the entry form one continuous
  horizontal reading line on the top row;
- alternates hang below their divergence point; exception / blocked results
  collect on a lower row; external exits sit in a light right lane;
- connector kinds are visually distinct: primary = dark solid, branch = gray
  solid, exception = red dashed, return = gray dashed (see the legend);
- layout_group values render as labeled bands behind their cards;
- every page card is a recognizable mini screen (task / key content /
  actions / feedback from the mapping spec's screen object), never a bare
  rounded rectangle with three lines of status text.

    python3 scripts/render_overview_board.py \
        --spec /abs/page-interaction-overview.json \
        --html /abs/overview.html \
        --png /abs/overview.png

A card may carry an optional explicit layout override:
"layout": {"column": 2, "row": 1}  — when every card has one, auto layout
is skipped entirely (escape hatch for hand-tuned boards).

Exit codes: 0 ok, 2 spec / render failure.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from mobile_screen_kit import SCREEN_H, SCREEN_W, esc, page_html, render_screen

MINI = 0.5                       # card screens render at half scale
CARD_W = round(SCREEN_W * MINI)          # 195
CARD_H = round(SCREEN_H * MINI)          # 422
HEAD = 30                        # card title row above the frame
COL_GAP = 132                    # room for edge labels between columns
ROW_GAP = 150                   # strip lanes live in this gap between rows
MARGIN = 56
TITLE_H = 108
LANE_GAP = 44                    # extra gap before the external exit lane

EDGE_CLASS = {
    "primary": "e-primary",
    "branch": "e-branch",
    "exception": "e-exception",
    "return": "e-return",
    "external": "e-branch",
}

BOARD_CSS = f"""
.ov-board {{ position: relative; }}
.ov-head {{ position: absolute; left: {MARGIN}px; top: 30px; }}
.ov-head h1 {{ font-size: 22px; font-weight: 700; }}
.ov-head p {{ font-size: 12.5px; color: var(--sub); margin-top: 6px; }}
.ov-legend {{ position: absolute; right: {MARGIN}px; top: 38px; display: flex;
  gap: 16px; font-size: 11.5px; color: var(--sub); align-items: center; }}
.ov-legend .lg {{ display: flex; align-items: center; gap: 6px; }}
.ov-legend .sw {{ width: 26px; border-top: 2.4px solid var(--primary); }}
.ov-legend .sw.branch {{ border-top-width: 1.6px; border-color: #5f5f5f; }}
.ov-legend .sw.exception {{ border-top: 1.6px dashed #9a3b3b; }}
.ov-legend .sw.return {{ border-top: 1.4px dashed #8a8a8a; }}
.ov-band {{ position: absolute; background: #f7f7f8; border: 1px solid #e6e7ea;
  border-radius: 16px; }}
.ov-band .band-title {{ position: absolute; top: 10px; left: 16px; font-size: 12px;
  font-weight: 600; color: var(--sub); }}
.ov-card {{ position: absolute; }}
.ov-card .ov-title {{ font-size: 13.5px; font-weight: 600; height: {HEAD - 8}px;
  display: flex; align-items: center; gap: 7px; }}
.ov-card .kind-pill {{ font-size: 10px; font-weight: 600; color: var(--sub);
  background: var(--hairline); border-radius: 8px; padding: 2px 7px; }}
.ov-mini {{ width: {CARD_W}px; height: {CARD_H}px; overflow: hidden; border-radius: 22px;
  border: 1px solid #d7dae0; box-shadow: 0 1px 4px rgba(20,24,40,.05); background: #fff; }}
.ov-mini .scale-wrap {{ transform: scale({MINI}); transform-origin: top left;
  width: {SCREEN_W}px; height: {SCREEN_H}px; }}
.ov-mini .phone {{ border: none; border-radius: 0; box-shadow: none; }}
.ov-touch {{ width: {CARD_W}px; background: #fff; border: 1px solid var(--line);
  border-radius: 16px; padding: 14px 14px 12px;
  box-shadow: 0 1px 4px rgba(20,24,40,.05); }}
.ov-touch .t-dot {{ width: 9px; height: 9px; border-radius: 50%; background: var(--info);
  display: inline-block; margin-right: 6px; }}
.ov-touch .t-title {{ font-size: 13.5px; font-weight: 600; display: inline; }}
.ov-touch .t-line {{ font-size: 11.5px; color: var(--sub); line-height: 1.6; margin-top: 8px; }}
.ov-exit {{ width: 150px; border: 1.4px dashed #c6c9cf; border-radius: 12px;
  padding: 10px 12px; background: #fbfbfd; }}
.ov-exit .x-title {{ font-size: 12.5px; font-weight: 600; color: var(--sub); }}
.ov-exit .x-note {{ font-size: 10.5px; color: var(--faint); margin-top: 3px; line-height: 1.5; }}
.ov-sys {{ width: {CARD_W}px; border: 1px solid var(--line); background: var(--system-fill, #f2f3f5);
  border-radius: 12px; padding: 10px 14px; font-size: 12.5px; font-weight: 600;
  color: var(--sub); text-align: center; }}
.ov-chip {{ width: {CARD_W}px; border: 1px dashed var(--line); background: #f7f8fa;
  border-radius: 20px; padding: 9px 14px; font-size: 11.5px; font-weight: 500;
  color: var(--sub); text-align: center; }}
.edge-label {{ position: absolute; transform: translate(-50%, -50%);
  background: #fff; border: 1px solid var(--line); border-radius: 7px;
  font-size: 10.5px; color: var(--sub); padding: 2.5px 8px; white-space: pre-line;
  text-align: center; line-height: 1.5; pointer-events: none; z-index: 3; }}
svg.ov-edges {{ position: absolute; inset: 0; pointer-events: none; z-index: 2; }}
.ov-card, .ov-band {{ z-index: 1; }}
path.e-primary {{ stroke: #1f2329; stroke-width: 2.6; fill: none; }}
path.e-branch {{ stroke: #5f5f5f; stroke-width: 1.6; fill: none; }}
path.e-exception {{ stroke: #9a3b3b; stroke-width: 1.6; fill: none; stroke-dasharray: 7 5; }}
path.e-return {{ stroke: #8a8a8a; stroke-width: 1.4; fill: none; stroke-dasharray: 7 5; }}
"""


# ------------------------------------------------------------------ spec ---

def load_spec(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError("spec requires a non-empty cards array")
    ids = [c.get("id") for c in cards]
    if len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("card ids must be unique and non-empty")
    known = set(ids)
    for conn in data.get("connectors", []):
        if conn.get("from_card") not in known or conn.get("to_card") not in known:
            raise ValueError(f"connector references unknown card: {conn}")
    # Shared screen source: cards with screen_ref reuse the storyboard's screen
    # blocks so the overview can never drift from the key-page storyboard.
    data["_screens"] = {}
    source_value = data.get("screen_source")
    if isinstance(source_value, str) and source_value.strip():
        source_path = Path(source_value)
        if not source_path.is_absolute():
            source_path = path.parent / source_path
        if not source_path.is_file():
            raise ValueError(f"screen_source does not exist: {source_path}")
        source_data = json.loads(source_path.read_text(encoding="utf-8"))
        for screen in source_data.get("screens", []):
            if isinstance(screen, dict) and screen.get("id"):
                data["_screens"][screen["id"]] = screen
    return data


# ---------------------------------------------------------------- layout ---

class BoardLayout:
    """Main-path-first grid layout.

    Row 0 is the continuous main path. Alternates and exceptions hang below
    their divergence point. External exits collect in a light right lane.
    """

    def __init__(self, spec: dict):
        self.cards = {c["id"]: dict(c) for c in spec["cards"]}
        self.conns = [dict(c) for c in spec.get("connectors", [])]
        self.pos: dict[str, tuple[int, int]] = {}   # id -> (col, row)
        self._place()

    def _primary_targets(self, cid: str) -> list[str]:
        return [c["to_card"] for c in self.conns
                if c["from_card"] == cid and c.get("kind", "primary") == "primary"]

    def _place(self):
        explicit = all(isinstance(c.get("layout"), dict) for c in self.cards.values())
        if explicit:
            for cid, card in self.cards.items():
                self.pos[cid] = (int(card["layout"]["column"]), int(card["layout"]["row"]))
            return
        in_deg = {cid: 0 for cid in self.cards}
        for c in self.conns:
            in_deg[c["to_card"]] = in_deg.get(c["to_card"], 0) + 1
        entries = [cid for cid, c in self.cards.items()
                   if c.get("kind") == "entry"] or [cid for cid, d in in_deg.items() if d == 0]
        externals = [cid for cid, c in self.cards.items() if c.get("kind") == "external"]

        # 1. main chain on row 0
        chain: list[str] = []
        start = entries[0]
        current = start
        while current and current not in chain:
            chain.append(current)
            nxt = [t for t in self._primary_targets(current)
                   if t not in chain and t not in externals]
            current = nxt[0] if nxt else None
        for col, cid in enumerate(chain):
            self.pos[cid] = (col, 0)

        # 2. BFS the rest: alternates below their source's column
        queue = list(chain)
        while queue:
            src = queue.pop(0)
            scol, srow = self.pos[src]
            for conn in self.conns:
                if conn["from_card"] != src:
                    continue
                dst = conn["to_card"]
                if dst in self.pos or dst in externals:
                    continue
                spot = self._find_free(scol, srow + 1)
                self.pos[dst] = spot
                queue.append(dst)
        # unconnected leftovers (e.g. secondary entries feeding the chain)
        for cid in self.cards:
            if cid not in self.pos and cid not in externals:
                self.pos[cid] = self._find_free(0, 1)

        # 3. external exits: right lane, ordered by source position (row, col)
        lane_col = max(c for c, _ in self.pos.values()) + 1 if self.pos else 0
        row_cursor: dict[int, None] = {}

        def src_key(cid):
            srcs = [c["from_card"] for c in self.conns if c["to_card"] == cid]
            pts = [self.pos[s] for s in srcs if s in self.pos]
            return min(pts) if pts else (99, 99)

        for cid in sorted(externals, key=src_key):
            row = 0
            while row in row_cursor:
                row += 1
            row_cursor[row] = None
            self.pos[cid] = (lane_col, row)
        self.has_lane = bool(externals)

    def _find_free(self, col: int, row: int) -> tuple[int, int]:
        taken = set(self.pos.values())
        while (col, row) in taken:
            col += 1
        return (col, row)


# ---------------------------------------------------------------- render ---

def card_blocks(card: dict, screens: dict) -> list[dict]:
    """Blocks for a page-like card: shared screen_ref first, then inline fields."""
    ref = card.get("screen_ref")
    if ref and ref in screens:
        return list(screens[ref].get("blocks", []))
    screen = card.get("screen") or {}
    if card.get("screen_blocks"):
        return list(card["screen_blocks"])
    blocks: list[dict] = []
    if screen.get("task"):
        blocks.append({"type": "text", "dim": True, "text": screen["task"]})
    if screen.get("key_content"):
        blocks.append({"type": "list",
                       "items": [{"title": k} for k in screen["key_content"][:3]]})
    actions = screen.get("actions", [])
    for i, action in enumerate(actions[:2]):
        blocks.append({"type": "button", "text": action,
                       "style": "primary" if i == 0 else "secondary"})
    feedback = str(screen.get("visible_feedback") or "").strip()
    if feedback and feedback not in {"无", "无反馈", "none", "None"}:
        blocks.append({"type": "banner", "tone": "info", "text": feedback})
    return blocks


def card_screen(card: dict, screens: dict) -> dict:
    """Full screen for a page-like card: blocks plus screen-level modal/toast.

    screen_ref takes the whole referenced screen (nav falls back to the card
    title so overview labeling wins); inline cards only carry blocks.
    """
    ref = card.get("screen_ref")
    if ref and ref in screens:
        s = screens[ref]
        screen = {"nav": card.get("title") or s.get("nav"),
                  "blocks": list(s.get("blocks", []))}
        if s.get("modal"):
            screen["modal"] = s["modal"]
        if s.get("toast"):
            screen["toast"] = s["toast"]
        return screen
    return {"nav": card.get("title"), "blocks": card_blocks(card, screens)}


def card_body_html(card: dict, screens: dict | None = None) -> str:
    kind = card.get("kind", "page")
    screen = card.get("screen") or {}
    title = card.get("title", card["id"])
    if kind == "external":
        note = esc(screen.get("task", "既有页面 / 本期不改动"))
        return (f'<div class="ov-exit"><div class="x-title">{esc(title)}</div>'
                f'<div class="x-note">{note}</div></div>')
    if kind == "system":
        return f'<div class="ov-sys">{esc(title)}</div>'
    if kind == "chip":
        # transient waypoint: slim bar with a waiting cue, never a page frame
        return f'<div class="ov-chip">⏳ {esc(title)}</div>'
    if kind == "entry":
        lines = "".join(f'<div class="t-line">· {esc(k)}</div>'
                        for k in screen.get("key_content", [])[:3])
        return f'<div class="ov-touch">{lines}</div>'
    # page / modal / result: recognizable mini screen
    inner = render_screen(card_screen(card, screens or {}), mini=True)
    return f'<div class="ov-mini"><div class="scale-wrap">{inner}</div></div>'


def geometry(layout: BoardLayout):
    """Absolute pixel rects per card: (x, y_visual_top, w, full_height).

    For page-like cards the rect starts at the title row (the phone frame sits
    HEAD px below); entry/system/external rects start at the element itself.
    Returns (rects, width, height).
    """
    lane_offset = LANE_GAP if layout.has_lane else 0
    cell_w = CARD_W + COL_GAP
    cell_h = CARD_H + HEAD + ROW_GAP
    rects: dict[str, tuple[float, float, float, float]] = {}
    max_right = max_bottom = 0.0
    lane_col = None
    if layout.has_lane:
        lane_col = max(c for c, _ in layout.pos.values())
    for cid, (col, row) in layout.pos.items():
        card = layout.cards[cid]
        kind = card.get("kind", "page")
        if kind == "external":
            w, h, yoff = 150, 64, float(HEAD)
        elif kind == "system":
            w, h, yoff = CARD_W, 40, float(HEAD)
        elif kind == "chip":
            # transient waypoint (loading/processing): slim bar, not a page
            w, h, yoff = CARD_W, 40, float(HEAD)
        elif kind == "entry":
            w, h, yoff = CARD_W, 96, float(HEAD)
        else:
            w, h, yoff = CARD_W, CARD_H + HEAD, 0.0
        x = MARGIN + col * cell_w + (lane_offset if lane_col is not None and col == lane_col else 0)
        y = TITLE_H + row * cell_h + yoff
        rects[cid] = (x, y, w, h)
        max_right = max(max_right, x + w)
        max_bottom = max(max_bottom, y + h)
    width = max_right + MARGIN
    height = max_bottom + MARGIN
    return rects, math.ceil(width), math.ceil(height)


def port(rect, side):
    x, y, w, h = rect
    return {
        "right": (x + w, y + h / 2),
        "left": (x, y + h / 2),
        "top": (x + w / 2, y),
        "bottom": (x + w / 2, y + h),
    }[side]


def ortho(p1, p2, via: str) -> list[tuple[float, float]]:
    if via == "h":   # exit right, enter left
        mx = (p1[0] + p2[0]) / 2
        return [p1, (mx, p1[1]), (mx, p2[1]), p2]
    if via == "v":   # exit bottom, enter top
        my = (p1[1] + p2[1]) / 2
        return [p1, (p1[0], my), (p2[0], my), p2]
    if via == "down-left":  # exit bottom, enter left
        return [p1, (p1[0], p2[1]), p2]
    return [p1, (p2[0], p1[1]), p2]


def rounded(points, radius=12.0):
    if len(points) < 3:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(1, len(points) - 1):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        d1 = math.hypot(x1 - x0, y1 - y0)
        d2 = math.hypot(x2 - x1, y2 - y1)
        r = min(radius, d1 / 2, d2 / 2)
        if r < 1:
            d += f" L{x1:.1f},{y1:.1f}"
            continue
        a = (x1 + (x0 - x1) / d1 * r, y1 + (y0 - y1) / d1 * r)
        b = (x1 + (x2 - x1) / d2 * r, y1 + (y2 - y1) / d2 * r)
        d += f" L{a[0]:.1f},{a[1]:.1f} Q{x1:.1f},{y1:.1f} {b[0]:.1f},{b[1]:.1f}"
    d += f" L{points[-1][0]:.1f},{points[-1][1]:.1f}"
    return d


def compute_bands(layout: BoardLayout, rects) -> list[tuple[float, float, float, float, str]]:
    """Group bands as (x, y, w, h, title); a band is dropped when it would
    swallow a non-member card (members not contiguous → band would mislead)."""
    bands: list[tuple[float, float, float, float, str]] = []
    groups: dict[str, list[str]] = {}
    for cid, card in layout.cards.items():
        if card.get("layout_group"):
            groups.setdefault(card["layout_group"], []).append(cid)
    for title, members in groups.items():
        if len(members) < 2:
            continue
        xs = [rects[m][0] for m in members]
        ys = [rects[m][1] for m in members]
        rs = [rects[m][0] + rects[m][2] for m in members]
        bs = [rects[m][1] + rects[m][3] for m in members]
        bx0, by0, bx1, by1 = min(xs) - 22, min(ys) - 32, max(rs) + 22, max(bs) + 24
        swallowed = False
        for cid in layout.cards:
            if cid in members:
                continue
            cx, cy, cw, ch = rects[cid]
            if cx < bx1 and cx + cw > bx0 and cy < by1 and cy + ch > by0:
                swallowed = True
                break
        if swallowed:
            continue
        bands.append((bx0, by0, bx1 - bx0, by1 - by0, title))
    return bands


def route_edges(layout: BoardLayout, rects, height: float):
    """Orthogonal edge routing shared by the HTML and pure-SVG emitters.

    Returns (routes, height) where routes are (conn, points, label_anchor,
    near_source) and height is extended to cover any strip lanes.
    """
    def row_bottom(row: int) -> float:
        return max((rects[c][1] + rects[c][3]
                    for c, (cc, rr) in layout.pos.items() if rr == row),
                   default=TITLE_H)

    def h_conflict(y: float, x_from: float, x_to: float, skip: set[str]) -> bool:
        lo, hi = min(x_from, x_to), max(x_from, x_to)
        for cid in layout.cards:
            if cid in skip:
                continue
            cx, cy, cw, ch = rects[cid]
            if cy - 6 <= y <= cy + ch + 6 and lo < cx + cw + 6 and hi > cx - 6:
                return True
        return False

    strip_fwd = 0   # forward strips between rows: offsets +24, +48, +72
    strip_bwd = 0   # backward strips between rows: offsets +96, +120
    routes: list[tuple[dict, list[tuple[float, float]], tuple[float, float], bool]] = []
    max_lane_y = 0.0

    for conn in layout.conns:
        a = rects[conn["from_card"]]
        b = rects[conn["to_card"]]
        (c1, r1), (c2, r2) = layout.pos[conn["from_card"]], layout.pos[conn["to_card"]]
        skip = {conn["from_card"], conn["to_card"]}
        near_source = False
        if conn.get("kind") == "external" or c2 > c1:
            p1, p2 = port(a, "right"), port(b, "left")
            mx = (p1[0] + p2[0]) / 2
            if c2 > c1 and not h_conflict(p1[1], p1[0], mx, skip) \
                    and not h_conflict(p2[1], mx, p2[0], skip):
                pts = [p1, (mx, p1[1]), (mx, p2[1]), p2]
            else:
                # cards in between (or external exit): drop to the strip below
                # the source row, ride it right, enter the target from the top
                p1, p2 = port(a, "bottom"), port(b, "top")
                strip_y = row_bottom(r1) + 24 + strip_fwd * 24
                strip_fwd += 1
                max_lane_y = max(max_lane_y, strip_y)
                pts = [p1, (p1[0], strip_y), (p2[0], strip_y), p2]
                near_source = True
        elif c2 == c1 and r2 > r1:
            pts = ortho(port(a, "bottom"), port(b, "top"), "v")
        elif c2 < c1 and r2 > r1:
            # down-left: ride the strip between the two rows
            p1, p2 = port(a, "bottom"), port(b, "top")
            strip_y = row_bottom(r1) + 24 + strip_fwd * 24
            strip_fwd += 1
            max_lane_y = max(max_lane_y, strip_y)
            pts = [p1, (p1[0], strip_y), (p2[0], strip_y), p2]
            near_source = True
        else:
            # backward / return / upward: strip below the lower of the two rows
            p1, p2 = port(a, "bottom"), port(b, "bottom")
            lane_y = row_bottom(max(r1, r2)) + 96 + strip_bwd * 26
            strip_bwd += 1
            max_lane_y = max(max_lane_y, lane_y)
            pts = [p1, (p1[0], lane_y), (p2[0], lane_y), p2]
            near_source = True
        # label anchor
        if near_source:
            at = (pts[0][0] + 14, pts[1][1])
        else:
            best, at = -1.0, pts[0]
            for i in range(len(pts) - 1):
                seg = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                if seg > best:
                    best = seg
                    at = ((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2)
        routes.append((conn, pts, at, near_source))

    height = math.ceil(max(height, max_lane_y + 26 + MARGIN))
    return routes, height


def render(spec: dict) -> tuple[str, int, int]:
    layout = BoardLayout(spec)
    rects, width, height = geometry(layout)

    # --- group bands ---
    bands: list[str] = []
    for bx0, by0, bw, bh, title in compute_bands(layout, rects):
        bands.append(
            f'<div class="ov-band" style="left:{bx0}px;top:{by0}px;'
            f'width:{bw}px;height:{bh}px">'
            f'<div class="band-title">{esc(title)}</div></div>')

    # --- edge routing ---
    routes, height = route_edges(layout, rects, height)

    edges_svg: list[str] = []
    labels: list[str] = []
    for conn, pts, at, near_source in routes:
        kind = conn.get("kind", "primary")
        cls = EDGE_CLASS.get(kind, "e-branch")
        marker = {"e-primary": "ov-arrow-p", "e-branch": "ov-arrow-b",
                  "e-exception": "ov-arrow-e", "e-return": "ov-arrow-r"}[cls]
        edges_svg.append(
            f'<path d="{rounded(pts)}" class="{cls}" marker-end="url(#{marker})"/>')
        label = str(conn.get("label", ""))
        if label:
            wrapped = "\n".join(label[i:i + 8] for i in range(0, len(label), 8))
            transform = "translate(0,-50%)" if near_source else "translate(-50%,-50%)"
            labels.append(
                f'<div class="edge-label" style="left:{at[0]:.1f}px;top:{at[1]:.1f}px;'
                f'transform:{transform}">{esc(wrapped)}</div>')

    cards_html: list[str] = []
    for cid, card in layout.cards.items():
        x, y, w, h = rects[cid]
        kind = card.get("kind", "page")
        pill = {"page": "页面", "modal": "弹层", "result": "结果", "entry": "触点",
                "system": "系统", "external": "出口"}.get(kind, kind)
        if kind in {"external", "system", "chip"}:
            cards_html.append(
                f'<div class="ov-card" style="left:{x}px;top:{y}px">'
                f'{card_body_html(card, spec.get("_screens"))}</div>')
        else:
            cards_html.append(
                f'<div class="ov-card" style="left:{x}px;top:{y}px">'
                f'<div class="ov-title"><span class="kind-pill">{pill}</span>'
                f'{esc(card.get("title", cid))}</div>'
                f'{card_body_html(card, spec.get("_screens"))}</div>')

    legend = (
        '<div class="ov-legend">'
        '<span class="lg"><span class="sw"></span>主路径</span>'
        '<span class="lg"><span class="sw branch"></span>分支</span>'
        '<span class="lg"><span class="sw exception"></span>异常 / 拦截</span>'
        '<span class="lg"><span class="sw return"></span>返回 / 重进</span>'
        '</div>')

    body = f"""
<div class="ov-board" style="width:{width}px;height:{height}px">
  <div class="ov-head"><h1>{esc(spec.get("title", "页面交互总览"))}</h1>
  <p>{esc(spec.get("subtitle", "页面卡片 + 带动作/条件的连线；与交互模型同源"))}</p></div>
  {legend}
  {''.join(bands)}
  <svg class="ov-edges" width="{width}" height="{height}">
    <defs>
      <marker id="ov-arrow-p" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#1f2329"/></marker>
      <marker id="ov-arrow-b" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#5f5f5f"/></marker>
      <marker id="ov-arrow-e" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#9a3b3b"/></marker>
      <marker id="ov-arrow-r" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#8a8a8a"/></marker>
    </defs>
    {''.join(edges_svg)}
  </svg>
  {''.join(cards_html)}
  {''.join(labels)}
</div>"""
    html_text = page_html(spec.get("title", "页面交互总览"), body, width, height)
    return html_text.replace("</style>", BOARD_CSS + "\n</style>", 1), width, height


# ------------------------------------------------------------- pure SVG ---
# The Feishu whiteboard SVG import keeps only native SVG primitives (verified:
# foreignObject content is dropped), so the rich aggregated board needs a
# pure-SVG emitter. It reuses BoardLayout / geometry / compute_bands /
# route_edges — same spec, same layout, same routes; only the paint differs.

SVG_FONT = "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"
_SVG_COLORS = {
    "ink": "#1f2329", "sub": "#646a73", "faint": "#8f959e",
    "line": "#e6e7ea", "hairline": "#eff0f1", "info": "#4f6bed",
    "info_fill": "#eef2ff", "exit_line": "#c6c9cf", "exit_fill": "#fbfbfd",
    "sys_fill": "#f2f3f5", "frame": "#d7dae0", "band": "#f7f7f8",
}
_SVG_EDGE = {
    "primary": ("#1f2329", 2.6, None),
    "branch": ("#5f5f5f", 1.6, None),
    "external": ("#5f5f5f", 1.6, None),
    "exception": ("#9a3b3b", 1.6, "7 5"),
    "return": ("#8a8a8a", 1.4, "7 5"),
}


def _n(v: float) -> str:
    return f"{v:.1f}"


def _wrap(text: str, per: int) -> list[str]:
    text = str(text)
    return [text[i:i + per] for i in range(0, len(text), per)] or [""]


def _t(x, y, text, size, fill, weight=400, anchor="start") -> str:
    return (f'<text x="{_n(x)}" y="{_n(y)}" font-size="{size}" fill="{fill}"'
            f' font-weight="{weight}" text-anchor="{anchor}">{esc(text)}</text>')


def _svg_blocks(blocks: list[dict], x: float, y: float, w: float, bottom: float) -> str:
    """Stack mini-screen blocks as SVG primitives inside the phone frame."""
    out: list[str] = []
    cx = x + 12
    cw = w - 24
    cur = y
    for block in blocks:
        if cur > bottom - 30:
            break
        btype = block.get("type")
        if btype == "text":
            for i, ln in enumerate(_wrap(block.get("text", ""), 17)):
                out.append(_t(cx, cur + 10, ln, 10, _SVG_COLORS["faint"]))
                cur += 14
            cur += 4
        elif btype == "list":
            for item in block.get("items", [])[:4]:
                out.append(f'<circle cx="{_n(cx + 3)}" cy="{_n(cur + 8)}" r="2" fill="{_SVG_COLORS["info"]}"/>')
                out.append(_t(cx + 11, cur + 11, str(item.get("title", ""))[:18], 10.5, _SVG_COLORS["ink"]))
                row_h = 21
                if item.get("note"):
                    out.append(_t(cx + 11, cur + 24, str(item["note"])[:20], 9, _SVG_COLORS["faint"]))
                    row_h = 33
                cur += row_h
                out.append(f'<line x1="{_n(cx)}" y1="{_n(cur - 5)}" x2="{_n(cx + cw)}" y2="{_n(cur - 5)}" stroke="{_SVG_COLORS["hairline"]}" stroke-width="1"/>')
            cur += 3
        elif btype == "button":
            primary = block.get("style", "primary") == "primary"
            fill = _SVG_COLORS["ink"] if primary else "#ffffff"
            stroke = "none" if primary else _SVG_COLORS["frame"]
            tfill = "#ffffff" if primary else _SVG_COLORS["ink"]
            out.append(f'<rect x="{_n(cx)}" y="{_n(cur)}" width="{_n(cw)}" height="24" rx="6" fill="{fill}" stroke="{stroke}"/>')
            out.append(_t(cx + cw / 2, cur + 16, str(block.get("text", ""))[:14], 10.5, tfill, 600, "middle"))
            cur += 31
        elif btype == "banner":
            lines = _wrap(block.get("text", ""), 17)
            bh = len(lines) * 14 + 8
            out.append(f'<rect x="{_n(cx)}" y="{_n(cur)}" width="{_n(cw)}" height="{bh}" rx="4" fill="{_SVG_COLORS["info_fill"]}"/>')
            for i, ln in enumerate(lines):
                out.append(_t(cx + 8, cur + 15 + i * 14, ln, 10, _SVG_COLORS["info"]))
            cur += bh + 7
        elif btype == "section":
            out.append(_t(cx + 2, cur + 11, str(block.get("title", ""))[:18], 10, _SVG_COLORS["sub"], 600))
            cur += 20
        elif btype in ("kv_group", "card"):
            fields = block.get("fields", [])
            rows = []
            if btype == "card" and block.get("title"):
                rows.append(("title", str(block["title"])))
            if btype == "card" and block.get("body"):
                rows.append(("body", str(block["body"])))
            rows.extend(("kv", f) for f in fields)
            if btype == "card" and block.get("action"):
                rows.append(("action", str(block["action"])))
            if rows:
                bh = len(rows) * 16 + 10
                out.append(f'<rect x="{_n(cx)}" y="{_n(cur)}" width="{_n(cw)}" height="{bh}" rx="6" fill="#f7f8fa"/>')
                ry = cur + 15
                for rkind, r in rows:
                    if rkind == "kv":
                        label = str(r.get("label", ""))[:8]
                        value = str(r.get("value", ""))[:13]
                        out.append(_t(cx + 8, ry, label, 9.5, _SVG_COLORS["faint"]))
                        out.append(_t(cx + cw - 8, ry, value, 9.5, _SVG_COLORS["ink"], 500, "end"))
                    elif rkind == "title":
                        out.append(_t(cx + 8, ry, r[:16], 10, _SVG_COLORS["ink"], 600))
                    elif rkind == "action":
                        out.append(_t(cx + 8, ry, r[:16], 9.5, _SVG_COLORS["info"], 600))
                    else:
                        out.append(_t(cx + 8, ry, r[:20], 9.5, _SVG_COLORS["sub"]))
                    ry += 16
                cur += bh + 7
        elif btype == "divider":
            out.append(f'<line x1="{_n(cx)}" y1="{_n(cur + 5)}" x2="{_n(cx + cw)}" y2="{_n(cur + 5)}" stroke="{_SVG_COLORS["hairline"]}" stroke-width="1"/>')
            cur += 11
        elif btype == "result":
            tone = block.get("tone", "success")
            ok = tone == "success"
            col = _SVG_COLORS["info"] if ok else "#d4380d"
            out.append(f'<circle cx="{_n(x + w / 2)}" cy="{_n(cur + 14)}" r="12" fill="{col}"/>')
            out.append(_t(x + w / 2, cur + 18, "✓" if ok else "!", 12, "#ffffff", 700, "middle"))
            cur += 32
            for i, ln in enumerate(_wrap(str(block.get("title", "")), 15)[:2]):
                out.append(_t(x + w / 2, cur + 11, ln, 11, _SVG_COLORS["ink"], 600, "middle"))
                cur += 15
            if block.get("body"):
                for ln in _wrap(str(block["body"]), 17)[:2]:
                    out.append(_t(x + w / 2, cur + 10, ln, 9.5, _SVG_COLORS["sub"], 400, "middle"))
                    cur += 13
            cur += 5
        elif btype == "empty":
            out.append(_t(x + w / 2, cur + 14, str(block.get("text", "暂无内容"))[:16], 10, _SVG_COLORS["faint"], 400, "middle"))
            cur += 26
        elif btype == "button_row":
            btns = block.get("buttons", [])[:2]
            bw = (cw - 8 * (len(btns) - 1)) / max(len(btns), 1)
            bx = cx
            for b in btns:
                primary = b.get("style", "primary") == "primary"
                fill = _SVG_COLORS["ink"] if primary else "#ffffff"
                stroke = "none" if primary else _SVG_COLORS["frame"]
                tfill = "#ffffff" if primary else _SVG_COLORS["ink"]
                out.append(f'<rect x="{_n(bx)}" y="{_n(cur)}" width="{_n(bw)}" height="24" rx="6" fill="{fill}" stroke="{stroke}"/>')
                out.append(_t(bx + bw / 2, cur + 16, str(b.get("text", ""))[:8], 10, tfill, 600, "middle"))
                bx += bw + 8
            cur += 31
        elif btype == "input":
            out.append(f'<rect x="{_n(cx)}" y="{_n(cur)}" width="{_n(cw)}" height="24" rx="6" fill="#ffffff" stroke="{_SVG_COLORS["frame"]}"/>')
            val = str(block.get("value") or block.get("placeholder", ""))
            out.append(_t(cx + 8, cur + 16, val[:16], 10, _SVG_COLORS["ink"] if block.get("value") else _SVG_COLORS["faint"]))
            cur += 31
        elif btype == "media":
            out.append(f'<rect x="{_n(cx)}" y="{_n(cur)}" width="{_n(cw)}" height="48" rx="6" fill="#f7f8fa" stroke="{_SVG_COLORS["hairline"]}"/>')
            out.append(_t(cx + cw / 2, cur + 28, str(block.get("label", "图片 / 内容区域"))[:14], 9.5, _SVG_COLORS["faint"], 400, "middle"))
            cur += 55
        elif btype == "steps":
            total = int(block.get("total", 3))
            current = int(block.get("current", 1))
            bw = (cw - 6 * (total - 1)) / max(total, 1)
            bx = cx
            for i in range(total):
                on = i < current
                out.append(f'<rect x="{_n(bx)}" y="{_n(cur)}" width="{_n(bw)}" height="4" rx="2" fill="{_SVG_COLORS["ink"] if on else _SVG_COLORS["hairline"]}"/>')
                bx += bw + 6
            cur += 12
        elif btype == "tags":
            items = [str(t) for t in block.get("items", [])[:4]]
            selected = set(block.get("selected", []))
            bx = cx
            for t in items:
                tw = min(len(t), 6) * 10.5 + 14
                on = t in selected
                out.append(f'<rect x="{_n(bx)}" y="{_n(cur)}" width="{_n(tw)}" height="18" rx="9" fill="{_SVG_COLORS["info_fill"] if on else "#f7f8fa"}"/>')
                out.append(_t(bx + tw / 2, cur + 13, t[:6], 9.5, _SVG_COLORS["info"] if on else _SVG_COLORS["sub"], 500, "middle"))
                bx += tw + 6
            cur += 25
        else:  # unknown block types degrade to a text line, never a gap
            label = block.get("text") or block.get("title") or ""
            if label:
                out.append(_t(cx, cur + 10, str(label)[:17], 10, _SVG_COLORS["sub"]))
                cur += 18
    return "".join(out)


def _svg_title_row(x: float, y: float, pill: str, title: str) -> str:
    return (f'<rect x="{_n(x)}" y="{_n(y)}" width="27" height="15" rx="4" fill="{_SVG_COLORS["hairline"]}"/>'
            + _t(x + 13.5, y + 11, pill, 9, _SVG_COLORS["sub"], 600, "middle")
            + _t(x + 33, y + 12, title, 12.5, _SVG_COLORS["ink"], 600))


def _svg_modal(modal: dict, x: float, fy: float, w: float, h: float) -> str:
    """Centered confirmation modal over the phone frame (mask + box + actions)."""
    c = _SVG_COLORS
    mw = w - 48
    mx = x + 24
    body_lines = _wrap(str(modal.get("body", "")), 15)[:3]
    actions = modal.get("actions", [])[:2]
    bh = 26 + 14 + len(body_lines) * 13 + 8 + len(actions) * 26 + 12
    my = fy + (h - bh) / 2
    parts = [f'<rect x="{_n(x)}" y="{_n(fy)}" width="{_n(w)}" height="{_n(h)}" rx="11" fill="rgba(15,17,20,0.45)"/>',
             f'<rect x="{_n(mx)}" y="{_n(my)}" width="{_n(mw)}" height="{_n(bh)}" rx="10" fill="#ffffff"/>']
    ty = my + 22
    parts.append(_t(mx + mw / 2, ty, str(modal.get("title", ""))[:14], 11, c["ink"], 600, "middle"))
    ty += 15
    for ln in body_lines:
        parts.append(_t(mx + mw / 2, ty, ln, 9, c["sub"], 400, "middle"))
        ty += 13
    ty += 8
    for a in actions:
        primary = a.get("style", "primary") == "primary"
        fill = c["ink"] if primary else "#ffffff"
        stroke = "none" if primary else c["frame"]
        tfill = "#ffffff" if primary else c["ink"]
        parts.append(f'<rect x="{_n(mx + 10)}" y="{_n(ty)}" width="{_n(mw - 20)}" height="20" rx="5" fill="{fill}" stroke="{stroke}"/>')
        parts.append(_t(mx + mw / 2, ty + 14, str(a.get("text", ""))[:10], 9.5, tfill, 600, "middle"))
        ty += 26
    return "".join(parts)


def _svg_card(cid: str, card: dict, rect, screens: dict | None = None) -> str:
    x, y, w, h = rect
    kind = card.get("kind", "page")
    title = card.get("title", cid)
    pill = {"page": "页面", "modal": "弹层", "result": "结果", "entry": "触点",
            "system": "系统", "external": "出口", "chip": "过程"}.get(kind, kind)
    c = _SVG_COLORS
    if kind == "chip":
        # transient waypoint: slim dashed pill between real pages
        return (f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" rx="{_n(h / 2)}" fill="#f7f8fa" stroke="{c["line"]}" stroke-dasharray="5 4"/>'
                + _t(x + w / 2, y + h / 2 + 4, "⏳ " + title, 11.5, c["sub"], 500, "middle"))
    if kind == "external":
        note = esc((card.get("screen") or {}).get("task", "既有页面 / 本期不改动"))
        parts = [f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" rx="8" fill="{c["exit_fill"]}" stroke="{c["exit_line"]}" stroke-width="1.4" stroke-dasharray="5 4"/>',
                 _t(x + 12, y + 20, title, 11.5, c["sub"], 600)]
        for i, ln in enumerate(_wrap(str((card.get("screen") or {}).get("task", "既有页面 / 本期不改动")), 14)[:2]):
            parts.append(_t(x + 12, y + 37 + i * 13, ln, 9.5, c["faint"]))
        return "".join(parts)
    if kind == "system":
        return (f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" rx="8" fill="{c["sys_fill"]}" stroke="{c["line"]}"/>'
                + _t(x + w / 2, y + h / 2 + 4, title, 11.5, c["sub"], 600, "middle"))
    if kind == "entry":
        screen = card.get("screen") or {}
        parts = [_svg_title_row(x, y - 22, pill, title),
                 f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" rx="8" fill="#ffffff" stroke="{c["line"]}"/>']
        lines = [str(k) for k in screen.get("key_content", [])[:3]] or [screen.get("task", "")]
        for i, ln in enumerate(lines):
            parts.append(_t(x + 14, y + 24 + i * 17, "· " + ln, 10.5, c["sub"]))
        return "".join(parts)
    # page / modal / result: recognizable mini phone screen
    screen = card_screen(card, screens or {})
    parts = [_svg_title_row(x, y + 8, pill, title)]
    fy = y + HEAD
    parts.append(f'<rect x="{_n(x)}" y="{_n(fy)}" width="{_n(w)}" height="{_n(CARD_H)}" rx="11" fill="#ffffff" stroke="{c["frame"]}"/>')
    parts.append(f'<rect x="{_n(x)}" y="{_n(fy)}" width="{_n(w)}" height="30" rx="11" fill="#f7f8fa"/>')
    parts.append(f'<rect x="{_n(x)}" y="{_n(fy + 19)}" width="{_n(w)}" height="11" fill="#f7f8fa"/>')
    parts.append(f'<line x1="{_n(x)}" y1="{_n(fy + 30)}" x2="{_n(x + w)}" y2="{_n(fy + 30)}" stroke="{c["hairline"]}"/>')
    parts.append(_t(x + w / 2, fy + 20, title, 11, c["ink"], 600, "middle"))
    parts.append(_svg_blocks(screen.get("blocks", []), x, fy + 38, w, fy + CARD_H))
    if screen.get("modal"):
        parts.append(_svg_modal(screen["modal"], x, fy, w, CARD_H))
    if screen.get("toast"):
        tt = str(screen["toast"])[:16]
        tw = len(tt) * 10 + 20
        parts.append(f'<rect x="{_n(x + (w - tw) / 2)}" y="{_n(fy + CARD_H - 42)}" width="{_n(tw)}" height="22" rx="11" fill="rgba(15,17,20,0.78)"/>')
        parts.append(_t(x + w / 2, fy + CARD_H - 27, tt, 9.5, "#ffffff", 500, "middle"))
    parts.append(f'<rect x="{_n(x + w / 2 - 30)}" y="{_n(fy + CARD_H - 9)}" width="60" height="3" rx="1.5" fill="{c["frame"]}"/>')
    return "".join(parts)


def render_svg(spec: dict) -> tuple[str, int, int]:
    """Pure-SVG board for Feishu whiteboard import (no foreignObject, no scripts)."""
    layout = BoardLayout(spec)
    rects, width, height = geometry(layout)
    routes, height = route_edges(layout, rects, height)
    c = _SVG_COLORS

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{SVG_FONT}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    # header
    parts.append(_t(MARGIN, 52, spec.get("title", "页面交互总览"), 22, c["ink"], 700))
    parts.append(_t(MARGIN, 74, spec.get("subtitle", "页面卡片 + 带动作/条件的连线；与交互模型同源"), 12.5, c["sub"]))
    # legend, right aligned
    legend_items = [("主路径", "primary"), ("分支", "branch"), ("异常 / 拦截", "exception"), ("返回 / 重进", "return")]
    lx = float(width - MARGIN)
    for label, ekind in reversed(legend_items):
        tw = len(label) * 11.5
        lx -= tw
        parts.append(_t(lx, 44, label, 11.5, c["sub"]))
        lx -= 6 + 26
        color, sw, dash = _SVG_EDGE[ekind]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<line x1="{_n(lx)}" y1="40" x2="{_n(lx + 26)}" y2="40" stroke="{color}" stroke-width="{sw}"{dash_attr}/>')
        lx -= 16
    # bands
    for bx0, by0, bw, bh, title in compute_bands(layout, rects):
        parts.append(f'<rect x="{_n(bx0)}" y="{_n(by0)}" width="{_n(bw)}" height="{_n(bh)}" rx="10" fill="{c["band"]}" stroke="{c["line"]}"/>')
        parts.append(_t(bx0 + 16, by0 + 21, title, 12, c["sub"], 600))
    # edges
    parts.append('<defs>')
    for name, color in (("p", "#1f2329"), ("b", "#5f5f5f"), ("e", "#9a3b3b"), ("r", "#8a8a8a")):
        parts.append(f'<marker id="ov-arrow-{name}" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{color}"/></marker>')
    parts.append('</defs>')
    marker_for = {"primary": "p", "branch": "b", "external": "b", "exception": "e", "return": "r"}
    for conn, pts, at, near_source in routes:
        kind = conn.get("kind", "primary")
        color, sw, dash = _SVG_EDGE.get(kind, _SVG_EDGE["branch"])
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<path d="{rounded(pts)}" fill="none" stroke="{color}" stroke-width="{sw}"{dash_attr} marker-end="url(#ov-arrow-{marker_for.get(kind, "b")})"/>')
    # cards
    for cid, card in layout.cards.items():
        parts.append(_svg_card(cid, card, rects[cid], spec.get("_screens")))
    # edge labels on top
    for conn, pts, at, near_source in routes:
        label = str(conn.get("label", ""))
        if not label:
            continue
        lines = _wrap(label, 8)
        lw = max(len(ln) for ln in lines) * 10.5 + 16
        lh = len(lines) * 14 + 8
        if near_source:
            rx, ry = at[0], at[1] - lh / 2
        else:
            rx, ry = at[0] - lw / 2, at[1] - lh / 2
        parts.append(f'<rect x="{_n(rx)}" y="{_n(ry)}" width="{_n(lw)}" height="{_n(lh)}" rx="5" fill="#ffffff" stroke="{c["line"]}"/>')
        for i, ln in enumerate(lines):
            parts.append(_t(rx + lw / 2, ry + 14 + i * 14, ln, 10.5, c["sub"], 400, "middle"))
    parts.append('</svg>')
    return "\n".join(parts), width, height


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
    parser.add_argument("--html", type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--svg", type=Path,
                        help="also write a pure-SVG board (Feishu whiteboard import path)")
    parser.add_argument("--scale", type=float, default=2.0)
    args = parser.parse_args()
    if not args.html and not args.svg:
        parser.error("at least one of --html or --svg is required")
    if args.png and not args.html:
        parser.error("--png requires --html (PNG is captured from the rendered HTML)")
    try:
        spec = load_spec(args.spec)
        if args.svg:
            svg_text, width, height = render_svg(spec)
            args.svg.parent.mkdir(parents=True, exist_ok=True)
            args.svg.write_text(svg_text, encoding="utf-8")
            print(f"Rendered SVG ({width}x{height}): {args.svg}")
        if args.html:
            html_text, width, height = render(spec)
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

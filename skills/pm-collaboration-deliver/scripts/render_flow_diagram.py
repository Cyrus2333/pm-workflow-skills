#!/usr/bin/env python3
"""Render a product flow diagram from a JSON spec to SVG (+ optional PNG).

Designed for PRD main-flow / branch-flow diagrams: layered (Sugiyama-lite)
layout with decision diamonds, orthogonal rounded edges, dashed return edges,
optional group bands, and full CJK text wrapping. No external dependencies:
ranking, ordering, routing and SVG emission are all implemented here.

    python3 scripts/render_flow_diagram.py \
        --spec /abs/path/flow.json \
        --out /abs/path/flow.svg \
        --png /abs/path/flow.png

PNG export uses scripts/capture_html_png.py (headless Chrome/Edge), so it no
longer depends on mermaid-cli, graphviz, rsvg or ImageMagick.

Spec shape (see assets/flow-diagram-template.json):
{
  "kind": "flow_diagram",
  "title": "...", "subtitle": "...",
  "direction": "LR" | "TB",              # default LR
  "nodes": [{"id", "label", "type": "process|decision|start|end|system",
             "group": "可选分组名"}],
  "edges": [{"from", "to", "label", "kind": "primary|branch|return|exception"}],
  "groups": [{"title": "...", "nodes": ["id", ...]}]   # optional bands
}

Exit codes: 0 ok, 2 spec / render failure.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

FONT = '-apple-system, "SF Pro Text", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif'

THEME = {
    "canvas": "#ffffff",
    "title": "#111111",
    "subtext": "#6b6b6b",
    "node_fill": "#ffffff",
    "node_stroke": "#1f1f1f",
    "system_fill": "#f2f3f5",
    "terminal_fill": "#1f1f1f",
    "terminal_text": "#ffffff",
    "decision_fill": "#fffdf5",
    "decision_stroke": "#8a6d1a",
    "band_fill": "#f7f7f8",
    "band_stroke": "#e2e2e4",
    "edge_primary": "#1f1f1f",
    "edge_branch": "#5f5f5f",
    "edge_exception": "#9a3b3b",
    "edge_return": "#8a8a8a",
    "label": "#4b4b4b",
}

EDGE_STYLE = {
    "primary": dict(color="edge_primary", width=2.4, dash=None),
    "branch": dict(color="edge_branch", width=1.6, dash=None),
    "exception": dict(color="edge_exception", width=1.6, dash="7 5"),
    "return": dict(color="edge_return", width=1.4, dash="7 5"),
}

BACK_KINDS = {"return"}  # excluded from ranking, routed below/above


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def char_width(ch: str) -> float:
    return 1.0 if ord(ch) > 0x2E7F else 0.56


def wrap_label(text: str, max_units: float) -> list[str]:
    """Greedy wrap by display width (CJK ~1 unit, latin ~0.56)."""
    lines: list[str] = []
    for raw in str(text).split("\n"):
        current, width = "", 0.0
        for ch in raw:
            w = char_width(ch)
            if current and width + w > max_units:
                lines.append(current)
                current, width = ch, w
            else:
                current += ch
                width += w
        lines.append(current)
    return lines or [""]


def load_spec(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list) or not data["nodes"]:
        raise ValueError("spec requires a non-empty nodes array")
    ids = [n.get("id") for n in data["nodes"]]
    if len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("node ids must be unique and non-empty")
    known = set(ids)
    for edge in data.get("edges", []):
        if edge.get("from") not in known or edge.get("to") not in known:
            raise ValueError(f"edge references unknown node: {edge}")
    return data


# ---------------------------------------------------------------- layout ---

class Layout:
    def __init__(self, spec: dict):
        self.spec = spec
        self.direction = spec.get("direction", "LR")
        self.nodes = {n["id"]: dict(n) for n in spec["nodes"]}
        self.edges = [dict(e) for e in spec.get("edges", [])]
        for e in self.edges:
            e.setdefault("kind", "primary" if not e.get("label") else "branch")
        self._measure_nodes()
        self.forward_edges, self.back_edges = self._split_back_edges()
        self.ranks = self._assign_ranks()
        self.order = self._order_within_ranks()
        self._assign_coordinates()

    def _measure_nodes(self):
        for node in self.nodes.values():
            is_decision = node.get("type") == "decision"
            lines = wrap_label(node.get("label", node["id"]), 12 if is_decision else 14)
            node["_lines"] = lines
            text_w = max((sum(char_width(c) for c in line) for line in lines), default=1) * 13.5
            text_h = len(lines) * 19
            if is_decision:
                node["_w"] = max(120.0, text_w * 1.35 + 44)
                node["_h"] = max(76.0, text_h * 1.5 + 36)
            else:
                node["_w"] = max(128.0, text_w + 40)
                node["_h"] = max(56.0, text_h + 30)

    def _split_back_edges(self):
        forward, back = [], []
        for e in self.edges:
            (back if e["kind"] in BACK_KINDS else forward).append(e)
        # break remaining cycles (DFS) by demoting to back edges
        adj: dict[str, list[int]] = {}
        for i, e in enumerate(forward):
            adj.setdefault(e["from"], []).append(i)
        state: dict[str, int] = {}
        demoted: set[int] = set()

        def dfs(u: str):
            state[u] = 1
            for i in adj.get(u, []):
                v = forward[i]["to"]
                if state.get(v) == 1:
                    demoted.add(i)
                elif state.get(v, 0) == 0:
                    dfs(v)
            state[u] = 2

        for nid in self.nodes:
            if state.get(nid, 0) == 0:
                dfs(nid)
        for i in sorted(demoted, reverse=True):
            back.append(forward.pop(i))
        return forward, back

    def _assign_ranks(self) -> dict[str, int]:
        rank = {nid: 0 for nid in self.nodes}
        incoming: dict[str, list[str]] = {}
        for e in self.forward_edges:
            incoming.setdefault(e["to"], []).append(e["from"])
        changed, guard = True, 0
        while changed and guard < 64:
            changed, guard = False, guard + 1
            for e in self.forward_edges:
                if rank[e["to"]] < rank[e["from"]] + 1:
                    rank[e["to"]] = rank[e["from"]] + 1
                    changed = True
        return rank

    def _order_within_ranks(self) -> dict[str, int]:
        by_rank: dict[int, list[str]] = {}
        for nid, r in self.ranks.items():
            by_rank.setdefault(r, []).append(nid)
        order = {nid: i for r, ids in by_rank.items() for i, nid in enumerate(sorted(ids))}
        group_index = self._group_index()

        def key(nid):
            return (group_index.get(nid, 0), order[nid])

        for _ in range(4):  # barycenter sweeps, alternating direction
            for r in sorted(by_rank):
                ids = by_rank[r]
                bary: dict[str, float] = {}
                for nid in ids:
                    neigh = [e["from"] for e in self.forward_edges if e["to"] == nid] + \
                            [e["to"] for e in self.forward_edges if e["from"] == nid]
                    if neigh:
                        bary[nid] = sum(order.get(x, 0) for x in neigh) / len(neigh)
                ids.sort(key=lambda n: (group_index.get(n, 0), bary.get(n, order[n])))
                for i, nid in enumerate(ids):
                    order[nid] = i
        return order

    def _group_index(self) -> dict[str, int]:
        groups = self.spec.get("groups") or []
        index: dict[str, int] = {}
        for gi, g in enumerate(groups):
            for nid in g.get("nodes", []):
                index.setdefault(nid, gi)
        return index

    def _assign_coordinates(self):
        rank_gap, order_gap, margin = 110.0, 42.0, 70.0
        top = margin + 78  # room for title/subtitle
        by_rank: dict[int, list[str]] = {}
        for nid, r in self.ranks.items():
            by_rank.setdefault(r, []).append(nid)
        # x per rank (LR) — width of widest node in rank
        rank_x: dict[int, float] = {}
        cursor = margin
        for r in sorted(by_rank):
            widest = max(self.nodes[n]["_w"] for n in by_rank[r])
            rank_x[r] = cursor
            cursor += widest + rank_gap
        self.canvas_w = cursor - rank_gap + margin
        # y per node within rank, respecting group ordering already applied
        for r, ids in by_rank.items():
            ids.sort(key=lambda n: self.order[n])
            y = top
            for nid in ids:
                node = self.nodes[nid]
                node["_x"] = rank_x[r] + (max(self.nodes[m]["_w"] for m in by_rank[r]) - node["_w"]) / 2
                node["_y"] = y
                y += node["_h"] + order_gap
        self.canvas_h = top + max(
            (self.nodes[n]["_y"] + self.nodes[n]["_h"] for n in self.nodes), default=0
        ) + margin + 30
        if self.direction == "TB":  # swap axes
            for node in self.nodes.values():
                node["_x"], node["_y"] = node["_y"], node["_x"]
                node["_w"], node["_h"] = node["_h"], node["_w"]
            self.canvas_w, self.canvas_h = self.canvas_h, self.canvas_w


# ---------------------------------------------------------------- render ---

class Svg:
    def __init__(self, w: float, h: float):
        self.w, self.h = math.ceil(w), math.ceil(h)
        self.parts: list[str] = [f'<rect width="{self.w}" height="{self.h}" fill="{THEME["canvas"]}"/>']

    def raw(self, markup: str):
        self.parts.append(markup)

    def text(self, x, y, value, size=13, bold=False, color="#111111", anchor="start"):
        weight = ' font-weight="600"' if bold else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'fill="{color}" text-anchor="{anchor}"{weight}>{esc(value)}</text>')

    def finish(self) -> str:
        markers = []
        for key, style in EDGE_STYLE.items():
            color = THEME[style["color"]]
            markers.append(
                f'<marker id="arrow-{key}" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" '
                f'orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{color}"/></marker>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}"><defs>{"".join(markers)}</defs>'
                f'{"".join(self.parts)}</svg>')


def rounded_path(points: list[tuple[float, float]], radius: float = 10.0) -> str:
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


def edge_points(layout: Layout, edge: dict,
                lane: float | None = None) -> tuple[list[tuple[float, float]], tuple[float, float]]:
    """Return (polyline points, label anchor).

    lane: for under-routed edges (back edges and long-span forward edges in
    LR direction), the y of the horizontal lane below the diagram; for TB
    direction the x of the vertical lane to the right.
    """
    a = layout.nodes[edge["from"]]
    b = layout.nodes[edge["to"]]
    lr = layout.direction == "LR"

    def port_right(n): return (n["_x"] + n["_w"], n["_y"] + n["_h"] / 2)
    def port_left(n): return (n["_x"], n["_y"] + n["_h"] / 2)
    def port_top(n): return (n["_x"] + n["_w"] / 2, n["_y"])
    def port_bottom(n): return (n["_x"] + n["_w"] / 2, n["_y"] + n["_h"])

    if lr:
        if lane is not None:
            p1, p2 = port_bottom(a), port_bottom(b)
            pts = [p1, (p1[0], lane), (p2[0], lane), p2]
        else:
            p1, p2 = port_right(a), port_left(b)
            mx = (p1[0] + p2[0]) / 2
            pts = [p1, (mx, p1[1]), (mx, p2[1]), p2]
    else:
        if lane is not None:
            p1, p2 = port_right(a), port_right(b)
            pts = [p1, (lane, p1[1]), (lane, p2[1]), p2]
        else:
            p1, p2 = port_bottom(a), port_top(b)
            my = (p1[1] + p2[1]) / 2
            pts = [p1, (p1[0], my), (p2[0], my), p2]
    # drop redundant collinear mid points
    clean = [pts[0]]
    for p in pts[1:]:
        if p != clean[-1]:
            clean.append(p)
    # label sits on the middle of the longest segment
    best_len, label_at = -1.0, clean[0]
    for i in range(len(clean) - 1):
        seg = math.hypot(clean[i + 1][0] - clean[i][0], clean[i + 1][1] - clean[i][1])
        if seg > best_len:
            best_len = seg
            label_at = ((clean[i][0] + clean[i + 1][0]) / 2, (clean[i][1] + clean[i + 1][1]) / 2)
    return clean, label_at


def render(spec: dict) -> tuple[str, int, int]:
    layout = Layout(spec)
    margin = 70.0
    lr = layout.direction == "LR"

    # Under-routed edges: back edges plus forward edges spanning >1 rank.
    # They run in staggered lanes outside the node field instead of cutting
    # through it, and the canvas grows to fit the deepest lane.
    under: list[dict] = list(layout.back_edges)
    for e in layout.forward_edges:
        if layout.ranks[e["to"]] - layout.ranks[e["from"]] > 1:
            under.append(e)
    lanes: dict[int, float] = {}
    if lr:
        base = max((n["_y"] + n["_h"] for n in layout.nodes.values()), default=0.0) + 36
        for i, e in enumerate(under):
            lanes[id(e)] = base + i * 38
        if under:
            layout.canvas_h = max(layout.canvas_h, lanes[id(under[-1])] + 30 + margin * 0.6)
    else:
        base = max((n["_x"] + n["_w"] for n in layout.nodes.values()), default=0.0) + 36
        for i, e in enumerate(under):
            lanes[id(e)] = base + i * 38
        if under:
            layout.canvas_w = max(layout.canvas_w, lanes[id(under[-1])] + 30 + margin * 0.6)

    svg = Svg(layout.canvas_w, layout.canvas_h)
    svg.text(margin, margin - 26, spec.get("title", "流程图"), 21, bold=True, color=THEME["title"])
    if spec.get("subtitle"):
        svg.text(margin, margin - 2, spec["subtitle"], 12.5, color=THEME["subtext"])

    # group bands behind everything
    group_index = layout._group_index()
    groups = spec.get("groups") or []
    for gi, group in enumerate(groups):
        members = [layout.nodes[n] for n in group.get("nodes", []) if n in group_index]
        if not members:
            continue
        x0 = min(n["_x"] for n in members) - 26
        x1 = max(n["_x"] + n["_w"] for n in members) + 26
        y0 = min(n["_y"] for n in members) - 44
        y1 = max(n["_y"] + n["_h"] for n in members) + 26
        svg.raw(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" '
                f'rx="14" fill="{THEME["band_fill"]}" stroke="{THEME["band_stroke"]}"/>')
        svg.text(x0 + 14, y0 + 26, group.get("title", ""), 12.5, bold=True, color=THEME["subtext"])

    # edges
    for edge in layout.forward_edges + layout.back_edges:
        style = EDGE_STYLE.get(edge["kind"], EDGE_STYLE["branch"])
        pts, (lx, ly) = edge_points(layout, edge, lanes.get(id(edge)))
        dash = f' stroke-dasharray="{style["dash"]}"' if style["dash"] else ""
        svg.raw(f'<path d="{rounded_path(pts)}" fill="none" stroke="{THEME[style["color"]]}" '
                f'stroke-width="{style["width"]}"{dash} marker-end="url(#arrow-{edge["kind"]})"/>')
        label = edge.get("label", "")
        if label:
            lines = wrap_label(label, 16)
            w = max(sum(char_width(c) for c in line) for line in lines) * 11.5 + 14
            h = len(lines) * 16 + 8
            top = ly - h / 2 - (0 if layout.direction == "LR" else 0)
            svg.raw(f'<rect x="{lx - w / 2:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" '
                    f'rx="5" fill="{THEME["canvas"]}" stroke="{THEME["band_stroke"]}"/>')
            for i, line in enumerate(lines):
                svg.text(lx, top + 14 + i * 16, line, 11, color=THEME["label"], anchor="middle")

    # nodes
    for node in layout.nodes.values():
        x, y, w, h = node["_x"], node["_y"], node["_w"], node["_h"]
        ntype = node.get("type", "process")
        cx, cy = x + w / 2, y + h / 2
        if ntype == "decision":
            points = f"{cx:.1f},{y:.1f} {x + w:.1f},{cy:.1f} {cx:.1f},{y + h:.1f} {x:.1f},{cy:.1f}"
            svg.raw(f'<polygon points="{points}" fill="{THEME["decision_fill"]}" '
                    f'stroke="{THEME["decision_stroke"]}" stroke-width="1.6"/>')
        else:
            fill, stroke, text_color = THEME["node_fill"], THEME["node_stroke"], THEME["title"]
            radius = 12
            if ntype == "system":
                fill = THEME["system_fill"]
            if ntype in {"start", "end"}:
                radius = min(28, h / 2)
            if ntype == "end":
                fill, text_color = THEME["terminal_fill"], THEME["terminal_text"]
            svg.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" '
                    f'fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
            node["_text_color"] = text_color
        color = node.get("_text_color", THEME["title"])
        lines = node["_lines"]
        first_baseline = cy - (len(lines) - 1) * 9.5 + 4.5
        for i, line in enumerate(lines):
            svg.text(cx, first_baseline + i * 19, line, 13.5, bold=(ntype in {"start", "end"}),
                     color=color, anchor="middle")
    return svg.finish(), svg.w, svg.h


def export_png(svg_markup: str, png_path: Path, width: int, height: int, scale: float) -> str:
    helper = Path(__file__).with_name("capture_html_png.py")
    if not helper.is_file():
        raise RuntimeError("capture_html_png.py not found next to this script")
    with tempfile.TemporaryDirectory(prefix="flow-diagram-") as tmp:
        page = Path(tmp) / "index.html"
        page.write_text(
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;}}"
            "svg{display:block;}</style></head><body>"
            + svg_markup + "</body></html>",
            encoding="utf-8",
        )
        cmd = [sys.executable, str(helper), "--html", str(page), "--png", str(png_path),
               "--width", str(width), "--height", str(height), "--scale", f"{scale:g}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "png capture failed")
    return "headless-browser"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="output .svg path")
    parser.add_argument("--png", type=Path, help="optional .png output (headless browser)")
    parser.add_argument("--scale", type=float, default=2.0)
    args = parser.parse_args()
    try:
        spec = load_spec(args.spec)
        markup, width, height = render(spec)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markup, encoding="utf-8")
        print(f"Rendered SVG ({width}x{height}): {args.out}")
        if args.png:
            renderer = export_png(markup, args.png, width, height, args.scale)
            print(f"Rendered PNG with {renderer}: {args.png}")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

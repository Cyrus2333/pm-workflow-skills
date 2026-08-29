#!/usr/bin/env python3
"""Export a flow-diagram or page-interaction-overview spec to Mermaid DSL.

Feishu whiteboards can import Mermaid natively, so in the Feishu delivery
surface this DSL is the *input format* for the board — not a local render
dependency. Local rendering continues to use render_flow_diagram.py /
render_overview_board.py; this exporter only translates the same spec JSON
into Mermaid so the semantic source of truth stays single.

Supported specs:
- assets/flow-diagram-template.json  (kind == "flow_diagram")
- assets/page-interaction-overview-template.json (cards/connectors)

Usage:
    python3 export_flow_mermaid.py --spec main-flow-spec.json --output main-flow.mmd
    python3 export_flow_mermaid.py --spec page-interaction-overview.json  # stdout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EDGE_ARROW = {
    "primary": "-->",
    "branch": "-->",
    "exception": "-.->",
    "return": "-.->",
}


def esc(text: str) -> str:
    """Escape a label for Mermaid flowchart syntax."""
    text = text.replace("\n", "<br/>")
    text = text.replace('"', "'")
    return text


def node_shape(node_type: str, label: str) -> str:
    if node_type == "decision":
        return '{"' + label + '"}'
    if node_type in {"start", "end"}:
        return '(["' + label + '"])'
    if node_type == "system":
        return '[["' + label + '"]]'
    return '["' + label + '"]'


def safe_id(raw: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    if not ident or ident[0].isdigit():
        ident = "N_" + ident
    return ident


def export_flow_diagram(spec: dict) -> str:
    direction = spec.get("direction", "LR")
    lines = [f"flowchart {direction}"]
    id_map: dict[str, str] = {}
    for node in spec.get("nodes", []):
        ident = safe_id(node["id"])
        id_map[node["id"]] = ident
        lines.append(f"    {ident}{node_shape(node.get('type', 'process'), esc(node['label']))}")
    for edge in spec.get("edges", []):
        src = id_map.get(edge["from"], safe_id(edge["from"]))
        dst = id_map.get(edge["to"], safe_id(edge["to"]))
        arrow = EDGE_ARROW.get(edge.get("kind", "primary"), "-->")
        label = esc(edge.get("label", ""))
        lines.append(f"    {src} {arrow}|{label}| {dst}" if label else f"    {src} {arrow} {dst}")
    for group in spec.get("groups", []):
        members = " & ".join(id_map.get(n, safe_id(n)) for n in group.get("nodes", []))
        if members:
            lines.append(f'    subgraph G_{safe_id(group["title"])}["{esc(group["title"])}"]')
            lines.append(f"        {members}")
            lines.append("    end")
    return "\n".join(lines) + "\n"


def export_overview(spec: dict) -> str:
    direction = "LR" if spec.get("reading_direction", "horizontal") == "horizontal" else "TD"
    lines = [f"flowchart {direction}"]
    id_map: dict[str, str] = {}
    for card in spec.get("cards", []):
        ident = safe_id(card["id"])
        id_map[card["id"]] = ident
        label = card["title"]
        screen = card.get("screen") or {}
        if screen.get("task"):
            label += "\n" + screen["task"]
        shape = node_shape("start" if card.get("kind") == "entry" else ("end" if card.get("kind") in {"exit", "external"} else "process"), esc(label))
        lines.append(f"    {ident}{shape}")
    for conn in spec.get("connectors", []):
        src = id_map.get(conn["from_card"], safe_id(conn["from_card"]))
        dst = id_map.get(conn["to_card"], safe_id(conn["to_card"]))
        arrow = EDGE_ARROW.get(conn.get("kind", "primary"), "-->")
        label = esc(conn.get("label", ""))
        lines.append(f"    {src} {arrow}|{label}| {dst}" if label else f"    {src} {arrow} {dst}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="write .mmd here; defaults to stdout")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec.get("kind") == "flow_diagram" or "nodes" in spec:
        mermaid = export_flow_diagram(spec)
    elif "cards" in spec and "connectors" in spec:
        mermaid = export_overview(spec)
    else:
        print("error: unsupported spec — expected flow-diagram nodes/edges or overview cards/connectors", file=sys.stderr)
        return 2

    if args.output:
        args.output.write_text(mermaid, encoding="utf-8")
        print(f"mermaid exported: {args.output}")
    else:
        sys.stdout.write(mermaid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

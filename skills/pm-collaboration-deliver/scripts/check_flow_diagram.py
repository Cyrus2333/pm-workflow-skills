#!/usr/bin/env python3
"""Semantic checks for a flow_diagram spec (视觉与原型 流程图章节).

    python3 scripts/check_flow_diagram.py --spec /abs/flow.json

Checks:
- every non-entry node has at least one incoming edge;
- every non-terminal node (type != end) has at least one outgoing edge;
- decision nodes have >= 2 outgoing edges and every outgoing edge is labeled;
- branch/exception/return edges carry a label (conditions must be readable);
- no orphan nodes;
- terminal (end) nodes describe a user/business result, not a process step —
  enforced softly via a warning when an end node still has outgoing edges.

Exit codes: 0 ok (warnings allowed), 2 on errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    args = parser.parse_args()
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    nodes = {n["id"]: n for n in spec.get("nodes", []) if isinstance(n, dict) and n.get("id")}
    edges = [e for e in spec.get("edges", []) if isinstance(e, dict)]
    errors: list[str] = []
    warnings: list[str] = []

    if not nodes:
        print("error: spec requires a non-empty nodes array", file=sys.stderr)
        return 2

    incoming: dict[str, list[dict]] = {nid: [] for nid in nodes}
    outgoing: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for e in edges:
        if e.get("from") not in nodes or e.get("to") not in nodes:
            errors.append(f"edge references unknown node: {e}")
            continue
        incoming[e["to"]].append(e)
        outgoing[e["from"]].append(e)

    for nid, node in nodes.items():
        ntype = node.get("type", "process")
        if not incoming[nid] and ntype != "start":
            errors.append(f"node {nid} has no incoming edge (non-entry nodes need a source)")
        if not outgoing[nid] and ntype != "end":
            errors.append(f"node {nid} has no outgoing edge (non-terminal nodes need a destination)")
        if ntype == "end" and outgoing[nid]:
            warnings.append(f"end node {nid} still has outgoing edges; terminal should be a result")
        if ntype == "decision":
            outs = outgoing[nid]
            if len(outs) < 2:
                errors.append(f"decision {nid} needs at least 2 outgoing edges")
            for e in outs:
                if not str(e.get("label", "")).strip():
                    errors.append(f"decision {nid} has an unlabeled branch to {e['to']}")
        for e in outgoing[nid]:
            if e.get("kind") in {"branch", "exception", "return"} \
                    and not str(e.get("label", "")).strip():
                errors.append(
                    f"{e['kind']} edge {nid}->{e['to']} needs a readable condition label")

    for error in errors:
        print(f"error: {error}")
    for warning in warnings:
        print(f"warning: {warning}")
    if errors:
        return 2
    print(f"ok: {len(nodes)} nodes, {len(edges)} edges, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

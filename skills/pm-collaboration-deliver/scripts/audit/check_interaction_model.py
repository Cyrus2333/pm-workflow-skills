#!/usr/bin/env python3
"""Validate a product interaction model and emit human-readable coverage evidence."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


STATE_TYPES = {
    "entry", "loading", "ready", "modal", "processing", "empty", "success",
    "failure", "blocked", "completed", "deferred", "external",
}
TRANSITION_KINDS = {"user", "system", "return", "retry", "reentry", "external"}
ASYNC_OUTCOMES = {"success", "failure"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def indexed(items: Any, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{label} must be an array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}] must be an object")
            continue
        item_id = item.get("id")
        if not nonempty(item_id):
            errors.append(f"{label}[{index}].id is required")
            continue
        if item_id in result:
            errors.append(f"duplicate {label} id: {item_id}")
        result[item_id] = item
    return result


def validate(model: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if model.get("schema_version") != "2.0":
        errors.append("schema_version must be 2.0")
    surfaces = indexed(model.get("surfaces"), "surfaces", errors)
    states = indexed(model.get("states"), "states", errors)
    transitions = indexed(model.get("transitions"), "transitions", errors)
    coverage = model.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("coverage must be an object")
        coverage = {}
    entry_ids = coverage.get("entry_state_ids")
    if not isinstance(entry_ids, list) or not entry_ids or not all(nonempty(x) for x in entry_ids):
        errors.append("coverage.entry_state_ids must be a non-empty string array")
        entry_ids = []
    for entry in entry_ids:
        if entry not in states:
            errors.append(f"unknown entry state: {entry}")

    action_owner: dict[str, str] = {}
    enabled_actions: set[str] = set()
    for state_id, state in states.items():
        for field in ("name", "surface_id", "entry", "visible", "source_anchor"):
            if not nonempty(state.get(field)):
                errors.append(f"state {state_id}.{field} is required")
        if state.get("surface_id") not in surfaces:
            errors.append(f"state {state_id} references unknown surface: {state.get('surface_id')}")
        if state.get("type") not in STATE_TYPES:
            errors.append(f"state {state_id}.type is unsupported")
        actions = state.get("actions", [])
        if not isinstance(actions, list):
            errors.append(f"state {state_id}.actions must be an array")
            actions = []
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                errors.append(f"state {state_id}.actions[{index}] must be an object")
                continue
            action_id = action.get("id")
            if not nonempty(action_id) or not nonempty(action.get("label")):
                errors.append(f"state {state_id}.actions[{index}] requires id and label")
                continue
            if action_id in action_owner:
                errors.append(f"duplicate action id: {action_id}")
            action_owner[action_id] = state_id
            if action.get("enabled", True):
                enabled_actions.add(action_id)
        if state.get("visual_required", True) and not nonempty(state.get("visual_ref")):
            errors.append(f"state {state_id} requires visual_ref")

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    covered_actions: set[str] = set()
    for transition_id, transition in transitions.items():
        for field in ("from", "to", "trigger", "source_anchor"):
            if not nonempty(transition.get(field)):
                errors.append(f"transition {transition_id}.{field} is required")
        source, target = transition.get("from"), transition.get("to")
        if source not in states:
            errors.append(f"transition {transition_id} has unknown source: {source}")
        if target not in states:
            errors.append(f"transition {transition_id} has unknown target: {target}")
        if transition.get("kind") not in TRANSITION_KINDS:
            errors.append(f"transition {transition_id}.kind is unsupported")
        action_id = transition.get("action_id")
        if action_id is not None:
            if action_id not in action_owner:
                errors.append(f"transition {transition_id} references unknown action: {action_id}")
            elif action_owner[action_id] != source:
                errors.append(f"transition {transition_id} action {action_id} belongs to another state")
            covered_actions.add(action_id)
        if source in states and target in states:
            outgoing[source].append(transition)
            incoming[target].append(transition)

    for action_id in sorted(enabled_actions - covered_actions):
        errors.append(f"enabled action has no transition: {action_id}")
    for state_id, state in states.items():
        if not state.get("terminal", False) and not outgoing[state_id]:
            errors.append(f"non-terminal state has no outgoing transition: {state_id}")
        if state.get("type") == "processing":
            outcomes = {t.get("outcome") for t in outgoing[state_id]}
            missing = sorted(ASYNC_OUTCOMES - outcomes)
            if missing:
                errors.append(f"processing state {state_id} misses outcomes: {', '.join(missing)}")

    reachable: set[str] = set()
    queue: deque[str] = deque(x for x in entry_ids if x in states)
    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        queue.extend(t["to"] for t in outgoing[current] if t.get("to") not in reachable)
    unreachable = sorted(set(states) - reachable)
    if unreachable:
        errors.append("unreachable states: " + ", ".join(unreachable))

    required_types = coverage.get("required_state_types", [])
    if not isinstance(required_types, list):
        errors.append("coverage.required_state_types must be an array")
        required_types = []
    actual_types = {state.get("type") for state in states.values()}
    missing_types = sorted(set(required_types) - actual_types)
    if missing_types:
        errors.append("missing required state types: " + ", ".join(missing_types))

    visual_states = {s.get("visual_ref") for s in states.values() if s.get("visual_required", True)}
    stats = {
        "surfaces": len(surfaces),
        "states": len(states),
        "transitions": len(transitions),
        "actions": len(action_owner),
        "enabled_actions": len(enabled_actions),
        "covered_actions": len(enabled_actions & covered_actions),
        "reachable_states": len(reachable),
        "terminal_states": sum(bool(s.get("terminal")) for s in states.values()),
        "visual_states": len(visual_states - {None}),
    }
    return errors, stats


def report(model: dict[str, Any], stats: dict[str, Any]) -> str:
    lines = [
        "# 交互模型覆盖报告", "",
        "| 检查项 | 结果 |", "|---|---:|",
        f"| 载体 / 页面 | {stats['surfaces']} |",
        f"| 用户可见状态 | {stats['states']} |",
        f"| 状态迁移 | {stats['transitions']} |",
        f"| 可用操作迁移覆盖 | {stats['covered_actions']} / {stats['enabled_actions']} |",
        f"| 可达状态 | {stats['reachable_states']} / {stats['states']} |",
        f"| 终态 | {stats['terminal_states']} |",
        f"| 视觉状态引用 | {stats['visual_states']} |", "",
        "## 最短主路径", "",
    ]
    state_names = {s["id"]: s.get("name", s["id"]) for s in model["states"]}
    transitions = defaultdict(list)
    for item in model["transitions"]:
        transitions[item["from"]].append(item)
    entries = model["coverage"]["entry_state_ids"]
    terminal = {s["id"] for s in model["states"] if s.get("terminal")}
    paths: list[list[str]] = []
    for target in sorted(terminal):
        queue = deque((entry, [entry]) for entry in entries)
        seen = set()
        found: list[str] | None = None
        while queue and found is None:
            current, path = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            if current == target:
                found = path
                break
            for item in transitions[current]:
                queue.append((item["to"], path + [item["to"]]))
        if found:
            paths.append(found)
    for path in paths:
        lines.append("- " + " → ".join(state_names[x] for x in path))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(model, dict):
        print("error: model root must be an object", file=sys.stderr)
        return 2
    errors, stats = validate(model)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 2
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report(model, stats), encoding="utf-8")
    print(
        "Interaction model checks passed: "
        f"{stats['surfaces']} surfaces, {stats['states']} states, "
        f"{stats['transitions']} transitions, "
        f"{stats['covered_actions']}/{stats['enabled_actions']} enabled actions covered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

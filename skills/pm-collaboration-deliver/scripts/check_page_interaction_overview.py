#!/usr/bin/env python3
"""Validate a page-level interaction overview against its interaction model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CARD_KINDS = {"entry", "page", "modal", "result", "system", "external", "chip"}
CONNECTOR_KINDS = {"primary", "branch", "return", "exception", "external"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be an object")
    return data


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


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def validate(overview: dict[str, Any], model: dict[str, Any], base: Path, check_files: bool = True) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    if overview.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if overview.get("kind") != "page_interaction_overview":
        errors.append("kind must be page_interaction_overview")
    if not nonempty(overview.get("question")):
        errors.append("question is required")
    if overview.get("coverage_mode") not in {"review_complete", "focused"}:
        errors.append("coverage_mode must be review_complete or focused")
    if overview.get("delivery_role") not in {"inline", "zoomable"}:
        errors.append("delivery_role must be inline or zoomable")
    if overview.get("reading_direction") not in {"left_to_right", "top_to_bottom"}:
        errors.append("reading_direction must be left_to_right or top_to_bottom")

    surfaces = indexed(model.get("surfaces"), "model.surfaces", errors)
    states = indexed(model.get("states"), "model.states", errors)
    transitions = indexed(model.get("transitions"), "model.transitions", errors)
    cards = indexed(overview.get("cards"), "cards", errors)
    connectors = indexed(overview.get("connectors"), "connectors", errors)

    state_to_card: dict[str, str] = {}
    represented_states: set[str] = set()
    for card_id, card in cards.items():
        if not nonempty(card.get("title")):
            errors.append(f"card {card_id}.title is required")
        if card.get("kind") not in CARD_KINDS:
            errors.append(f"card {card_id}.kind is unsupported")
        state_ids = card.get("state_ids")
        if not isinstance(state_ids, list) or not state_ids or not all(nonempty(x) for x in state_ids):
            errors.append(f"card {card_id}.state_ids must be a non-empty string array")
            state_ids = []
        for state_id in state_ids:
            if state_id not in states:
                errors.append(f"card {card_id} references unknown state: {state_id}")
                continue
            if state_id in state_to_card:
                errors.append(f"state {state_id} is represented by multiple cards")
            state_to_card[state_id] = card_id
            represented_states.add(state_id)
        # Transient states (loading / processing) are waypoints between pages,
        # not pages: they must be slim chip cards and are exempt from screen
        # content. Chip cards may only carry transient states.
        for state_id in state_ids:
            state = states.get(state_id)
            if not state:
                continue
            visibility = state.get("visibility", "page")
            if visibility == "transient" and card.get("kind") not in {"chip", "system"}:
                errors.append(
                    f"transient state {state_id} must be represented by a chip or system card, "
                    f"not a {card.get('kind')} card (loading/processing is not a page)")
            if card.get("kind") == "chip" and visibility != "transient":
                errors.append(
                    f"chip card {card_id} carries non-transient state {state_id}; "
                    f"pages the user can land on need a full page card")
        if len(state_ids) > 1:
            variants = card.get("state_variants")
            visual_equivalent = card.get("visual_equivalent") is True
            if visual_equivalent:
                if not nonempty(card.get("equivalence_reason")):
                    errors.append(f"card {card_id}.equivalence_reason is required when visual_equivalent=true")
            elif not isinstance(variants, list):
                errors.append(
                    f"card {card_id}.state_variants is required when one card aggregates multiple states"
                )
            else:
                variant_state_ids: list[str] = []
                for variant_index, variant in enumerate(variants):
                    label = f"card {card_id}.state_variants[{variant_index}]"
                    if not isinstance(variant, dict):
                        errors.append(f"{label} must be an object")
                        continue
                    state_id = variant.get("state_id")
                    if not nonempty(state_id):
                        errors.append(f"{label}.state_id is required")
                    else:
                        variant_state_ids.append(state_id)
                    if not nonempty(variant.get("label")):
                        errors.append(f"{label}.label is required")
                    if not nonempty(variant.get("difference")):
                        errors.append(f"{label}.difference is required")
                if sorted(variant_state_ids) != sorted(state_ids):
                    errors.append(f"card {card_id}.state_variants must map every aggregated state exactly once")
        surface_ids = card.get("surface_ids")
        if not isinstance(surface_ids, list) or not surface_ids or not all(nonempty(x) for x in surface_ids):
            errors.append(f"card {card_id}.surface_ids must be a non-empty string array")
            surface_ids = []
        for surface_id in surface_ids:
            if surface_id not in surfaces:
                errors.append(f"card {card_id} references unknown surface: {surface_id}")
        for state_id in state_ids:
            if state_id in states and states[state_id].get("surface_id") not in surface_ids:
                errors.append(f"card {card_id} omits surface of state {state_id}")
        if card.get("kind") not in {"system", "external", "chip"}:
            if not nonempty(card.get("visual_ref")):
                errors.append(f"card {card_id}.visual_ref is required for a visible page card")
            screen = card.get("screen")
            if nonempty(card.get("screen_ref")):
                # Screen content is reused from the shared screen_source and
                # validated against it below; inline phrases are not needed.
                pass
            elif not isinstance(screen, dict):
                errors.append(f"card {card_id}.screen is required for a recognizable page card")
            else:
                if not nonempty(screen.get("task")):
                    errors.append(f"card {card_id}.screen.task is required")
                key_content = screen.get("key_content")
                if not isinstance(key_content, list) or not key_content or not all(nonempty(x) for x in key_content):
                    errors.append(f"card {card_id}.screen.key_content must be a non-empty string array")
                actions = screen.get("actions")
                if not isinstance(actions, list) or not all(nonempty(x) for x in actions):
                    errors.append(f"card {card_id}.screen.actions must be a string array")
                if not actions and not nonempty(screen.get("visible_feedback")):
                    errors.append(
                        f"card {card_id}.screen requires actions or visible_feedback to show the user state"
                    )

    represented_transitions: set[str] = set()
    action_transition_ids = {tid for tid, item in transitions.items() if item.get("action_id")}

    # screen_ref: overview cards reuse the same screen definitions as the
    # key-page storyboard, so the two visuals can never drift apart.
    screen_source_ids: set[str] | None = None
    screen_source = overview.get("screen_source")
    if nonempty(screen_source):
        source_path = resolve(base, screen_source)
        if not source_path.is_file():
            errors.append(f"screen_source does not exist: {source_path}")
        else:
            try:
                source_data = json.loads(source_path.read_text(encoding="utf-8"))
                screen_source_ids = {
                    item.get("id") for item in source_data.get("screens", [])
                    if isinstance(item, dict) and nonempty(item.get("id"))
                }
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"screen_source cannot be read: {exc}")
    for card_id, card in cards.items():
        ref = card.get("screen_ref")
        if not nonempty(ref):
            continue
        if screen_source_ids is None:
            errors.append(f"card {card_id}.screen_ref requires overview.screen_source")
        elif ref not in screen_source_ids:
            errors.append(f"card {card_id}.screen_ref references unknown screen in screen_source: {ref}")

    for connector_id, connector in connectors.items():
        source_card = connector.get("from_card")
        target_card = connector.get("to_card")
        if source_card not in cards or target_card not in cards:
            errors.append(f"connector {connector_id} references an unknown card")
        if not nonempty(connector.get("label")):
            errors.append(f"connector {connector_id}.label is required")
        if connector.get("kind") not in CONNECTOR_KINDS:
            errors.append(f"connector {connector_id}.kind is unsupported")
        transition_ids = connector.get("transition_ids")
        if not isinstance(transition_ids, list) or not transition_ids or not all(nonempty(x) for x in transition_ids):
            errors.append(f"connector {connector_id}.transition_ids must be a non-empty string array")
            transition_ids = []
        for transition_id in transition_ids:
            if transition_id not in transitions:
                errors.append(f"connector {connector_id} references unknown transition: {transition_id}")
                continue
            if transition_id in represented_transitions:
                errors.append(f"transition {transition_id} is represented by multiple connectors")
            represented_transitions.add(transition_id)
            transition = transitions[transition_id]
            expected_source = state_to_card.get(transition.get("from"))
            expected_target = state_to_card.get(transition.get("to"))
            if expected_source and source_card != expected_source:
                errors.append(f"connector {connector_id} has wrong source card for {transition_id}")
            if expected_target and target_card != expected_target:
                errors.append(f"connector {connector_id} has wrong target card for {transition_id}")
            if transition.get("kind") in {"return", "retry", "reentry"} and connector.get("kind") != "return":
                errors.append(f"connector {connector_id} must visually declare return for {transition_id}")

    if overview.get("coverage_mode") == "review_complete":
        entry_states = set(model.get("coverage", {}).get("entry_state_ids", []))
        missing_entries = sorted(entry_states - represented_states)
        if missing_entries:
            errors.append("overview misses entry states: " + ", ".join(missing_entries))
        visible_states = {sid for sid, item in states.items() if item.get("visual_required", True)}
        missing_visible = sorted(visible_states - represented_states)
        if missing_visible:
            errors.append("overview misses visually required states: " + ", ".join(missing_visible))
        terminal_states = {sid for sid, item in states.items() if item.get("terminal")}
        missing_terminal = sorted(terminal_states - represented_states)
        if missing_terminal:
            errors.append("overview misses terminal states: " + ", ".join(missing_terminal))
        missing_actions = sorted(action_transition_ids - represented_transitions)
        if missing_actions:
            errors.append("overview misses action transitions: " + ", ".join(missing_actions))
        missing_states = sorted(set(states) - represented_states)
        missing_transitions = sorted(set(transitions) - represented_transitions)
        if missing_states:
            errors.append("review_complete overview misses states: " + ", ".join(missing_states))
        if missing_transitions:
            errors.append("review_complete overview misses transitions: " + ", ".join(missing_transitions))
    else:
        focus_states = overview.get("focus_state_ids")
        focus_transitions = overview.get("focus_transition_ids")
        if not isinstance(focus_states, list) or not focus_states or not all(nonempty(x) for x in focus_states):
            errors.append("focused overview requires focus_state_ids")
            focus_states = []
        if not isinstance(focus_transitions, list) or not focus_transitions or not all(nonempty(x) for x in focus_transitions):
            errors.append("focused overview requires focus_transition_ids")
            focus_transitions = []
        unknown_focus_states = sorted(set(focus_states) - set(states))
        unknown_focus_transitions = sorted(set(focus_transitions) - set(transitions))
        if unknown_focus_states:
            errors.append("focused overview references unknown states: " + ", ".join(unknown_focus_states))
        if unknown_focus_transitions:
            errors.append("focused overview references unknown transitions: " + ", ".join(unknown_focus_transitions))
        missing_focus_states = sorted(set(focus_states) - represented_states)
        missing_focus_transitions = sorted(set(focus_transitions) - represented_transitions)
        if missing_focus_states:
            errors.append("focused overview misses declared states: " + ", ".join(missing_focus_states))
        if missing_focus_transitions:
            errors.append("focused overview misses declared transitions: " + ", ".join(missing_focus_transitions))

    render = overview.get("render")
    if not isinstance(render, dict):
        errors.append("render is required")
    else:
        for field in ("source_path", "preview_path"):
            if not nonempty(render.get(field)):
                errors.append(f"render.{field} is required")
            elif check_files and not resolve(base, render[field]).is_file():
                errors.append(f"render.{field} does not exist: {resolve(base, render[field])}")

    stats = {
        "cards": len(cards),
        "connectors": len(connectors),
        "states": len(represented_states),
        "transitions": len(represented_transitions),
        "action_transitions": len(action_transition_ids & represented_transitions),
    }
    return errors, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overview", required=True, type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--no-file-check", action="store_true",
                        help="skip on-disk existence checks for render artifacts (structure is still validated)")
    args = parser.parse_args()
    try:
        overview = load(args.overview)
        model_value = args.model or resolve(args.overview.parent, overview.get("interaction_model", ""))
        model = load(model_value)
        errors, stats = validate(overview, model, args.overview.parent, check_files=not args.no_file_check)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 2
    print(
        "Page interaction overview passed: "
        f"{stats['cards']} cards, {stats['connectors']} connectors, "
        f"{stats['states']} states, {stats['transitions']} transitions, "
        f"{stats['action_transitions']} action transitions covered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

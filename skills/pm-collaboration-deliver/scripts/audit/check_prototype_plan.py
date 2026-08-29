#!/usr/bin/env python3
"""Validate prototype readiness, evidence roles, and planned visual outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PRODUCT_SEMANTICS = {"interaction_complete", "structure_complete", "partial", "insufficient"}
VISUAL_CONTEXTS = {"confirmed_design", "existing_ui", "reference_only", "declared_unverified", "none"}
DECISIONS = {"generate", "annotate_only", "plan_only", "return_upstream"}
EVIDENCE_TYPES = {"formal_prd", "design", "screenshot", "design_system", "existing_product"}
AUTHORITIES = {"product_behavior", "visual_design", "observational", "reference"}
SCREENSHOT_ROLES = {"current_ui", "confirmed_design", "visual_reference"}
OBSERVATION_KINDS = {"observed", "inferred", "unknown"}
REUSE_STRATEGIES = {"reuse_confirmed", "adapt_existing", "reference_only", "low_fidelity_new", "plan_only"}
OUTPUT_KINDS = {
    "page_map", "annotated_screenshot", "state_comparison", "interaction_storyboard",
    "page_interaction_overview", "low_fidelity_wireframe", "design_handoff",
}
DELIVERY_ROLES = {"inline", "zoomable"}
COVERAGE = {"focused", "complete"}
OUTPUT_STATUS = {"planned", "draft", "reviewed", "approved"}
BEHAVIOR_OUTPUTS = {
    "state_comparison", "interaction_storyboard", "page_interaction_overview",
    "low_fidelity_wireframe", "design_handoff"
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def unique_ids(items: Any, label: str, errors: list[str]) -> set[str]:
    if not isinstance(items, list):
        errors.append(f"{label} must be an array")
        return set()
    ids: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not nonempty(item.get("id")):
            errors.append(f"{label}[{index}].id is required")
            continue
        ids.append(item["id"])
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        errors.append(f"duplicate {label} ids: " + ", ".join(duplicates))
    return set(ids)


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def string_array(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(nonempty(item) for item in value)


def validate(data: dict[str, Any], base: Path, check_files: bool = True) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if not nonempty(data.get("source_prd")):
        errors.append("source_prd is required")
    elif check_files and not resolve_path(data["source_prd"], base).is_file():
        errors.append(f"source_prd file does not exist: {resolve_path(data['source_prd'], base)}")

    readiness = data.get("readiness")
    semantics = visual_context = decision = None
    if not isinstance(readiness, dict):
        errors.append("readiness is required")
    else:
        semantics = readiness.get("product_semantics")
        visual_context = readiness.get("visual_context")
        decision = readiness.get("decision")
        if semantics not in PRODUCT_SEMANTICS:
            errors.append("readiness.product_semantics is unsupported")
        if visual_context not in VISUAL_CONTEXTS:
            errors.append("readiness.visual_context is unsupported")
        if decision not in DECISIONS:
            errors.append("readiness.decision is unsupported")
        missing = readiness.get("missing_facts", [])
        if not isinstance(missing, list):
            errors.append("readiness.missing_facts must be an array")
        if semantics in {"partial", "insufficient"} and decision == "generate":
            errors.append("partial or insufficient product semantics cannot use decision=generate")
        if semantics == "insufficient" and decision not in {"plan_only", "return_upstream"}:
            errors.append("insufficient product semantics must plan only or return upstream")

    evidence = data.get("evidence")
    evidence_ids = unique_ids(evidence, "evidence", errors)
    evidence_by_id: dict[str, dict[str, Any]] = {}
    formal_prd_ids: set[str] = set()
    screenshot_ids: set[str] = set()
    if isinstance(evidence, list):
        for index, item in enumerate(evidence):
            if not isinstance(item, dict) or not nonempty(item.get("id")):
                continue
            evidence_by_id[item["id"]] = item
            if item.get("type") not in EVIDENCE_TYPES:
                errors.append(f"evidence[{index}].type is unsupported")
            if item.get("authority") not in AUTHORITIES:
                errors.append(f"evidence[{index}].authority is unsupported")
            for field in ("path", "status", "scope"):
                if not nonempty(item.get(field)):
                    errors.append(f"evidence[{index}].{field} is required")
            if check_files and nonempty(item.get("path")):
                path = resolve_path(item["path"], base)
                if not path.is_file():
                    errors.append(f"evidence[{index}] file does not exist: {path}")
            if item.get("type") == "formal_prd":
                formal_prd_ids.add(item["id"])
                if item.get("authority") != "product_behavior":
                    errors.append(f"evidence[{index}] formal_prd must have authority=product_behavior")
            if item.get("type") == "screenshot":
                screenshot_ids.add(item["id"])
                if item.get("authority") not in {"observational", "visual_design", "reference"}:
                    errors.append(f"evidence[{index}] screenshot cannot be product_behavior authority")
                if item.get("role") not in SCREENSHOT_ROLES:
                    errors.append(f"evidence[{index}].role is unsupported for screenshot")
                if item.get("sensitive_data") not in {"checked", "redacted", "not_applicable"}:
                    errors.append(f"evidence[{index}].sensitive_data must be checked, redacted, or not_applicable")
                observations = item.get("observations")
                if not isinstance(observations, list) or not observations:
                    errors.append(f"evidence[{index}].observations must be a non-empty array")
                else:
                    seen: set[str] = set()
                    for obs_index, observation in enumerate(observations):
                        if not isinstance(observation, dict):
                            errors.append(f"evidence[{index}].observations[{obs_index}] must be an object")
                            continue
                        obs_id = observation.get("id")
                        if not nonempty(obs_id):
                            errors.append(f"evidence[{index}].observations[{obs_index}].id is required")
                        elif obs_id in seen:
                            errors.append(f"evidence[{index}] has duplicate observation id: {obs_id}")
                        else:
                            seen.add(obs_id)
                        if observation.get("kind") not in OBSERVATION_KINDS:
                            errors.append(f"evidence[{index}].observations[{obs_index}].kind is unsupported")
                        if not nonempty(observation.get("statement")):
                            errors.append(f"evidence[{index}].observations[{obs_index}].statement is required")

    surface_ids = unique_ids(data.get("surfaces"), "surfaces", errors)
    surface_state_ids: dict[str, set[str]] = {}
    surfaces = data.get("surfaces", [])
    if isinstance(surfaces, list):
        for index, surface in enumerate(surfaces):
            if not isinstance(surface, dict):
                continue
            if nonempty(surface.get("id")):
                declared_states = surface.get("state_ids", [])
                if not isinstance(declared_states, list) or not all(nonempty(item) for item in declared_states):
                    errors.append(f"surfaces[{index}].state_ids must be a string array")
                    declared_states = []
                surface_state_ids[surface["id"]] = set(declared_states)
            if not nonempty(surface.get("purpose")):
                errors.append(f"surfaces[{index}].purpose is required")
            if not string_array(surface.get("source_anchors")):
                errors.append(f"surfaces[{index}].source_anchors must be a non-empty string array")
            refs = surface.get("evidence_ids")
            if not string_array(refs):
                errors.append(f"surfaces[{index}].evidence_ids must be a non-empty string array")
                refs = []
            unknown = sorted(set(refs) - evidence_ids)
            if unknown:
                errors.append(f"surfaces[{index}] references unknown evidence: " + ", ".join(unknown))
            reuse = surface.get("design_reuse")
            if not isinstance(reuse, dict):
                errors.append(f"surfaces[{index}].design_reuse is required")
            else:
                strategy = reuse.get("strategy")
                if strategy not in REUSE_STRATEGIES:
                    errors.append(f"surfaces[{index}].design_reuse.strategy is unsupported")
                if not nonempty(reuse.get("rationale")):
                    errors.append(f"surfaces[{index}].design_reuse.rationale is required")
                source_ids = reuse.get("source_ids", [])
                if not isinstance(source_ids, list):
                    errors.append(f"surfaces[{index}].design_reuse.source_ids must be an array")
                    source_ids = []
                unknown_sources = sorted(set(source_ids) - evidence_ids)
                if unknown_sources:
                    errors.append(f"surfaces[{index}] design_reuse references unknown evidence: " + ", ".join(unknown_sources))
                if strategy in {"reuse_confirmed", "adapt_existing", "reference_only"} and not source_ids:
                    errors.append(f"surfaces[{index}] design_reuse.source_ids is required for {strategy}")
                if visual_context == "confirmed_design" and strategy == "low_fidelity_new" and reuse.get("reuse_exception") is not True:
                    errors.append(f"surfaces[{index}] confirmed design cannot be redrawn without reuse_exception=true")
                if visual_context == "declared_unverified" and strategy in {"reuse_confirmed", "adapt_existing"}:
                    errors.append(
                        f"surfaces[{index}] declared but unverified design cannot use strategy={strategy}"
                    )
            regions = surface.get("regions")
            region_ids = unique_ids(regions, f"surfaces[{index}].regions", errors)
            if isinstance(regions, list):
                for region_index, region in enumerate(regions):
                    if not isinstance(region, dict):
                        continue
                    for field in ("purpose", "priority", "visible_content"):
                        if not nonempty(region.get(field)):
                            errors.append(f"surfaces[{index}].regions[{region_index}].{field} is required")
                    if not string_array(region.get("source_anchors")):
                        errors.append(f"surfaces[{index}].regions[{region_index}].source_anchors must be a non-empty string array")
            if not region_ids and semantics in {"interaction_complete", "structure_complete"}:
                warnings.append(f"surface {surface.get('id', index)} has no regions despite stable structure")

    outputs = data.get("outputs")
    output_ids = unique_ids(outputs, "outputs", errors)
    model_states: set[str] = set()
    model_state_map: dict[str, dict[str, Any]] = {}
    model_transitions: set[str] = set()
    model_transition_map: dict[str, dict[str, Any]] = {}
    model: dict[str, Any] = {}
    interaction_model = data.get("interaction_model")
    if nonempty(interaction_model) and check_files:
        model_path = resolve_path(interaction_model, base)
        if not model_path.is_file():
            errors.append(f"interaction_model file does not exist: {model_path}")
        else:
            try:
                model = json.loads(model_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"interaction_model cannot be read: {exc}")
            else:
                if isinstance(model, dict):
                    model_state_map = {
                        item["id"]: item for item in model.get("states", [])
                        if isinstance(item, dict) and nonempty(item.get("id"))
                    }
                    model_states = set(model_state_map)
                    model_transition_map = {
                        item["id"]: item for item in model.get("transitions", [])
                        if isinstance(item, dict) and nonempty(item.get("id"))
                    }
                    model_transitions = set(model_transition_map)
    if isinstance(outputs, list):
        for index, output in enumerate(outputs):
            if not isinstance(output, dict):
                continue
            for field in ("reader_question", "placement", "strategy"):
                if not nonempty(output.get(field)):
                    errors.append(f"outputs[{index}].{field} is required")
            kind = output.get("kind")
            if kind not in OUTPUT_KINDS:
                errors.append(f"outputs[{index}].kind is unsupported")
            if output.get("delivery_role") not in DELIVERY_ROLES:
                errors.append(f"outputs[{index}].delivery_role is unsupported")
            coverage = output.get("coverage")
            if coverage not in COVERAGE:
                errors.append(f"outputs[{index}].coverage is unsupported")
            if output.get("status") not in OUTPUT_STATUS:
                errors.append(f"outputs[{index}].status is unsupported")
            refs = output.get("evidence_ids")
            if not string_array(refs):
                errors.append(f"outputs[{index}].evidence_ids must be a non-empty string array")
                refs = []
            unknown = sorted(set(refs) - evidence_ids)
            if unknown:
                errors.append(f"outputs[{index}] references unknown evidence: " + ", ".join(unknown))
            if not string_array(output.get("source_anchors")):
                errors.append(f"outputs[{index}].source_anchors must be a non-empty string array")
            surface_refs = output.get("surface_ids")
            if not string_array(surface_refs):
                errors.append(f"outputs[{index}].surface_ids must be a non-empty string array")
                surface_refs = []
            unknown_surfaces = sorted(set(surface_refs) - surface_ids)
            if unknown_surfaces:
                errors.append(f"outputs[{index}] references unknown surfaces: " + ", ".join(unknown_surfaces))
            if kind in BEHAVIOR_OUTPUTS and not (set(refs) & formal_prd_ids):
                errors.append(f"outputs[{index}] behavior-bearing prototype requires formal PRD evidence")
            if kind == "annotated_screenshot" and not (set(refs) & screenshot_ids):
                errors.append(f"outputs[{index}] annotated_screenshot requires screenshot evidence")
            if kind in {"page_map", "state_comparison", "low_fidelity_wireframe", "design_handoff"} and semantics not in {"interaction_complete", "structure_complete"}:
                errors.append(f"outputs[{index}] {kind} requires at least structure_complete product semantics")
            if kind == "interaction_storyboard":
                if semantics != "interaction_complete":
                    errors.append(f"outputs[{index}] interaction_storyboard requires interaction_complete product semantics")
                if not nonempty(interaction_model):
                    errors.append(f"outputs[{index}] interaction_storyboard requires interaction_model")
                states = output.get("state_ids")
                transitions = output.get("transition_ids")
                if not string_array(states):
                    errors.append(f"outputs[{index}].state_ids must be a non-empty string array")
                    states = []
                if not string_array(transitions):
                    errors.append(f"outputs[{index}].transition_ids must be a non-empty string array")
                    transitions = []
                if model_states:
                    unknown_states = sorted(set(states) - model_states)
                    if unknown_states:
                        errors.append(f"outputs[{index}] references unknown model states: " + ", ".join(unknown_states))
                if model_transitions:
                    unknown_transitions = sorted(set(transitions) - model_transitions)
                    if unknown_transitions:
                        errors.append(f"outputs[{index}] references unknown model transitions: " + ", ".join(unknown_transitions))
                    selected_states = set(states)
                    selected_transitions = [model_transition_map[item] for item in transitions if item in model_transition_map]
                    outside_pairs = [
                        f"{item.get('id')}:{item.get('from')}->{item.get('to')}"
                        for item in selected_transitions
                        if item.get("from") not in selected_states or item.get("to") not in selected_states
                    ]
                    if outside_pairs:
                        errors.append(
                            f"outputs[{index}] storyboard transitions leave the selected state set: "
                            + ", ".join(outside_pairs)
                        )
                    if states and not outside_pairs:
                        adjacency: dict[str, list[str]] = {item: [] for item in selected_states}
                        for item in selected_transitions:
                            adjacency[item["from"]].append(item["to"])
                        reachable: set[str] = set()
                        queue = [states[0]]
                        while queue:
                            current = queue.pop(0)
                            if current in reachable:
                                continue
                            reachable.add(current)
                            queue.extend(adjacency.get(current, []))
                        missing_story_states = sorted(selected_states - reachable)
                        if missing_story_states:
                            errors.append(
                                f"outputs[{index}] storyboard states are not reachable from {states[0]}: "
                                + ", ".join(missing_story_states)
                            )
                declared_by_surfaces: set[str] = set()
                for surface_id in surface_refs:
                    declared_by_surfaces.update(surface_state_ids.get(surface_id, set()))
                if declared_by_surfaces:
                    undeclared = sorted(set(states) - declared_by_surfaces)
                    if undeclared:
                        errors.append(
                            f"outputs[{index}] states are not declared by selected surfaces: "
                            + ", ".join(undeclared)
                        )
            if kind == "page_interaction_overview":
                if semantics != "interaction_complete":
                    errors.append(
                        f"outputs[{index}] page_interaction_overview requires interaction_complete product semantics"
                    )
                if not nonempty(interaction_model):
                    errors.append(f"outputs[{index}] page_interaction_overview requires interaction_model")
                overview_spec = output.get("overview_spec")
                if not nonempty(overview_spec):
                    errors.append(f"outputs[{index}].overview_spec is required")
                elif check_files:
                    overview_path = resolve_path(overview_spec, base)
                    if not overview_path.is_file():
                        errors.append(f"outputs[{index}] overview_spec file does not exist: {overview_path}")
                    elif model:
                        try:
                            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                            from check_page_interaction_overview import validate as validate_overview

                            overview = json.loads(overview_path.read_text(encoding="utf-8"))
                            if not isinstance(overview, dict):
                                raise ValueError("overview root must be an object")
                            expected_mode = "review_complete" if coverage == "complete" else "focused"
                            if overview.get("coverage_mode") != expected_mode:
                                errors.append(
                                    f"outputs[{index}] coverage={coverage} requires overview coverage_mode={expected_mode}"
                                )
                            overview_errors, _ = validate_overview(overview, model, overview_path.parent)
                        except (OSError, json.JSONDecodeError, ValueError) as exc:
                            errors.append(f"outputs[{index}] overview_spec cannot be read: {exc}")
                        else:
                            errors.extend(
                                f"outputs[{index}] overview_spec: {message}"
                                for message in overview_errors
                            )
            if coverage == "complete" and semantics != "interaction_complete":
                errors.append(f"outputs[{index}] complete coverage requires interaction_complete product semantics")
    if not output_ids and decision in {"generate", "annotate_only"}:
        errors.append("generate or annotate_only decision requires at least one output")

    if semantics == "interaction_complete" and model_state_map and model_transition_map:
        visible_surfaces = {
            item.get("surface_id") for item in model_state_map.values()
            if item.get("visual_required", True) and nonempty(item.get("surface_id"))
        }
        has_cross_surface_transition = any(
            model_state_map.get(item.get("from"), {}).get("surface_id")
            != model_state_map.get(item.get("to"), {}).get("surface_id")
            for item in model_transition_map.values()
            if item.get("from") in model_state_map and item.get("to") in model_state_map
        )
        overview_outputs = [
            item for item in outputs or []
            if isinstance(item, dict) and item.get("kind") == "page_interaction_overview"
        ]
        if len(visible_surfaces) > 1 and has_cross_surface_transition and not overview_outputs:
            reason = data.get("page_interaction_overview_not_applicable")
            if not nonempty(reason):
                errors.append(
                    "multi-page interaction plan requires a page_interaction_overview output "
                    "or a non-empty page_interaction_overview_not_applicable reason"
                )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--no-file-check", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("plan root must be an object")
        errors, warnings = validate(data, args.plan.parent, check_files=not args.no_file_check)
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 2
        print(
            "Prototype plan passed "
            f"({len(data.get('evidence', []))} evidence, "
            f"{len(data.get('surfaces', []))} surfaces, "
            f"{len(data.get('outputs', []))} outputs)"
        )
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

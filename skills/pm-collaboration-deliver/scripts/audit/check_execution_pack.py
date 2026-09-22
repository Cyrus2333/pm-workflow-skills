#!/usr/bin/env python3
"""Validate the internal execution pack for complex PRD collaboration delivery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from check_interaction_model import validate as validate_interaction_model
from check_prototype_plan import validate as validate_prototype_plan


VISUAL_TYPES = {"flowchart", "state", "swimlane", "timeline", "wireframe", "screenshot", "table", "ia"}
VISUAL_ROLES = {"overview", "local", "deep_dive", "supporting", "interaction"}
VISUAL_COVERAGE = {"focused", "complete"}
DELIVERY_ROLES = {"inline", "zoomable"}
RELATION_KINDS = {"sequence", "handoff", "state", "spatial", "condition", "hierarchy", "comparison", "data"}
REPRESENTATIONS = VISUAL_TYPES | {"text", "list"}
CHECK_RESULTS = {"pass", "fail", "not_applicable"}
VALIDATION_LEVELS = {"enhanced", "strict"}
PRIMARY_ARTIFACT_TYPES = {"traditional_prd", "review_brief"}
PRIMARY_SURFACES = {"local", "feishu", "other"}
TECHNICAL_DEPTHS = {"product_only", "collaboration_only", "spec_included"}
REQUIRED_SPINE = {"background_problem", "goal", "scope", "solution", "detail", "acceptance"}


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


def validate(data: dict[str, Any], base: Path, check_files: bool = True) -> list[str]:
    errors: list[str] = []
    if data.get("mode") not in {"visual", "interaction"}:
        errors.append("mode must be visual or interaction for an execution pack")
    validation_level = data.get("validation_level")
    if validation_level not in VALIDATION_LEVELS:
        errors.append("validation_level must be enhanced or strict")
    for field in ("source", "document", "review_task", "mainline"):
        if not nonempty(data.get(field)):
            errors.append(f"{field} is required")
    audience = data.get("audience")
    if not isinstance(audience, list) or not audience or not all(nonempty(item) for item in audience):
        errors.append("audience must be a non-empty string array")

    primary = data.get("primary_artifact")
    if not isinstance(primary, dict):
        errors.append("primary_artifact is required")
    else:
        artifact_type = primary.get("type")
        if artifact_type not in PRIMARY_ARTIFACT_TYPES:
            errors.append("primary_artifact.type is unsupported")
        if artifact_type == "review_brief" and primary.get("explicit_user_request") is not True:
            errors.append("review_brief can be primary only after an explicit user request")
        if primary.get("surface") not in PRIMARY_SURFACES:
            errors.append("primary_artifact.surface is unsupported")
        if primary.get("technical_depth") not in TECHNICAL_DEPTHS:
            errors.append("primary_artifact.technical_depth is unsupported")
        spine = primary.get("reader_spine")
        if not isinstance(spine, list) or not all(nonempty(item) for item in spine):
            errors.append("primary_artifact.reader_spine must be a non-empty string array")
        elif artifact_type == "traditional_prd":
            missing_spine = sorted(REQUIRED_SPINE - set(spine))
            if missing_spine:
                errors.append("traditional_prd reader_spine misses: " + ", ".join(missing_spine))
        secondary = primary.get("secondary_artifacts", [])
        if not isinstance(secondary, list):
            errors.append("primary_artifact.secondary_artifacts must be an array")

    for field in ("source", "document", "interaction_model", "prototype_plan"):
        value = data.get(field)
        if check_files and nonempty(value):
            path = Path(value)
            if not path.is_absolute():
                path = base / path
            if not path.is_file():
                errors.append(f"{field} file does not exist: {path}")

    fact_ids = unique_ids(data.get("facts"), "facts", errors)
    state_ids = unique_ids(data.get("states"), "states", errors)
    visual_ids = unique_ids(data.get("visuals"), "visuals", errors)
    module_ids = unique_ids(data.get("modules", []), "modules", errors)
    if not fact_ids:
        errors.append("at least one high-risk fact is required")
    interaction_model = data.get("interaction_model")
    interaction_planned = any(
        isinstance(item, dict) and item.get("relation_kind") == "state"
        for item in data.get("review_questions", [])
    )
    if interaction_planned and not state_ids and not nonempty(interaction_model):
        errors.append("state-focused review question requires states or interaction_model")
    model_data: dict[str, Any] | None = None
    if nonempty(interaction_model) and check_files:
        model_path = Path(interaction_model)
        if not model_path.is_absolute():
            model_path = base / model_path
        if model_path.is_file():
            try:
                model_data = json.loads(model_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"interaction_model cannot be read: {exc}")
            else:
                if not isinstance(model_data, dict):
                    errors.append("interaction_model root must be an object")
                    model_data = None
                else:
                    model_errors, _ = validate_interaction_model(model_data)
                    errors.extend(f"interaction_model: {item}" for item in model_errors)

    prototype_plan = data.get("prototype_plan")
    if nonempty(prototype_plan) and check_files:
        plan_path = Path(prototype_plan)
        if not plan_path.is_absolute():
            plan_path = base / plan_path
        if plan_path.is_file():
            try:
                plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"prototype_plan cannot be read: {exc}")
            else:
                if not isinstance(plan_data, dict):
                    errors.append("prototype_plan root must be an object")
                else:
                    plan_errors, _ = validate_prototype_plan(plan_data, plan_path.parent, check_files=True)
                    errors.extend(f"prototype_plan: {item}" for item in plan_errors)

    for index, fact in enumerate(data.get("facts", [])):
        if not isinstance(fact, dict):
            continue
        for field in ("statement", "source_anchor", "document_anchor"):
            if not nonempty(fact.get(field)):
                errors.append(f"facts[{index}].{field} is required")
        refs = fact.get("visual_ids", [])
        if not isinstance(refs, list):
            errors.append(f"facts[{index}].visual_ids must be an array")
            refs = []
        unknown = sorted(set(refs) - visual_ids)
        if unknown:
            errors.append(f"facts[{index}] references unknown visuals: " + ", ".join(unknown))
        if fact.get("needs_visual") is True and not refs:
            errors.append(f"facts[{index}] needs visual evidence but visual_ids is empty")

    for index, state in enumerate(data.get("states", [])):
        if not isinstance(state, dict):
            continue
        for field in ("surface", "entry", "visible", "result_or_exit", "recovery", "source_anchor"):
            if not nonempty(state.get(field)):
                errors.append(f"states[{index}].{field} is required")
        actions = state.get("actions")
        if not isinstance(actions, list) or not actions or not all(nonempty(item) for item in actions):
            errors.append(f"states[{index}].actions must be a non-empty string array")
        visual_id = state.get("visual_id")
        if visual_id is not None and visual_id not in visual_ids:
            errors.append(f"states[{index}] references unknown visual: {visual_id}")

    for index, visual in enumerate(data.get("visuals", [])):
        if not isinstance(visual, dict):
            continue
        for field in ("question", "path", "placement"):
            if not nonempty(visual.get(field)):
                errors.append(f"visuals[{index}].{field} is required")
        if visual.get("type") not in VISUAL_TYPES:
            errors.append(f"visuals[{index}].type is unsupported")
        role = visual.get("role")
        if role is not None and role not in VISUAL_ROLES:
            errors.append(f"visuals[{index}].role is unsupported")
        coverage = visual.get("coverage", "focused")
        if coverage not in VISUAL_COVERAGE:
            errors.append(f"visuals[{index}].coverage is unsupported")
        delivery_role = visual.get("delivery_role")
        if delivery_role not in DELIVERY_ROLES:
            errors.append(f"visuals[{index}].delivery_role is required and must be inline or zoomable")
        anchors = visual.get("source_anchors")
        if not isinstance(anchors, list) or not anchors or not all(nonempty(item) for item in anchors):
            errors.append(f"visuals[{index}].source_anchors must be a non-empty string array")
        if check_files and nonempty(visual.get("path")):
            path = Path(visual["path"])
            if not path.is_absolute():
                path = base / path
            if not path.is_file():
                errors.append(f"visuals[{index}] file does not exist: {path}")
            else:
                if path.stat().st_size == 0:
                    errors.append(f"visuals[{index}] file is empty: {path}")
                if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".svg", ".html", ".webp", ".gif", ".mmd"}:
                    errors.append(f"visuals[{index}] file is not a renderable visual format: {path.name}")
                spec_value = visual.get("spec_path")
                if nonempty(spec_value):
                    spec_path = Path(spec_value)
                    if not spec_path.is_absolute():
                        spec_path = base / spec_path
                    if spec_path.is_file() and path.stat().st_mtime < spec_path.stat().st_mtime:
                        errors.append(
                            f"visuals[{index}] render is stale: {path.name} is older than its spec {spec_path.name}"
                        )
        # A low-fidelity wireframe board that claims to carry interaction must
        # expose checkable nodes and links. A state/process diagram can carry
        # interaction semantics through its own graph source and therefore is
        # not forced into the wireframe-board schema.
        needs_wireframe_spec = (
            visual.get("type") == "wireframe"
            and (
                visual.get("role") in {"interaction", "deep_dive"}
                or visual.get("relation_kind") in {"sequence", "state"}
            )
        )
        if needs_wireframe_spec:
            spec_value = visual.get("spec_path")
            if not nonempty(spec_value):
                errors.append(f"visuals[{index}].spec_path is required for a wireframe interaction asset")
            elif check_files:
                spec_path = Path(spec_value)
                if not spec_path.is_absolute():
                    spec_path = base / spec_path
                if not spec_path.is_file():
                    errors.append(f"visuals[{index}] interaction spec does not exist: {spec_path}")
                else:
                    try:
                        board_spec = json.loads(spec_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        errors.append(f"visuals[{index}] interaction spec cannot be read: {exc}")
                    else:
                        if not isinstance(board_spec, dict):
                            errors.append(f"visuals[{index}] interaction spec root must be an object")
                        else:
                            board_ids = {
                                item.get("id") for item in board_spec.get("boards", [])
                                if isinstance(item, dict) and nonempty(item.get("id"))
                            }
                            links = board_spec.get("links")
                            if not isinstance(links, list) or not links:
                                errors.append(f"visuals[{index}] interaction board has no transition links")
                                links = []
                            visual_pairs = {
                                (item.get("from"), item.get("to")) for item in links
                                if isinstance(item, dict) and nonempty(item.get("from"))
                                and nonempty(item.get("to")) and nonempty(item.get("label"))
                            }
                            if model_data is not None and coverage == "complete":
                                state_to_board: dict[str, str] = {}
                                for state in model_data.get("states", []):
                                    if not isinstance(state, dict) or state.get("visual_required") is False:
                                        continue
                                    ref = state.get("visual_ref")
                                    if nonempty(ref) and "#" in ref:
                                        state_to_board[state.get("id")] = ref.rsplit("#", 1)[1]
                                missing_boards = sorted(set(state_to_board.values()) - board_ids)
                                if missing_boards:
                                    errors.append(
                                        f"visuals[{index}] interaction board misses modeled states: "
                                        + ", ".join(missing_boards)
                                    )
                                required_pairs = {
                                    (state_to_board.get(item.get("from")), state_to_board.get(item.get("to")))
                                    for item in model_data.get("transitions", []) if isinstance(item, dict)
                                    and item.get("from") in state_to_board and item.get("to") in state_to_board
                                }
                                missing_pairs = sorted(pair for pair in required_pairs if pair not in visual_pairs)
                                if missing_pairs:
                                    rendered = ", ".join(f"{left}->{right}" for left, right in missing_pairs)
                                    errors.append(
                                        f"visuals[{index}] interaction board misses modeled transition pairs: {rendered}"
                                    )
                            elif model_data is not None and coverage == "focused":
                                state_refs = visual.get("state_ids")
                                transition_refs = visual.get("transition_ids")
                                if not isinstance(state_refs, list) or not state_refs:
                                    errors.append(f"visuals[{index}].state_ids is required for focused model coverage")
                                    state_refs = []
                                if not isinstance(transition_refs, list):
                                    errors.append(f"visuals[{index}].transition_ids must be an array")
                                    transition_refs = []
                                known_states = {
                                    item.get("id") for item in model_data.get("states", [])
                                    if isinstance(item, dict) and nonempty(item.get("id"))
                                }
                                known_transitions = {
                                    item.get("id") for item in model_data.get("transitions", [])
                                    if isinstance(item, dict) and nonempty(item.get("id"))
                                }
                                unknown_states = sorted(set(state_refs) - known_states)
                                unknown_transitions = sorted(set(transition_refs) - known_transitions)
                                if unknown_states:
                                    errors.append(f"visuals[{index}] references unknown model states: " + ", ".join(unknown_states))
                                if unknown_transitions:
                                    errors.append(f"visuals[{index}] references unknown model transitions: " + ", ".join(unknown_transitions))

    question_ids = unique_ids(data.get("review_questions", []), "review_questions", errors)
    for index, question in enumerate(data.get("review_questions", [])):
        if not isinstance(question, dict):
            continue
        for field in ("question", "scope", "rationale", "validation"):
            if not nonempty(question.get(field)):
                errors.append(f"review_questions[{index}].{field} is required")
        anchors = question.get("source_anchors")
        if not isinstance(anchors, list) or not anchors or not all(nonempty(item) for item in anchors):
            errors.append(f"review_questions[{index}].source_anchors must be a non-empty string array")
        if question.get("relation_kind") not in RELATION_KINDS:
            errors.append(f"review_questions[{index}].relation_kind is unsupported")
        if question.get("representation") not in REPRESENTATIONS:
            errors.append(f"review_questions[{index}].representation is unsupported")
        visual_ref = question.get("visual_id")
        if visual_ref is not None and visual_ref not in visual_ids:
            errors.append(f"review_questions[{index}] references unknown visual: {visual_ref}")

    reader_test = data.get("reader_test")
    if not isinstance(reader_test, dict):
        errors.append("reader_test is required")
    else:
        if not nonempty(reader_test.get("reader_context")):
            errors.append("reader_test.reader_context is required")
        if reader_test.get("reader_type") not in {"author", "independent"}:
            errors.append("reader_test.reader_type must be author or independent")
        if validation_level == "strict" and reader_test.get("reader_type") != "independent":
            errors.append("strict validation requires an independent reader_test")
        reader_questions = reader_test.get("questions")
        if not isinstance(reader_questions, list) or not reader_questions:
            errors.append("reader_test.questions must be a non-empty array")
            reader_questions = []
        tested_ids: list[str] = []
        for index, item in enumerate(reader_questions):
            if not isinstance(item, dict):
                errors.append(f"reader_test.questions[{index}] must be an object")
                continue
            question_id = item.get("question_id")
            if question_id not in question_ids:
                errors.append(f"reader_test.questions[{index}] references unknown review question")
            else:
                tested_ids.append(question_id)
            if item.get("result") not in {"pass", "fail"}:
                errors.append(f"reader_test.questions[{index}].result must be pass or fail")
            for field in ("reader_answer", "gap"):
                if not nonempty(item.get(field)):
                    errors.append(f"reader_test.questions[{index}].{field} is required")
        untested = sorted(question_ids - set(tested_ids))
        if untested:
            errors.append("reader_test does not cover review questions: " + ", ".join(untested))
        if any(isinstance(item, dict) and item.get("result") == "fail" for item in reader_questions):
            errors.append("reader_test contains failed review questions")
        for field in ("ambiguities", "hidden_assumptions", "contradictions"):
            if not isinstance(reader_test.get(field), list):
                errors.append(f"reader_test.{field} must be an array")
            elif reader_test.get(field):
                errors.append(f"reader_test.{field} must be resolved before delivery")

    render_check = data.get("render_check")
    if not isinstance(render_check, dict):
        errors.append("render_check is required")
    else:
        for field in ("target", "checked_at"):
            if not nonempty(render_check.get(field)):
                errors.append(f"render_check.{field} is required")
        checks = render_check.get("checks")
        required_checks = {
            "document_structure", "visual_legibility", "cross_references", "asset_integrity",
            "information_hierarchy", "terminology_layering", "inline_readability", "zoom_readability"
        }
        if not isinstance(checks, dict):
            errors.append("render_check.checks must be an object")
        else:
            for key in required_checks:
                if checks.get(key) not in CHECK_RESULTS:
                    errors.append(f"render_check.checks.{key} must be pass, fail, or not_applicable")
            failed = sorted(key for key, value in checks.items() if value == "fail")
            if failed:
                errors.append("render_check contains failures: " + ", ".join(failed))
            inline_visuals = [item for item in data.get("visuals", []) if isinstance(item, dict) and item.get("delivery_role") == "inline"]
            zoom_visuals = [item for item in data.get("visuals", []) if isinstance(item, dict) and item.get("delivery_role") == "zoomable"]
            if inline_visuals and checks.get("inline_readability") != "pass":
                errors.append("inline visuals require render_check.checks.inline_readability=pass")
            if zoom_visuals and checks.get("zoom_readability") != "pass":
                errors.append("zoomable visuals require render_check.checks.zoom_readability=pass")
        issues = render_check.get("issues")
        if not isinstance(issues, list):
            errors.append("render_check.issues must be an array")
        elif issues:
            errors.append("render_check.issues must be resolved before delivery")

    for index, visual in enumerate(data.get("visuals", [])):
        if not isinstance(visual, dict):
            continue
        question_ref = visual.get("review_question_id")
        if question_ids and question_ref not in question_ids:
            errors.append(f"visuals[{index}] must reference a known review question")
        for field in ("scope", "rationale", "validation"):
            if question_ids and not nonempty(visual.get(field)):
                errors.append(f"visuals[{index}].{field} is required when review_questions are present")
        if question_ids and visual.get("relation_kind") not in RELATION_KINDS:
            errors.append(f"visuals[{index}].relation_kind is unsupported")

    modules = data.get("modules", [])
    assigned_facts: list[str] = []
    if modules:
        for index, module in enumerate(modules):
            if not isinstance(module, dict):
                continue
            if not nonempty(module.get("title")):
                errors.append(f"modules[{index}].title is required")
            refs = module.get("fact_ids")
            if not isinstance(refs, list) or not refs:
                errors.append(f"modules[{index}].fact_ids must be a non-empty array")
                refs = []
            unknown = sorted(set(refs) - fact_ids)
            if unknown:
                errors.append(f"modules[{index}] references unknown facts: " + ", ".join(unknown))
            assigned_facts.extend(refs)
            visual_refs = module.get("visual_ids", [])
            if not isinstance(visual_refs, list):
                errors.append(f"modules[{index}].visual_ids must be an array")
                visual_refs = []
            unknown_visuals = sorted(set(visual_refs) - visual_ids)
            if unknown_visuals:
                errors.append(f"modules[{index}] references unknown visuals: " + ", ".join(unknown_visuals))
        duplicate_facts = sorted({item for item in assigned_facts if assigned_facts.count(item) > 1})
        if duplicate_facts:
            errors.append("facts must have one primary module owner: " + ", ".join(duplicate_facts))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--skip-file-checks", action="store_true")
    args = parser.parse_args()
    if not args.pack.is_file():
        print(f"error: file does not exist: {args.pack}", file=sys.stderr)
        return 2
    try:
        data = json.loads(args.pack.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("error: execution pack root must be an object", file=sys.stderr)
        return 2
    errors = validate(data, args.pack.parent, not args.skip_file_checks)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 2
    print("Execution pack checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

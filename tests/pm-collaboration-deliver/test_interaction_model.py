#!/usr/bin/env python3
"""Regression tests for the interaction-model gate."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


CHECKER = (
    Path(__file__).resolve().parents[2]
    / "skills" / "pm-collaboration-deliver" / "scripts" / "audit" / "check_interaction_model.py"
)


def base_model() -> dict:
    return {
        "schema_version": "2.0",
        "coverage": {
            "entry_state_ids": ["S-ENTRY"],
            "required_state_types": ["entry", "ready", "processing", "success", "failure"],
        },
        "surfaces": [
            {"id": "P-ENTRY", "name": "入口"},
            {"id": "P-FORM", "name": "表单"},
            {"id": "P-RESULT", "name": "结果"},
        ],
        "states": [
            {"id": "S-ENTRY", "name": "入口", "surface_id": "P-ENTRY", "type": "entry",
             "entry": "收到入口", "visible": "入口卡片", "actions": [{"id": "A-OPEN", "label": "打开"}],
             "source_anchor": "FR-01", "visual_ref": "V-ENTRY"},
            {"id": "S-READY", "name": "可提交", "surface_id": "P-FORM", "type": "ready",
             "entry": "打开成功", "visible": "表单和提交按钮", "actions": [{"id": "A-SUBMIT", "label": "提交"}],
             "source_anchor": "FR-02", "visual_ref": "V-READY"},
            {"id": "S-PROCESS", "name": "提交中", "surface_id": "P-FORM", "type": "processing",
             "entry": "点击提交", "visible": "处理中且按钮禁用", "actions": [],
             "source_anchor": "FR-02", "visual_ref": "V-PROCESS"},
            {"id": "S-SUCCESS", "name": "成功", "surface_id": "P-RESULT", "type": "success",
             "entry": "明确成功", "visible": "成功结果", "actions": [], "terminal": True,
             "source_anchor": "FR-03", "visual_ref": "V-SUCCESS"},
            {"id": "S-FAIL", "name": "失败", "surface_id": "P-RESULT", "type": "failure",
             "entry": "提交失败", "visible": "失败结果", "actions": [], "terminal": True,
             "source_anchor": "FR-03", "visual_ref": "V-FAIL"},
        ],
        "transitions": [
            {"id": "T-OPEN", "from": "S-ENTRY", "to": "S-READY", "trigger": "点击打开",
             "kind": "user", "action_id": "A-OPEN", "source_anchor": "FR-01"},
            {"id": "T-SUBMIT", "from": "S-READY", "to": "S-PROCESS", "trigger": "点击提交",
             "kind": "user", "action_id": "A-SUBMIT", "source_anchor": "FR-02"},
            {"id": "T-OK", "from": "S-PROCESS", "to": "S-SUCCESS", "trigger": "明确成功",
             "kind": "system", "outcome": "success", "source_anchor": "FR-03"},
            {"id": "T-FAIL", "from": "S-PROCESS", "to": "S-FAIL", "trigger": "返回失败或结果不明",
             "kind": "system", "outcome": "failure", "source_anchor": "FR-03"},
        ],
    }


class InteractionModelTest(unittest.TestCase):
    def run_model(self, model: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.json"
            path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
            return subprocess.run(
                ["python3", str(CHECKER), "--model", str(path)], capture_output=True, text=True
            )

    def test_complete_model_passes(self) -> None:
        result = self.run_model(base_model())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("5 states", result.stdout)

    def test_enabled_action_requires_transition(self) -> None:
        model = base_model()
        model["transitions"] = [x for x in model["transitions"] if x["id"] != "T-SUBMIT"]
        result = self.run_model(model)
        self.assertEqual(result.returncode, 2)
        self.assertIn("enabled action has no transition: A-SUBMIT", result.stderr)

    def test_processing_requires_success_and_failure(self) -> None:
        model = base_model()
        model["transitions"] = [x for x in model["transitions"] if x["id"] != "T-FAIL"]
        result = self.run_model(model)
        self.assertEqual(result.returncode, 2)
        self.assertIn("misses outcomes: failure", result.stderr)

    def test_unreachable_state_fails(self) -> None:
        model = base_model()
        model["states"].append(
            {"id": "S-ORPHAN", "name": "孤立状态", "surface_id": "P-RESULT", "type": "blocked",
             "entry": "未知", "visible": "拦截", "actions": [], "terminal": True,
             "source_anchor": "FR-04", "visual_ref": "V-ORPHAN"}
        )
        result = self.run_model(model)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unreachable states: S-ORPHAN", result.stderr)

    def test_non_terminal_requires_exit(self) -> None:
        model = base_model()
        for state in model["states"]:
            if state["id"] == "S-FAIL":
                state["terminal"] = False
        result = self.run_model(model)
        self.assertEqual(result.returncode, 2)
        self.assertIn("non-terminal state has no outgoing transition: S-FAIL", result.stderr)

    def test_visual_reference_is_required(self) -> None:
        model = base_model()
        del model["states"][1]["visual_ref"]
        result = self.run_model(model)
        self.assertEqual(result.returncode, 2)
        self.assertIn("state S-READY requires visual_ref", result.stderr)


if __name__ == "__main__":
    unittest.main()

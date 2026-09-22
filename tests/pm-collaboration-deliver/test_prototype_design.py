#!/usr/bin/env python3
"""Regression tests for prototype readiness and screenshot annotation."""

from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skills" / "pm-collaboration-deliver" / "scripts"
CHECKER = ROOT / "audit" / "check_prototype_plan.py"
ANNOTATOR = ROOT / "annotate_reference_screenshot.py"


class PrototypeDesignTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.prd = self.work / "prd.md"
        self.prd.write_text("# 正式 PRD\n", encoding="utf-8")
        self.image = self.work / "screen.png"
        self.image.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ))
        self.model = self.work / "model.json"
        self.model.write_text(json.dumps({
            "surfaces": [{"id": "PAGE-1"}],
            "states": [
                {"id": "S-READY", "surface_id": "PAGE-1", "visual_required": True},
                {"id": "S-SUCCESS", "surface_id": "PAGE-1", "visual_required": True, "terminal": True},
            ],
            "transitions": [{
                "id": "T-SUBMIT", "from": "S-READY", "to": "S-SUCCESS",
                "action_id": "A-SUBMIT",
            }],
            "coverage": {"entry_state_ids": ["S-READY"]},
        }), encoding="utf-8")
        self.overview_svg = self.work / "overview.svg"
        self.overview_svg.write_text("<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>", encoding="utf-8")
        self.overview_png = self.work / "overview.png"
        self.overview_png.write_bytes(self.image.read_bytes())
        self.overview = self.work / "overview.json"
        self.overview.write_text(json.dumps({
            "schema_version": "1.0",
            "kind": "page_interaction_overview",
            "question": "用户如何从入口进入成功结果",
            "interaction_model": str(self.model),
            "coverage_mode": "review_complete",
            "delivery_role": "zoomable",
            "reading_direction": "left_to_right",
            "cards": [
                {"id": "C-READY", "title": "待确认", "kind": "entry",
                 "state_ids": ["S-READY"], "surface_ids": ["PAGE-1"],
                 "screen": {"task": "确认", "key_content": ["课程信息"], "actions": ["提交"], "visible_feedback": "待提交"},
                 "visual_ref": "overview.svg#ready"},
                {"id": "C-SUCCESS", "title": "成功", "kind": "result",
                 "state_ids": ["S-SUCCESS"], "surface_ids": ["PAGE-1"],
                 "screen": {"task": "确认结果", "key_content": ["成功结果"], "actions": [], "visible_feedback": "提交成功"},
                 "visual_ref": "overview.svg#success"},
            ],
            "connectors": [{
                "id": "E-SUBMIT", "from_card": "C-READY", "to_card": "C-SUCCESS",
                "label": "确认提交", "kind": "primary", "transition_ids": ["T-SUBMIT"],
            }],
            "render": {"source_path": str(self.overview_svg), "preview_path": str(self.overview_png)},
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def plan(self) -> dict:
        return {
            "schema_version": "1.0",
            "source_prd": str(self.prd),
            "interaction_model": str(self.model),
            "readiness": {
                "product_semantics": "interaction_complete",
                "visual_context": "existing_ui",
                "decision": "generate",
                "missing_facts": [],
            },
            "evidence": [
                {"id": "E-PRD", "type": "formal_prd", "path": str(self.prd),
                 "authority": "product_behavior", "status": "confirmed", "scope": "产品行为"},
                {"id": "E-SCREEN", "type": "screenshot", "path": str(self.image),
                 "authority": "observational", "role": "current_ui", "status": "confirmed",
                 "scope": "现状页面", "sensitive_data": "checked",
                 "observations": [{"id": "OBS-1", "kind": "observed", "statement": "存在主操作"}]},
            ],
            "surfaces": [{
                "id": "PAGE-1", "purpose": "完成任务", "source_anchors": ["PAGE-01"],
                "evidence_ids": ["E-PRD", "E-SCREEN"],
                "design_reuse": {"strategy": "adapt_existing", "source_ids": ["E-SCREEN"],
                                 "rationale": "沿用现状页面壳"},
                "regions": [{"id": "IA-1", "purpose": "展示信息", "priority": "primary",
                             "visible_content": "课程信息", "source_anchors": ["IA-01"]}],
                "state_ids": ["S-READY", "S-SUCCESS"], "action_ids": ["A-SUBMIT"],
            }],
            "outputs": [{
                "id": "P-1", "reader_question": "用户如何完成任务", "kind": "interaction_storyboard",
                "surface_ids": ["PAGE-1"], "state_ids": ["S-READY", "S-SUCCESS"],
                "transition_ids": ["T-SUBMIT"], "evidence_ids": ["E-PRD", "E-SCREEN"],
                "source_anchors": ["FR-01"], "coverage": "focused", "delivery_role": "inline",
                "placement": "需求详情", "strategy": "adapt_existing", "status": "planned",
            }],
        }

    def run_plan(self, data: dict) -> subprocess.CompletedProcess[str]:
        path = self.work / "plan.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(["python3", str(CHECKER), "--plan", str(path)], capture_output=True, text=True)

    def overview_output(self) -> dict:
        return {
            "id": "P-OVERVIEW",
            "reader_question": "页面与状态之间如何跳转",
            "kind": "page_interaction_overview",
            "surface_ids": ["PAGE-1"],
            "evidence_ids": ["E-PRD", "E-SCREEN"],
            "source_anchors": ["FR-01"],
            "coverage": "complete",
            "delivery_role": "zoomable",
            "placement": "产品方案 / 页面交互总览",
            "strategy": "adapt_existing",
            "status": "planned",
            "overview_spec": str(self.overview),
        }

    def test_interaction_complete_plan_passes(self) -> None:
        result = self.run_plan(self.plan())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 evidence, 1 surfaces, 1 outputs", result.stdout)

    def test_screenshot_does_not_authorize_hidden_interaction(self) -> None:
        data = self.plan()
        data["readiness"]["product_semantics"] = "partial"
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("partial or insufficient product semantics cannot use decision=generate", result.stderr)
        self.assertIn("interaction_storyboard requires interaction_complete", result.stderr)

    def test_behavior_prototype_requires_formal_prd_evidence(self) -> None:
        data = self.plan()
        data["outputs"][0]["evidence_ids"] = ["E-SCREEN"]
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires formal PRD evidence", result.stderr)

    def test_confirmed_design_requires_reuse_or_explicit_exception(self) -> None:
        data = self.plan()
        data["readiness"]["visual_context"] = "confirmed_design"
        data["surfaces"][0]["design_reuse"] = {
            "strategy": "low_fidelity_new", "source_ids": [], "rationale": "重新绘制"
        }
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot be redrawn without reuse_exception=true", result.stderr)

    def test_declared_unverified_design_is_preserved_without_fake_reuse(self) -> None:
        data = self.plan()
        data["readiness"]["visual_context"] = "declared_unverified"
        data["surfaces"][0]["design_reuse"] = {
            "strategy": "low_fidelity_new", "source_ids": [],
            "rationale": "正式 PRD 声明已有原型但本轮不可访问，仅生成结构示意",
        }
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 0, result.stderr)

        data["surfaces"][0]["design_reuse"] = {
            "strategy": "adapt_existing", "source_ids": ["E-SCREEN"],
            "rationale": "未核验却声称沿用",
        }
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("declared but unverified design cannot use strategy=adapt_existing", result.stderr)

    def test_storyboard_transition_must_connect_selected_states(self) -> None:
        data = self.plan()
        data["outputs"][0]["state_ids"] = ["S-READY"]
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("storyboard transitions leave the selected state set", result.stderr)

    def test_page_interaction_overview_is_a_validated_plan_output(self) -> None:
        data = self.plan()
        data["outputs"].append(self.overview_output())
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 outputs", result.stdout)

    def test_page_interaction_overview_requires_spec_and_matching_coverage(self) -> None:
        data = self.plan()
        output = self.overview_output()
        output["coverage"] = "focused"
        data["outputs"].append(output)
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires overview coverage_mode=focused", result.stderr)

        output.pop("overview_spec")
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("overview_spec is required", result.stderr)

    def test_page_interaction_overview_spec_is_checked_against_model(self) -> None:
        overview = json.loads(self.overview.read_text(encoding="utf-8"))
        overview["connectors"] = []
        self.overview.write_text(json.dumps(overview), encoding="utf-8")
        data = self.plan()
        data["outputs"].append(self.overview_output())
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("overview misses action transitions: T-SUBMIT", result.stderr)

    def test_multi_page_interaction_cannot_silently_omit_overview(self) -> None:
        model = json.loads(self.model.read_text(encoding="utf-8"))
        model["surfaces"].append({"id": "PAGE-2"})
        model["states"][1]["surface_id"] = "PAGE-2"
        self.model.write_text(json.dumps(model), encoding="utf-8")
        result = self.run_plan(self.plan())
        self.assertEqual(result.returncode, 2)
        self.assertIn("multi-page interaction plan requires a page_interaction_overview", result.stderr)

    def test_multi_page_interaction_may_record_auditable_not_applicable_reason(self) -> None:
        model = json.loads(self.model.read_text(encoding="utf-8"))
        model["surfaces"].append({"id": "PAGE-2"})
        model["states"][1]["surface_id"] = "PAGE-2"
        self.model.write_text(json.dumps(model), encoding="utf-8")
        data = self.plan()
        data["page_interaction_overview_not_applicable"] = "只有一次线性跳转，局部故事板已能完整回答读者问题。"
        result = self.run_plan(data)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_annotated_screenshot_is_self_contained(self) -> None:
        spec = self.work / "annotations.json"
        spec.write_text(json.dumps({
            "title": "现状页面标注", "image": str(self.image), "role": "current_ui",
            "sensitive_data": "checked",
            "annotations": [{"id": "A-1", "kind": "observed", "label": "主操作",
                             "description": "页面底部存在一个主按钮",
                             "x": 0.1, "y": 0.1, "width": 0.8, "height": 0.3}],
        }, ensure_ascii=False), encoding="utf-8")
        svg = self.work / "annotated.svg"
        result = subprocess.run(
            ["python3", str(ANNOTATOR), "--spec", str(spec), "--out", str(svg)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = svg.read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64", rendered)
        self.assertIn("页面底部存在一个主按钮", rendered)
        self.assertIn("可观察", rendered)


if __name__ == "__main__":
    unittest.main()

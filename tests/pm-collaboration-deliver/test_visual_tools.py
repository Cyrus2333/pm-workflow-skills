#!/usr/bin/env python3
"""Regression tests for the generic visual production and assembly tools."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skills" / "pm-collaboration-deliver" / "scripts"
RENDERER = ROOT / "render_wireframe_board.py"
PACK_CHECKER = ROOT / "audit" / "check_execution_pack.py"
THEME = Path(__file__).resolve().parent / "black-white-wireframe-theme.json"


class VisualToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_json(self, name: str, value: object) -> Path:
        path = self.work / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def primary_artifact(self) -> dict[str, object]:
        return {
            "type": "traditional_prd",
            "surface": "local",
            "reader_spine": ["background_problem", "goal", "scope", "solution", "detail", "acceptance"],
            "technical_depth": "collaboration_only",
            "secondary_artifacts": [],
        }

    def render_checks(self) -> dict[str, str]:
        return {
            "document_structure": "pass", "visual_legibility": "pass",
            "cross_references": "pass", "asset_integrity": "pass",
            "information_hierarchy": "pass", "terminology_layering": "pass",
            "inline_readability": "pass", "zoom_readability": "not_applicable",
        }

    def test_render_multi_state_board_and_png(self) -> None:
        spec = self.write_json(
            "board.json",
            {
                "title": "评价表单状态",
                "boards": [
                    {
                        "id": "empty",
                        "title": "未填写",
                        "nav": "评价",
                        "blocks": [
                            {"type": "scale", "label": "课程内容", "selected": 2},
                            {"type": "chips", "label": "原因", "items": ["太长", "没学会"],
                             "selected": ["太长"]},
                            {"type": "button", "text": "提交评价", "enabled": False},
                        ],
                    },
                    {
                        "id": "failed",
                        "title": "提交失败",
                        "nav": "评价",
                        "blocks": [
                            {"type": "state", "title": "提交失败", "body": "保留输入，可重试"},
                            {"type": "button", "text": "重新提交"},
                        ],
                    },
                ],
                "links": [{"from": "empty", "to": "failed", "label": "失败"}],
            },
        )
        svg = self.work / "board.svg"
        png = self.work / "board.png"
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--theme", str(THEME),
             "--out", str(svg), "--png", str(png)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("评价表单状态", svg.read_text(encoding="utf-8"))
        self.assertNotIn(">。</text>", svg.read_text(encoding="utf-8"))
        self.assertTrue(png.is_file())
        self.assertGreater(png.stat().st_size, 1000)

    def test_reject_unknown_link(self) -> None:
        spec = self.write_json(
            "bad.json",
            {"boards": [{"id": "a", "title": "A", "blocks": []}],
             "links": [{"from": "a", "to": "missing", "label": "打开"}]},
        )
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(self.work / "bad.svg")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown board", result.stderr)

    def test_interaction_board_rejects_unreachable_state(self) -> None:
        spec = self.write_json(
            "unreachable.json",
            {
                "entry_board_ids": ["a"],
                "boards": [
                    {"id": "a", "title": "入口", "blocks": []},
                    {"id": "b", "title": "孤立状态", "blocks": []},
                ],
                "links": [],
            },
        )
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(self.work / "unreachable.svg")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unreachable boards: b", result.stderr)

    def test_interaction_board_requires_transition_label(self) -> None:
        spec = self.write_json(
            "unlabeled.json",
            {"boards": [{"id": "a", "title": "A", "blocks": []},
                        {"id": "b", "title": "B", "blocks": []}],
             "links": [{"from": "a", "to": "b"}]},
        )
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(self.work / "unlabeled.svg")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("label is required", result.stderr)

    def test_wireframe_rejects_small_fixed_height_instead_of_clipping(self) -> None:
        spec = self.write_json(
            "overflow.json",
            {"board_height": 200, "boards": [{"id": "a", "title": "A", "blocks": [
                {"type": "text", "text": "这是一段需要完整显示而不能静默截断的较长页面说明。" * 8}
            ]}]},
        )
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(self.work / "overflow.svg")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("too small", result.stderr)

    def test_inline_board_rejects_unreadable_final_width_without_node_thresholds(self) -> None:
        spec = self.write_json(
            "too-wide-inline.json",
            {
                "delivery_role": "inline",
                "target_width": 900,
                "columns": 4,
                "boards": [
                    {"id": f"s-{index}", "title": f"状态 {index}", "blocks": []}
                    for index in range(8)
                ],
                "links": [],
            },
        )
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(self.work / "wide.svg")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("inline board would render text", result.stderr)
        self.assertIn("focused storyboards", result.stderr)

    def test_same_large_board_can_be_zoomable(self) -> None:
        spec = self.write_json(
            "zoomable.json",
            {
                "delivery_role": "zoomable",
                "columns": 4,
                "boards": [
                    {"id": f"s-{index}", "title": f"状态 {index}", "blocks": []}
                    for index in range(8)
                ],
                "links": [],
            },
        )
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(self.work / "zoomable.svg")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_render_reusable_tabs_card_annotation_and_secondary_button(self) -> None:
        spec = self.write_json(
            "components.json",
            {
                "title": "通用组件组合",
                "boards": [{
                    "id": "list",
                    "title": "列表页",
                    "nav": "活动",
                    "blocks": [
                        {"type": "tabs", "items": ["全部", "已通过", "未通过"],
                         "selected": "已通过"},
                        {"type": "card", "title": "示例对象", "body": "用于验证通用卡片配方",
                         "fields": [{"label": "状态", "value": "已通过"}], "action": "查看详情"},
                        {"type": "annotation", "label": "去向", "text": "点击后进入详情页"},
                        {"type": "button", "text": "返回", "style": "secondary"},
                    ],
                }],
            },
        )
        svg = self.work / "components.svg"
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(svg)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = svg.read_text(encoding="utf-8")
        self.assertIn("已通过", rendered)
        self.assertIn("查看详情", rendered)
        self.assertIn("点击后进入详情页", rendered)
        self.assertRegex(rendered, r'fill="#ffffff" stroke="#8c8c8c"')
        self.assertIn('y="114"', rendered)

    def test_storyboard_supports_steps_and_progress(self) -> None:
        spec = self.write_json(
            "storyboard.json",
            {
                "delivery_role": "inline", "target_width": 1100, "columns": 2,
                "boards": [
                    {"id": "ready", "step": 1, "title": "准备下载", "blocks": [
                        {"type": "button", "text": "下载"}
                    ]},
                    {"id": "downloading", "step": 2, "title": "下载中", "blocks": [
                        {"type": "progress", "label": "下载进度", "value": 42,
                         "caption": "离开页面后继续下载"}
                    ]},
                ],
                "links": [{"from": "ready", "to": "downloading", "label": "点击下载"}],
            },
        )
        svg = self.work / "storyboard.svg"
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(svg)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = svg.read_text(encoding="utf-8")
        self.assertIn("42%", rendered)
        self.assertIn("点击下载", rendered)
        self.assertRegex(rendered, r'<circle cx="63" cy="109"')

    def test_storyboard_rejects_link_through_unrelated_page(self) -> None:
        spec = self.write_json(
            "cross-page.json",
            {
                "boards": [
                    {"id": "source", "title": "来源", "blocks": []},
                    {"id": "middle", "title": "中间页面", "blocks": []},
                    {"id": "target", "title": "目标", "blocks": []},
                ],
                "links": [{"from": "source", "to": "target", "label": "分支"}],
            },
        )
        result = subprocess.run(
            ["python3", str(RENDERER), "--spec", str(spec), "--out", str(self.work / "cross.svg")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("crosses board middle", result.stderr)
        self.assertIn("explicit layout or split", result.stderr)

    def test_execution_pack_requires_complete_state_and_visual_evidence(self) -> None:
        source = self.work / "formal.md"
        document = self.work / "traditional.md"
        visual = self.work / "flow.svg"
        source.write_text("# 正式 PRD\n", encoding="utf-8")
        document.write_text("# 传统 PRD\n", encoding="utf-8")
        visual.write_text("<svg/>", encoding="utf-8")
        pack = self.write_json("pack.json", {
            "mode": "visual",
            "validation_level": "enhanced",
            "primary_artifact": self.primary_artifact(),
            "source": str(source),
            "document": str(document),
            "audience": ["产品", "研发"],
            "review_task": "理解用户从入口到失败恢复的路径",
            "mainline": "入口 → 选择 → 提交 → 成功",
            "review_questions": [{"id": "Q-01", "question": "提交失败后如何恢复",
                "source_anchors": ["FR-01"], "relation_kind": "sequence",
                "representation": "flowchart", "scope": "提交与失败恢复",
                "rationale": "需要表达顺序和结果", "validation": "逐边核对并预览",
                "visual_id": "VIS-01"}],
            "reader_test": {"reader_type": "author", "reader_context": "只读成稿", "questions": [{"question_id": "Q-01",
                "result": "pass", "reader_answer": "失败后保留选择并重试", "gap": "无"}],
                "ambiguities": [], "hidden_assumptions": [], "contradictions": []},
            "render_check": {"target": "本地阅读视图", "checked_at": "2026-08-13T20:00:00+08:00",
                "checks": self.render_checks(), "issues": []},
            "facts": [{
                "id": "FACT-01", "statement": "提交前再次校验", "source_anchor": "FR-01",
                "document_anchor": "4.5.1", "needs_visual": True, "visual_ids": ["VIS-01"]
            }],
            "states": [{
                "id": "STATE-01", "surface": "提交页", "entry": "候选项已选",
                "visible": "已选期数和提交按钮", "actions": ["提交"],
                "result_or_exit": "提交成功进入结果页", "recovery": "失败保留选择并重试",
                "source_anchor": "FR-01", "visual_id": "VIS-01"
            }],
            "visuals": [{
                "id": "VIS-01", "question": "提交失败后如何恢复", "type": "flowchart",
                "coverage": "focused", "delivery_role": "inline",
                "review_question_id": "Q-01", "relation_kind": "sequence",
                "scope": "提交与恢复", "rationale": "顺序关系", "validation": "预览",
                "source_anchors": ["FR-01"], "path": str(visual), "placement": "4.2 产品动线"
            }]
        })
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack)],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_execution_pack_rejects_unknown_visual_and_missing_recovery(self) -> None:
        pack = self.write_json("bad-pack.json", {
            "mode": "visual", "source": "formal.md", "document": "traditional.md",
            "validation_level": "enhanced",
            "primary_artifact": self.primary_artifact(),
            "audience": ["产品"], "review_task": "评审", "mainline": "入口 → 结果",
            "facts": [{"id": "FACT-01", "statement": "事实", "source_anchor": "FR-01",
                       "document_anchor": "4.1", "needs_visual": True, "visual_ids": ["MISSING"]}],
            "states": [{"id": "STATE-01", "surface": "页面", "entry": "进入", "visible": "内容",
                        "actions": ["操作"], "result_or_exit": "结果", "source_anchor": "FR-01",
                        "visual_id": "MISSING"}],
            "visuals": []
        })
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack), "--skip-file-checks"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown visuals", result.stderr)
        self.assertIn("recovery is required", result.stderr)

    def test_execution_pack_rejects_invalid_interaction_model(self) -> None:
        source = self.work / "formal.md"
        document = self.work / "traditional.md"
        source.write_text("# 正式 PRD\n", encoding="utf-8")
        document.write_text("# 传统 PRD\n", encoding="utf-8")
        model = self.write_json("model.json", {
            "schema_version": "2.0",
            "coverage": {"entry_state_ids": ["S-1"], "required_state_types": ["entry"]},
            "surfaces": [{"id": "P-1", "name": "页面"}],
            "states": [{"id": "S-1", "name": "入口", "surface_id": "P-1", "type": "entry",
                        "entry": "进入", "visible": "内容", "actions": [{"id": "A-1", "label": "继续"}],
                        "source_anchor": "FR-01", "visual_ref": "V-1"}],
            "transitions": []
        })
        pack = self.write_json("pack-with-model.json", {
            "mode": "visual", "source": str(source), "document": str(document),
            "validation_level": "enhanced",
            "primary_artifact": self.primary_artifact(),
            "interaction_model": str(model), "audience": ["产品"], "review_task": "评审交互",
            "mainline": "入口 → 结果", "facts": [{"id": "FACT-01", "statement": "事实",
            "source_anchor": "FR-01", "document_anchor": "3.1", "needs_visual": False,
            "visual_ids": []}], "states": [], "visuals": []
        })
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("interaction_model: enabled action has no transition", result.stderr)

    def test_execution_pack_allows_demand_specific_visual_plan(self) -> None:
        source = self.work / "formal.md"
        document = self.work / "traditional.md"
        visual = self.work / "single.svg"
        source.write_text("# 正式 PRD\n", encoding="utf-8")
        document.write_text("# 传统 PRD\n", encoding="utf-8")
        visual.write_text("<svg/>", encoding="utf-8")
        pack = self.write_json("dynamic-pack.json", {
            "mode": "visual", "source": str(source), "document": str(document),
            "validation_level": "enhanced",
            "primary_artifact": self.primary_artifact(),
            "audience": ["产品"], "review_task": "评审单页信息层级",
            "mainline": "进入 → 查看", "facts": [{"id": "FACT-01", "statement": "单页展示",
            "source_anchor": "FR-01", "document_anchor": "3.1", "needs_visual": True,
            "visual_ids": ["VIS-01"]}], "states": [],
            "modules": [{"id": "MOD-01", "title": "查看信息", "fact_ids": ["FACT-01"],
            "visual_ids": ["VIS-01"]}],
            "review_questions": [{"id": "Q-01", "question": "信息如何分层",
            "source_anchors": ["FR-01"], "relation_kind": "spatial",
            "representation": "wireframe", "scope": "只包含单页信息",
            "rationale": "空间关系比流程更重要", "validation": "逐字段核对并预览",
            "visual_id": "VIS-01"}],
            "reader_test": {"reader_type": "author", "reader_context": "只读成稿", "questions": [{"question_id": "Q-01",
            "result": "pass", "reader_answer": "信息按任务层级展示", "gap": "无"}],
            "ambiguities": [], "hidden_assumptions": [], "contradictions": []},
            "render_check": {"target": "本地阅读视图", "checked_at": "2026-08-13T20:00:00+08:00",
            "checks": self.render_checks(), "issues": []},
            "visuals": [{"id": "VIS-01", "question": "信息如何分层", "type": "wireframe",
            "role": "local", "coverage": "focused", "delivery_role": "inline",
            "review_question_id": "Q-01", "relation_kind": "spatial",
            "scope": "单页", "rationale": "空间关系", "validation": "预览",
            "source_anchors": ["FR-01"], "path": str(visual), "placement": "3.1"}]
        })
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_execution_pack_rejects_unresolved_reader_or_render_failures(self) -> None:
        pack = self.write_json("failed-evidence.json", {
            "mode": "visual", "source": "formal.md", "document": "traditional.md",
            "validation_level": "enhanced",
            "primary_artifact": self.primary_artifact(),
            "audience": ["产品"], "review_task": "评审", "mainline": "进入 → 结果",
            "facts": [{"id": "FACT-01", "statement": "事实", "source_anchor": "FR-01",
                "document_anchor": "3.1", "needs_visual": False, "visual_ids": []}],
            "states": [], "modules": [], "visuals": [],
            "review_questions": [{"id": "Q-01", "question": "结果是什么",
                "source_anchors": ["FR-01"], "relation_kind": "sequence",
                "representation": "text", "scope": "结果", "rationale": "一句话足够",
                "validation": "读者复述"}],
            "reader_test": {"reader_type": "author", "reader_context": "只读成稿", "questions": [{"question_id": "Q-01",
                "result": "fail", "reader_answer": "无法判断", "gap": "缺少结果"}],
                "ambiguities": ["结果不明确"], "hidden_assumptions": [], "contradictions": []},
            "render_check": {"target": "本地", "checked_at": "2026-08-13T20:00:00+08:00",
                "checks": {"document_structure": "pass", "visual_legibility": "not_applicable",
                    "cross_references": "fail", "asset_integrity": "pass",
                    "information_hierarchy": "pass", "terminology_layering": "pass",
                    "inline_readability": "not_applicable", "zoom_readability": "not_applicable"},
                "issues": ["主源链接失效"]}
        })
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack), "--skip-file-checks"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("reader_test contains failed", result.stderr)
        self.assertIn("render_check contains failures", result.stderr)

    def test_strict_execution_pack_rejects_author_only_reader_evidence(self) -> None:
        data = {
            "mode": "visual", "validation_level": "strict",
            "source": "formal.md", "document": "traditional.md",
            "primary_artifact": self.primary_artifact(),
            "audience": ["产品"], "review_task": "评审", "mainline": "进入 → 结果",
            "facts": [{"id": "FACT-01", "statement": "事实", "source_anchor": "FR-01",
                "document_anchor": "4.1", "needs_visual": False, "visual_ids": []}],
            "states": [], "modules": [], "visuals": [],
            "review_questions": [{"id": "Q-01", "question": "结果是什么",
                "source_anchors": ["FR-01"], "relation_kind": "sequence",
                "representation": "text", "scope": "结果", "rationale": "一句话足够",
                "validation": "读者复述"}],
            "reader_test": {"reader_type": "author", "reader_context": "作者回读",
                "questions": [{"question_id": "Q-01", "result": "pass",
                    "reader_answer": "结果明确", "gap": "无"}],
                "ambiguities": [], "hidden_assumptions": [], "contradictions": []},
            "render_check": {"target": "本地", "checked_at": "2026-08-14T20:00:00+08:00",
                "checks": {**self.render_checks(), "inline_readability": "not_applicable"},
                "issues": []},
        }
        pack = self.write_json("strict-author.json", data)
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack), "--skip-file-checks"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("strict validation requires an independent", result.stderr)

    def test_interaction_visual_rejects_state_gallery_without_links(self) -> None:
        source = self.work / "formal.md"
        document = self.work / "traditional.md"
        visual = self.work / "board.svg"
        source.write_text("# 正式 PRD\n", encoding="utf-8")
        document.write_text("# 传统 PRD\n", encoding="utf-8")
        visual.write_text("<svg/>", encoding="utf-8")
        model = self.write_json("model.json", {
            "schema_version": "2.0", "surfaces": [{"id": "P-1", "name": "页面"}],
            "states": [
                {"id": "S-1", "name": "可用", "surface_id": "P-1", "type": "ready",
                 "entry": "进入", "visible": "按钮", "actions": [{"id": "A-1", "label": "提交"}],
                 "source_anchor": "FR-01", "visual_ref": "VIS-01#ready"},
                {"id": "S-2", "name": "成功", "surface_id": "P-1", "type": "completed",
                 "entry": "提交成功", "visible": "成功", "actions": [], "terminal": True,
                 "source_anchor": "FR-01", "visual_ref": "VIS-01#success"}],
            "transitions": [{"id": "T-1", "from": "S-1", "to": "S-2", "trigger": "提交",
                             "kind": "user", "action_id": "A-1", "source_anchor": "FR-01"}],
            "coverage": {"entry_state_ids": ["S-1"], "required_state_types": ["ready", "completed"]}
        })
        board = self.write_json("board.json", {
            "boards": [{"id": "ready", "title": "可用", "blocks": []},
                       {"id": "success", "title": "成功", "blocks": []}], "links": []
        })
        pack = self.write_json("gallery-pack.json", {
            "mode": "visual", "source": str(source), "document": str(document),
            "validation_level": "enhanced",
            "primary_artifact": self.primary_artifact(),
            "interaction_model": str(model), "audience": ["产品"], "review_task": "评审状态",
            "mainline": "可用 → 成功", "facts": [{"id": "FACT-01", "statement": "提交后成功",
                "source_anchor": "FR-01", "document_anchor": "3.1", "needs_visual": True,
                "visual_ids": ["VIS-01"]}], "states": [], "modules": [],
            "review_questions": [{"id": "Q-01", "question": "状态如何迁移",
                "source_anchors": ["FR-01"], "relation_kind": "state",
                "representation": "wireframe", "scope": "可用到成功", "rationale": "状态关系",
                "validation": "模型和画板一致", "visual_id": "VIS-01"}],
            "reader_test": {"reader_type": "author", "reader_context": "只读成稿", "questions": [{"question_id": "Q-01",
                "result": "pass", "reader_answer": "提交后成功", "gap": "无"}],
                "ambiguities": [], "hidden_assumptions": [], "contradictions": []},
            "render_check": {"target": "本地", "checked_at": "2026-08-13T20:00:00+08:00",
                "checks": {**self.render_checks(), "zoom_readability": "pass"}, "issues": []},
            "visuals": [{"id": "VIS-01", "question": "状态如何迁移", "type": "wireframe",
                "role": "deep_dive", "coverage": "complete", "delivery_role": "zoomable",
                "review_question_id": "Q-01", "relation_kind": "state",
                "scope": "两个状态", "rationale": "状态关系", "validation": "核对",
                "source_anchors": ["FR-01"], "path": str(visual), "spec_path": str(board),
                "placement": "3.1"}]
        })
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("interaction board has no transition links", result.stderr)
        self.assertIn("ready->success", result.stderr)

    def test_state_diagram_can_carry_interaction_without_wireframe_spec(self) -> None:
        source = self.work / "formal.md"
        document = self.work / "traditional.md"
        visual = self.work / "state.mmd"
        source.write_text("# 正式 PRD\n", encoding="utf-8")
        document.write_text("# 传统 PRD\n", encoding="utf-8")
        visual.write_text("stateDiagram-v2\n  Ready --> Done: 提交\n", encoding="utf-8")
        pack = self.write_json("state-diagram-pack.json", {
            "mode": "visual", "source": str(source), "document": str(document),
            "validation_level": "enhanced",
            "primary_artifact": self.primary_artifact(),
            "audience": ["产品"], "review_task": "评审状态迁移", "mainline": "可用 → 完成",
            "facts": [{"id": "FACT-01", "statement": "提交后完成", "source_anchor": "FR-01",
                "document_anchor": "3.1", "needs_visual": True, "visual_ids": ["VIS-01"]}],
            "states": [
                {"id": "S-01", "surface": "详情页", "entry": "进入可用态", "visible": "提交按钮",
                 "actions": ["提交"], "result_or_exit": "进入完成态", "recovery": "返回可用态",
                 "source_anchor": "FR-01"},
                {"id": "S-02", "surface": "详情页", "entry": "提交成功", "visible": "完成提示",
                 "actions": ["返回"], "result_or_exit": "结束", "recovery": "返回详情页",
                 "source_anchor": "FR-01"}
            ], "modules": [],
            "review_questions": [{"id": "Q-01", "question": "状态如何迁移",
                "source_anchors": ["FR-01"], "relation_kind": "state", "representation": "state",
                "scope": "可用到完成", "rationale": "生命周期关系", "validation": "核对迁移",
                "visual_id": "VIS-01"}],
            "reader_test": {"reader_type": "author", "reader_context": "只读成稿", "questions": [{"question_id": "Q-01",
                "result": "pass", "reader_answer": "提交后完成", "gap": "无"}],
                "ambiguities": [], "hidden_assumptions": [], "contradictions": []},
            "render_check": {"target": "本地", "checked_at": "2026-08-13T20:00:00+08:00",
                "checks": self.render_checks(), "issues": []},
            "visuals": [{"id": "VIS-01", "question": "状态如何迁移", "type": "state",
                "role": "deep_dive", "coverage": "complete", "delivery_role": "inline",
                "review_question_id": "Q-01", "relation_kind": "state",
                "scope": "两个状态", "rationale": "生命周期关系", "validation": "核对迁移",
                "source_anchors": ["FR-01"], "path": str(visual), "placement": "3.1"}]
        })
        result = subprocess.run(
            ["python3", str(PACK_CHECKER), "--pack", str(pack)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class OverviewBoardRenderTest(unittest.TestCase):
    """Unit tests for render_overview_board: shared screens, modal, SVG blocks."""

    def setUp(self) -> None:
        sys.path.insert(0, str(ROOT))
        import render_overview_board as rob
        self.rob = rob

    def tearDown(self) -> None:
        sys.path.remove(str(ROOT))

    @staticmethod
    def screens():
        return {
            "plan": {
                "id": "plan", "title": "方案可确认",
                "blocks": [
                    {"type": "section", "title": "调整后安排"},
                    {"type": "kv_group", "fields": [
                        {"label": "被调整课程", "value": "思维拓展营"},
                        {"label": "调整后安排", "value": "周六 15:45"},
                    ]},
                ],
            },
            "confirm": {
                "id": "confirm", "title": "二次确认",
                "blocks": [{"type": "list", "items": [{"title": "课程A"}]}],
                "modal": {"title": "确认调整吗？", "body": "提交后不可撤销",
                          "actions": [{"text": "确认", "style": "primary"}]},
            },
        }

    def minimal_spec(self, card):
        return {
            "title": "总览", "cards": [card],
            "connectors": [],
            "_screens": self.screens(),
        }

    def test_card_screen_keeps_modal_and_blocks_from_shared_source(self):
        card = {"id": "C1", "title": "二次确认", "kind": "modal", "screen_ref": "confirm"}
        screen = self.rob.card_screen(card, self.screens())
        self.assertEqual(screen["modal"]["title"], "确认调整吗？")
        self.assertEqual(screen["blocks"][0]["type"], "list")
        self.assertEqual(screen["nav"], "二次确认")  # card title wins over storyboard nav

    def test_card_screen_inline_fallback_ignores_screen_ref_miss(self):
        card = {"id": "C1", "title": "方案", "kind": "page", "screen_ref": "missing",
                "screen": {"task": "确认方案", "key_content": ["内容"], "actions": ["确认"]}}
        screen = self.rob.card_screen(card, self.screens())
        self.assertNotIn("modal", screen)
        self.assertTrue(any(b["type"] == "button" for b in screen["blocks"]))

    def test_svg_card_renders_modal_overlay(self):
        card = {"id": "C1", "title": "二次确认", "kind": "modal", "screen_ref": "confirm"}
        spec = self.minimal_spec(card)
        svg, _, _ = self.rob.render_svg(spec)
        self.assertIn("确认调整吗？", svg)
        self.assertIn("rgba(15,17,20,0.45)", svg)  # mask
        self.assertIn("提交后不可撤销", svg)

    def test_svg_card_renders_kv_group_and_section(self):
        card = {"id": "C1", "title": "方案可确认", "kind": "page", "screen_ref": "plan"}
        spec = self.minimal_spec(card)
        svg, _, _ = self.rob.render_svg(spec)
        self.assertIn("调整后安排", svg)
        self.assertIn("思维拓展营", svg)
        self.assertIn("被调整课程", svg)

    def test_svg_chip_card_is_slim_without_screen(self):
        card = {"id": "C1", "title": "校验中", "kind": "chip", "state_ids": ["S1"]}
        spec = self.minimal_spec(card)
        svg, _, _ = self.rob.render_svg(spec)
        self.assertIn("校验中", svg)
        self.assertIn("stroke-dasharray", svg)  # dashed pill
        self.assertNotIn("确认调整吗？", svg)

    def test_html_card_body_renders_modal_for_shared_screen(self):
        card = {"id": "C1", "title": "二次确认", "kind": "modal", "screen_ref": "confirm"}
        html = self.rob.card_body_html(card, self.screens())
        self.assertIn("确认调整吗？", html)
        self.assertIn("b-modal", html)


if __name__ == "__main__":
    unittest.main()

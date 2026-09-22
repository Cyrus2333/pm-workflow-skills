import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "skills" / "pm-collaboration-deliver" / "scripts"),
)

from check_page_interaction_overview import validate


class PageInteractionOverviewTests(unittest.TestCase):
    @staticmethod
    def screen(task="完成当前任务", actions=None):
        return {
            "task": task,
            "key_content": ["关键信息", "当前状态"],
            "actions": ["确认"] if actions is None else actions,
            "visible_feedback": "页面反馈",
        }

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        (self.base / "overview.svg").write_text("<svg/>", encoding="utf-8")
        (self.base / "overview.png").write_bytes(b"png")
        self.model = {
            "surfaces": [{"id": "P1"}, {"id": "P2"}],
            "states": [
                {"id": "S1", "surface_id": "P1", "visual_required": True, "terminal": False},
                {"id": "S2", "surface_id": "P2", "visual_required": True, "terminal": True},
            ],
            "transitions": [{"id": "T1", "from": "S1", "to": "S2", "kind": "user", "action_id": "A1"}],
            "coverage": {"entry_state_ids": ["S1"]},
        }
        self.overview = {
            "schema_version": "1.0", "kind": "page_interaction_overview", "question": "页面如何跳转",
            "coverage_mode": "review_complete", "delivery_role": "zoomable", "reading_direction": "left_to_right",
            "cards": [
                {"id": "C1", "title": "入口", "kind": "entry", "state_ids": ["S1"], "surface_ids": ["P1"], "screen": self.screen(), "visual_ref": "overview.svg#c1"},
                {"id": "C2", "title": "结果", "kind": "result", "state_ids": ["S2"], "surface_ids": ["P2"], "screen": self.screen("确认结果", []), "visual_ref": "overview.svg#c2"},
            ],
            "connectors": [{"id": "E1", "from_card": "C1", "to_card": "C2", "label": "确认", "kind": "primary", "transition_ids": ["T1"]}],
            "render": {"source_path": "overview.svg", "preview_path": "overview.png"},
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_overview_passes(self):
        errors, stats = validate(self.overview, self.model, self.base)
        self.assertEqual(errors, [])
        self.assertEqual(stats["action_transitions"], 1)

    def test_render_file_check_can_be_skipped(self):
        (self.base / "overview.svg").unlink()
        (self.base / "overview.png").unlink()
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("render.source_path does not exist" in item for item in errors))
        errors, _ = validate(self.overview, self.model, self.base, check_files=False)
        self.assertEqual(errors, [])

    def test_missing_action_transition_fails(self):
        self.overview["connectors"] = []
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("misses action transitions" in item for item in errors))

    def test_wrong_connector_endpoint_fails(self):
        self.overview["connectors"][0]["from_card"] = "C2"
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("wrong source card" in item for item in errors))

    def test_return_requires_return_style(self):
        self.model["transitions"][0]["kind"] = "return"
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("visually declare return" in item for item in errors))

    def test_aggregated_states_require_visible_variant_mapping(self):
        self.overview["cards"] = [{
            "id": "C-ALL", "title": "同页结果", "kind": "result",
            "state_ids": ["S1", "S2"], "surface_ids": ["P1", "P2"],
            "screen": self.screen(), "visual_ref": "overview.svg#all",
        }]
        self.overview["connectors"] = [{
            "id": "E1", "from_card": "C-ALL", "to_card": "C-ALL", "label": "确认",
            "kind": "primary", "transition_ids": ["T1"],
        }]
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("state_variants is required" in item for item in errors))

        self.overview["cards"][0]["state_variants"] = [
            {"state_id": "S1", "label": "进入", "difference": "显示可操作内容"},
            {"state_id": "S2", "label": "完成", "difference": "显示完成反馈"},
        ]
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertEqual(errors, [])

    def test_visually_equivalent_states_require_reason(self):
        self.overview["cards"] = [{
            "id": "C-ALL", "title": "同页状态", "kind": "page",
            "state_ids": ["S1", "S2"], "surface_ids": ["P1", "P2"],
            "screen": self.screen(), "visual_ref": "overview.svg#all", "visual_equivalent": True,
        }]
        self.overview["connectors"] = [{
            "id": "E1", "from_card": "C-ALL", "to_card": "C-ALL", "label": "确认",
            "kind": "primary", "transition_ids": ["T1"],
        }]
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("equivalence_reason is required" in item for item in errors))

    def test_visible_card_requires_recognizable_screen_content(self):
        self.overview["cards"][0].pop("screen")
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("recognizable page card" in item for item in errors))

    def test_focused_overview_only_requires_declared_subset(self):
        self.overview["coverage_mode"] = "focused"
        self.overview["focus_state_ids"] = ["S1", "S2"]
        self.overview["focus_transition_ids"] = ["T1"]
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertEqual(errors, [])

        self.overview["focus_transition_ids"] = ["T1", "MISSING"]
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("unknown transitions" in item for item in errors))

    def make_transient(self):
        """Insert a transient state between S1 and S2 with chip-friendly wiring."""
        self.model["states"].insert(1, {
            "id": "S1L", "surface_id": "P1", "visibility": "transient",
            "visual_required": False, "terminal": False,
        })
        self.model["transitions"] = [
            {"id": "T1", "from": "S1", "to": "S1L", "kind": "system"},
            {"id": "T2", "from": "S1L", "to": "S2", "kind": "system"},
        ]
        self.overview["cards"].insert(1, {
            "id": "C1L", "title": "校验中", "kind": "chip",
            "state_ids": ["S1L"], "surface_ids": ["P1"],
        })
        self.overview["connectors"] = [
            {"id": "E1", "from_card": "C1", "to_card": "C1L", "label": "提交", "kind": "primary", "transition_ids": ["T1"]},
            {"id": "E2", "from_card": "C1L", "to_card": "C2", "label": "校验通过", "kind": "primary", "transition_ids": ["T2"]},
        ]

    def test_transient_state_must_use_chip_card(self):
        self.make_transient()
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertEqual(errors, [])

        self.overview["cards"][1]["kind"] = "page"
        self.overview["cards"][1]["screen"] = self.screen()
        self.overview["cards"][1]["visual_ref"] = "overview.svg#c1l"
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("must be represented by a chip or system card" in item for item in errors))

    def test_transient_state_may_use_system_card(self):
        # A routing/decision waypoint is a system node, not a page; system
        # cards are exempt from screen content just like chip cards.
        self.make_transient()
        self.overview["cards"][1]["kind"] = "system"
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertEqual(errors, [])

    def test_chip_card_cannot_carry_page_state(self):
        self.make_transient()
        self.overview["cards"][1]["state_ids"] = ["S1L", "S1"]
        self.overview["cards"][0]["state_ids"] = ["S2"]
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("non-transient state S1" in item for item in errors))

    def test_screen_ref_requires_declared_source_and_known_screen(self):
        (self.base / "screens.json").write_text(json.dumps({
            "screens": [{"id": "plan", "blocks": []}],
        }), encoding="utf-8")
        self.overview["cards"][0]["screen_ref"] = "plan"

        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("screen_ref requires overview.screen_source" in item for item in errors))

        self.overview["screen_source"] = "screens.json"
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertEqual(errors, [])

        self.overview["cards"][0]["screen_ref"] = "missing"
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("unknown screen in screen_source" in item for item in errors))

        self.overview["screen_source"] = "not-there.json"
        errors, _ = validate(self.overview, self.model, self.base)
        self.assertTrue(any("screen_source does not exist" in item for item in errors))


if __name__ == "__main__":
    unittest.main()

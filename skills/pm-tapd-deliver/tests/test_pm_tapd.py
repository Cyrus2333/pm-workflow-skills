#!/usr/bin/env python3
"""Focused offline regression tests for Story classification and label checks."""

import argparse
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pm_tapd.py"
SPEC = importlib.util.spec_from_file_location("pm_tapd", SCRIPT)
pm_tapd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pm_tapd)


def story_schema_request(method, path, params, form):
    assert method == "GET"
    assert path == "/stories/get_fields_info"
    return {
        "data": {
            "category_id": {
                "label": "分类",
                "html_type": "select",
                "options": {"category-1": "AI学练项目", "-1": "未分类"},
            },
            "label": {
                "label": "标签",
                "html_type": "multi_select",
                "options": {"常规工作项": "常规工作项"},
            },
        }
    }


class StoryRequiredFieldTests(unittest.TestCase):
    def test_compact_item_keeps_category_id(self):
        item = pm_tapd.compact_item(
            {"id": "1", "workspace_id": "w", "category_id": "category-1", "label": "常规工作项"},
            "stories",
        )
        self.assertEqual(item["category_id"], "category-1")

    def test_dry_run_resolves_required_story_fields(self):
        args = argparse.Namespace(
            entity="stories",
            payload='{"workspace_id":"w","name":"测试需求","category_id":"AI学练项目","label":"常规工作项"}',
            payload_file="",
            dry_run=True,
        )
        result = pm_tapd.cmd_write(args, story_schema_request)
        self.assertEqual(result["form"]["category_id"], "category-1")
        self.assertEqual(result["form"]["label"], "常规工作项")

    def test_dry_run_rejects_missing_story_label(self):
        args = argparse.Namespace(
            entity="stories",
            payload='{"workspace_id":"w","name":"测试需求","category_id":"AI学练项目"}',
            payload_file="",
            dry_run=True,
        )
        with self.assertRaisesRegex(pm_tapd.AdapterError, "label.*required"):
            pm_tapd.cmd_write(args, story_schema_request)

    def test_dry_run_rejects_uncategorized_story(self):
        args = argparse.Namespace(
            entity="stories",
            payload='{"workspace_id":"w","name":"测试需求","category_id":"未分类","label":"常规工作项"}',
            payload_file="",
            dry_run=True,
        )
        with self.assertRaisesRegex(pm_tapd.AdapterError, "cannot be 未分类"):
            pm_tapd.cmd_write(args, story_schema_request)

    def test_readback_asserts_category_and_label(self):
        args = argparse.Namespace(
            entity="stories",
            workspace_id="w",
            id="1",
            expect='{"category_id":"category-1","label":"常规工作项"}',
            expect_file="",
        )

        def get_request(method, path, params, form):
            return {
                "data": {
                    "Story": {
                        "id": "1",
                        "workspace_id": "w",
                        "category_id": "category-1",
                        "label": "常规工作项",
                    }
                }
            }

        result = pm_tapd.cmd_readback(args, get_request)
        self.assertTrue(result["matched"])

    def test_readback_rejects_missing_required_assertion(self):
        args = argparse.Namespace(
            entity="stories",
            workspace_id="w",
            id="1",
            expect='{"label":"常规工作项"}',
            expect_file="",
        )
        with self.assertRaisesRegex(pm_tapd.AdapterError, "category_id and label"):
            pm_tapd.cmd_readback(args, lambda *_: {"data": {}})


if __name__ == "__main__":
    unittest.main()

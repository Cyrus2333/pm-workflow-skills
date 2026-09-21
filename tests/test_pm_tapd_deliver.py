from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "pm-tapd-deliver" / "scripts"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = load_module("tapd_contract", "tapd-contract.py")
preflight = load_module("tapd_preflight", "tapd-preflight.py")
deliverables = load_module("verify_local_deliverables", "verify-local-deliverables.py")


class TapdContractTests(unittest.TestCase):
    def test_resolves_writable_field_and_enum(self):
        fields = {
            "custom_field_1": {
                "label": "类别",
                "readonly": False,
                "options": {"release": "【上线】发布&验收"},
            }
        }
        key, field = contract.resolve_field(fields, "类别")
        self.assertEqual(key, "custom_field_1")
        self.assertEqual(contract.resolve_enum(field, "【上线】发布&验收"), "release")

    def test_rejects_ambiguous_or_readonly_field(self):
        with self.assertRaises(ValueError):
            contract.resolve_field({"a": {"label": "状态"}, "b": {"label": "状态"}}, "状态")
        with self.assertRaises(ValueError):
            contract.resolve_field({"a": {"label": "状态", "readonly": True}}, "状态")

    def test_duplicate_requires_complete_query_for_clear_result(self):
        items = [{"id": 1, "workspace_id": 42, "name": "  发布  验证 "}]
        self.assertEqual(contract.duplicates("发布 验证", items, 42, complete=True)["state"], "duplicate")
        self.assertEqual(contract.duplicates("其他", items, 42, complete=False)["state"], "incomplete")
        self.assertEqual(contract.duplicates("其他", items, 42, complete=True)["state"], "clear_complete")


class TapdPreflightTests(unittest.TestCase):
    def test_configured_server_is_not_reported_as_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "SKILL.md"
            skill.write_text("---\nname: pm-tapd-deliver\n---\n", encoding="utf-8")
            config = root / "config.toml"
            config.write_text('[mcp_servers.tapd]\ncommand = "placeholder"\n', encoding="utf-8")
            result = preflight.inspect(skill, [config], tools=[])
        self.assertFalse(result["ready"])
        self.assertEqual(result["state"], "CONFIGURED_NOT_EXPOSED")

    def test_discovered_tools_still_require_live_read_probe(self):
        skill = ROOT / "skills" / "pm-tapd-deliver" / "SKILL.md"
        result = preflight.inspect(skill, [], tools=["tapd_get_stories"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["state"], "READ_PROBE_REQUIRED")


class DeliverableValidationTests(unittest.TestCase):
    def test_accepts_explicit_nonempty_file_inside_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            artifact = root / "release.md"
            artifact.write_text("release", encoding="utf-8")
            result = deliverables.validate(artifact, root)
        self.assertTrue(result["ok"])

    def test_rejects_empty_or_outside_file(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            root = Path(first).resolve()
            empty = root / "empty.md"
            empty.touch()
            outside = Path(second).resolve() / "outside.md"
            outside.write_text("content", encoding="utf-8")
            self.assertFalse(deliverables.validate(empty, root)["ok"])
            self.assertFalse(deliverables.validate(outside, root)["ok"])


if __name__ == "__main__":
    unittest.main()

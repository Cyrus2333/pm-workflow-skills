from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "pm-tapd-deliver" / "scripts"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = load_module("tapd_contract", "tapd-contract.py")
adapter = load_module("pm_tapd", "pm_tapd.py")
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


class AdapterTests(unittest.TestCase):
    def test_capabilities_do_not_claim_attachment_or_mention(self):
        payload = json.loads(self._run(["capabilities"]))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "tapd-openapi")
        self.assertTrue(payload["capabilities"]["story"])
        self.assertFalse(payload["capabilities"]["attachment"])
        self.assertFalse(payload["capabilities"]["mention"])
        self.assertFalse(payload["capabilities"]["workflow"])

    def test_redact_strips_password_fields(self):
        cleaned = adapter.redact(
            {"api_user": "u", "api_password": "secret", "nested": {"access_token": "t"}}
        )
        self.assertEqual(cleaned["api_user"], "u")
        self.assertEqual(cleaned["api_password"], "***")
        self.assertEqual(cleaned["nested"]["access_token"], "***")

    def test_preflight_requires_live_probe_not_config(self):
        calls = []

        def request(method, path, params, form):
            calls.append(path)
            if path == "/quickstart/testauth":
                return {
                    "http_status": 200,
                    "data": {"api_user": "alice", "api_password": "should-not-leak"},
                }
            raise AssertionError(path)

        with patch.dict(os.environ, {"TAPD_API_USER": "alice", "TAPD_API_PASSWORD": "secret"}, clear=False):
            output = self._run(["preflight"], request=request)
        payload = json.loads(output)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["state"], "READY")
        self.assertEqual(payload["auth"]["method"], "basic")
        self.assertEqual(payload["user"]["api_user"], "alice")
        self.assertEqual(calls, ["/quickstart/testauth"])
        self.assertNotIn("should-not-leak", output)
        self.assertNotIn("secret", output)

    def test_preflight_missing_credentials_does_not_call_tapd(self):
        calls = []

        def request(method, path, params, form):
            calls.append(path)
            raise AssertionError("should not call TAPD")

        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(
                os.environ,
                {"TAPD_ACCESS_TOKEN": "", "TAPD_API_USER": "", "TAPD_API_PASSWORD": ""},
                clear=False,
            ):
                with patch.object(adapter.Path, "home", return_value=Path(temporary)):
                    output = self._run(["preflight"], request=request, allowed_codes=(3,))
        payload = json.loads(output)
        self.assertFalse(payload["ok"])
        self.assertFalse(calls)

    def test_find_marks_incomplete_when_pages_are_short(self):
        def request(method, path, params, form):
            if path.endswith("/count"):
                return {"http_status": 200, "data": {"count": 2}}
            if path == "/stories":
                return {"http_status": 200, "data": [{"Story": {"id": "1", "workspace_id": "42", "name": "发布验证"}}]}
            raise AssertionError(path)

        payload = json.loads(self._run(
            ["find", "--entity", "stories", "--workspace-id", "42", "--name", "其他"],
            request=request,
        ))
        self.assertEqual(payload["duplicates"]["state"], "incomplete")
        self.assertFalse(payload["query"]["complete"])

    def test_write_dry_run_does_not_post(self):
        def request(method, path, params, form):
            raise AssertionError("dry-run must not call TAPD")

        payload = json.loads(self._run(
            [
                "write",
                "--entity",
                "stories",
                "--dry-run",
                "--payload",
                json.dumps(
                    {
                        "workspace_id": "42",
                        "name": "发布验证",
                        "description": "背景",
                        "custom_fields": {"custom_field_1": "release"},
                    }
                ),
            ],
            request=request,
        ))
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["action"], "create")
        self.assertEqual(payload["form"]["name"], "发布验证")
        self.assertEqual(payload["form"]["custom_field_1"], "release")

    def test_write_posts_when_not_dry_run(self):
        calls = []

        def request(method, path, params, form):
            calls.append((method, path, form))
            return {
                "http_status": 200,
                "data": [{"Story": {"id": "9", "workspace_id": "42", "name": "发布验证"}}],
            }

        payload = json.loads(self._run(
            [
                "write",
                "--entity",
                "stories",
                "--payload",
                json.dumps({"workspace_id": "42", "name": "发布验证"}),
            ],
            request=request,
        ))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["item"]["id"], "9")
        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[0][1], "/stories")

    def test_readback_detects_field_mismatch(self):
        def request(method, path, params, form):
            self.assertEqual(path, "/stories")
            return {
                "http_status": 200,
                "data": [{"Story": {"id": "9", "workspace_id": "42", "name": "别的标题", "status": "planning"}}],
            }

        payload = json.loads(self._run(
            [
                "readback",
                "--entity",
                "stories",
                "--workspace-id",
                "42",
                "--id",
                "9",
                "--expect",
                json.dumps({"name": "发布验证", "workspace_id": "42"}),
            ],
            request=request,
        ))
        self.assertFalse(payload["ok"])
        self.assertIn("name", payload["mismatches"])

    def _run(self, argv, request=None, allowed_codes=(0, 1)):
        buf = StringIO()
        with contextlib.redirect_stdout(buf):
            code = adapter.main(argv, request=request)
        self.assertIn(code, allowed_codes)
        return buf.getvalue()


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

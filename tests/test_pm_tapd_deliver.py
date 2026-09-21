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

    def test_resolves_json_encoded_enum_options(self):
        fields = {
            "custom_field_four": {
                "label": "任务类别",
                "readonly": False,
                "options": '{"25":"【产品】方案策划","7":"【研发】编码"}',
            }
        }
        key, field = contract.resolve_field(fields, "任务类别")
        self.assertEqual(key, "custom_field_four")
        self.assertEqual(contract.resolve_enum(field, "【研发】编码"), "7")
        self.assertEqual(contract.resolve_enum(field, "25"), "25")

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
    def test_capabilities_include_workflow_attachment_and_mention(self):
        payload = json.loads(self._run(["capabilities"]))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["backend"], "tapd-openapi")
        self.assertEqual(payload["version"], 2)
        self.assertTrue(payload["capabilities"]["story"])
        self.assertTrue(payload["capabilities"]["workflow"])
        self.assertTrue(payload["capabilities"]["mention"])
        self.assertTrue(payload["capabilities"]["attachment"])
        self.assertTrue(payload["capabilities"]["attachment_list"])
        self.assertTrue(payload["capabilities"]["attachment_upload"])
        self.assertEqual(payload["contracts"]["attachment_upload"], "community")
        self.assertEqual(payload["unavailable"], [])

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

    def test_task_category_dry_run_uses_display_label_and_preserves_status(self):
        calls = []

        def request(method, path, params, form):
            calls.append((method, path, params, form))
            if path == "/tasks/custom_fields_settings":
                return {
                    "http_status": 200,
                    "data": [{"CustomFieldConfig": {
                        "custom_field": "custom_field_four",
                        "label": "任务类别",
                        "options": '{"25":"【产品】方案策划","7":"【研发】编码"}',
                    }}],
                }
            if path == "/tasks":
                return {
                    "http_status": 200,
                    "data": [{"Task": {
                        "id": "7", "workspace_id": "42", "name": "编码",
                        "status": "open", "custom_field_four": "7",
                    }}],
                }
            raise AssertionError(path)

        payload = json.loads(self._run(
            [
                "write", "--entity", "tasks", "--dry-run",
                "--payload", json.dumps({
                    "workspace_id": "42", "id": "7", "name": "编码",
                    "custom_fields": {"custom_field_four": "7"},
                }),
            ],
            request=request,
        ))
        self.assertEqual(payload["form"]["custom_field_four"], "【研发】编码")
        self.assertEqual(payload["form"]["status"], "open")
        self.assertEqual([call[1] for call in calls], ["/tasks/custom_fields_settings", "/tasks"])

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


    def test_mention_html_escapes_and_rejects_injection(self):
        html = adapter.build_comment_description('<b class="at-who">x</b>', ['alice" onclick=x'])
        self.assertIn('data-userid="alice&quot; onclick=x"', html)
        self.assertIn("&lt;b class=", html)
        self.assertEqual(adapter.extract_mention_nodes(html)[0]["nick"], 'alice" onclick=x')
        verified = adapter.mention_verification(["alice"], "@alice 请看")
        self.assertEqual(verified["status"], "MENTION_UNVERIFIED")

    def test_members_reject_duplicate_display_name(self):
        def request(method, path, params, form, files=None):
            self.assertEqual(path, "/workspaces/users")
            return {
                "http_status": 200,
                "data": [
                    {"UserWorkspace": {"user": "a1", "name": "Alice", "status": "1"}},
                    {"UserWorkspace": {"user": "a2", "name": "Alice", "status": "1"}},
                ],
            }

        payload = json.loads(self._run(
            ["members", "--workspace-id", "42", "--nicks", "Alice"],
            request=request,
            allowed_codes=(1,),
        ))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "MEMBER_AMBIGUOUS")

    def test_workflow_story_rejects_illegal_transition(self):
        def request(method, path, params, form, files=None):
            if path == "/workflows/status_map":
                return {"http_status": 200, "data": {"planning": "规划中", "status_2": "实现中"}}
            if path == "/workflows/all_transitions":
                return {
                    "http_status": 200,
                    "data": [{"WorkflowTransition": {"from": "planning", "to": "status_2"}}],
                }
            raise AssertionError(path)

        payload = json.loads(self._run(
            [
                "workflow",
                "--entity",
                "stories",
                "--workspace-id",
                "42",
                "--workitem-type-id",
                "9",
                "--from",
                "实现中",
                "--to",
                "规划中",
            ],
            request=request,
        ))
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["legal"])
        self.assertTrue(payload["workflow_proven"])
        self.assertEqual(payload["source"], "official_workflow")
        self.assertEqual(payload["from_key"], "status_2")
        self.assertEqual(payload["to_key"], "planning")

    def test_workflow_task_falls_back_when_official_api_rejects(self):
        def request(method, path, params, form, files=None):
            raise adapter.AdapterError("system invalid", 1, extra={"info": "system invalid"})

        payload = json.loads(self._run(
            [
                "workflow",
                "--entity",
                "tasks",
                "--workspace-id",
                "42",
                "--from",
                "open",
                "--to",
                "progressing",
            ],
            request=request,
        ))
        self.assertTrue(payload["legal"])
        self.assertFalse(payload["workflow_proven"])
        self.assertEqual(payload["source"], "documented_task_status")

    def test_comment_preview_and_dry_run_do_not_post(self):
        calls = []

        def request(method, path, params, form, files=None):
            calls.append((method, path, form, files))
            if path == "/workspaces/users":
                return {
                    "http_status": 200,
                    "data": [{"UserWorkspace": {"user": "alice", "name": "Alice", "status": "1"}}],
                }
            raise AssertionError(path)

        payload = json.loads(self._run(
            [
                "comment",
                "add",
                "--dry-run",
                "--entity",
                "tasks",
                "--workspace-id",
                "42",
                "--id",
                "7",
                "--author",
                "pm",
                "--text",
                "请看",
                "--mentions",
                "alice",
            ],
            request=request,
        ))
        self.assertTrue(payload["dry_run"])
        self.assertIn('data-userid="alice"', payload["description"])
        self.assertEqual(calls, [("GET", "/workspaces/users", None, None)])

    def test_comment_add_requires_native_node_readback(self):
        def request(method, path, params, form, files=None):
            if path == "/workspaces/users":
                return {
                    "http_status": 200,
                    "data": [{"UserWorkspace": {"user": "alice", "name": "Alice", "status": "1"}}],
                }
            if method == "POST" and path == "/comments":
                return {"http_status": 200, "data": {"Comment": {"id": "c1"}}}
            if path == "/comments":
                return {
                    "http_status": 200,
                    "data": [{"Comment": {
                        "id": "c1",
                        "workspace_id": "42",
                        "entry_type": "tasks",
                        "entry_id": "7",
                        "author": "pm",
                        "description": "@alice 请看",
                    }}],
                }
            raise AssertionError(path)

        payload = json.loads(self._run(
            [
                "comment",
                "add",
                "--entity",
                "tasks",
                "--workspace-id",
                "42",
                "--id",
                "7",
                "--author",
                "pm",
                "--text",
                "请看",
                "--mentions",
                "alice",
            ],
            request=request,
            allowed_codes=(1,),
        ))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["verification"]["status"], "MENTION_UNVERIFIED")

    def test_attachment_upload_dry_run_validates_local_file_and_does_not_post(self):
        calls = []

        def request(method, path, params, form, files=None):
            calls.append((method, path, files))
            if path == "/attachments":
                return {"http_status": 200, "data": []}
            raise AssertionError(path)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            artifact = root / "release.md"
            artifact.write_text("release", encoding="utf-8")
            payload = json.loads(self._run(
                [
                    "attachments",
                    "upload",
                    "--dry-run",
                    "--entity",
                    "tasks",
                    "--workspace-id",
                    "42",
                    "--id",
                    "7",
                    "--file",
                    str(artifact),
                    "--root",
                    str(root),
                ],
                request=request,
            ))
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["filename"], "release.md")
        self.assertEqual(payload["would_post"], "/files/upload_attachment")
        self.assertEqual(payload["type"], "task")
        self.assertEqual(calls, [("GET", "/attachments", None)])

    def test_attachment_same_name_stops_without_upload(self):
        def request(method, path, params, form, files=None):
            if path == "/attachments":
                return {
                    "http_status": 200,
                    "data": [{"Attachment": {
                        "id": "a1",
                        "workspace_id": "42",
                        "type": "task",
                        "entry_id": "7",
                        "filename": "release.md",
                    }}],
                }
            raise AssertionError("must not upload")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            artifact = root / "release.md"
            artifact.write_text("release", encoding="utf-8")
            payload = json.loads(self._run(
                [
                    "attachments",
                    "upload",
                    "--entity",
                    "tasks",
                    "--workspace-id",
                    "42",
                    "--id",
                    "7",
                    "--file",
                    str(artifact),
                    "--root",
                    str(root),
                ],
                request=request,
                allowed_codes=(1,),
            ))
        self.assertEqual(payload["code"], "ATTACHMENT_DUPLICATE")


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

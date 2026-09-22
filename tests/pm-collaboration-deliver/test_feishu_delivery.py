#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "pm-collaboration-deliver" / "scripts"
CHECKER = SCRIPTS / "audit" / "check_feishu_delivery.py"
BUILDER = SCRIPTS / "audit" / "build_feishu_audit.py"


class FeishuDeliveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        (self.work / "fetched.xml").write_text(
            '<title>测试 PRD</title><h1>一、背景与目标</h1><p>本期范围</p>'
            '<whiteboard token="wbcn-test"/>', encoding="utf-8"
        )
        (self.work / "preview.jpg").write_bytes(b"jpeg-preview")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def audit(self) -> dict:
        return {
            "schema_version": "1.1", "platform": "feishu_docx",
            "document": {"url": "https://example.feishu.cn/docx/test", "document_id": "test",
                "revision_id": 3, "fetched_xml": "fetched.xml", "checked_at": "2026-08-13T20:00:00+08:00",
                "required_headings": ["一、背景与目标"], "required_phrases": ["本期范围"]},
            "publish": {"strategy": "block_update", "identity": "user", "overwrite_used": False,
                "protected_resources_checked": True},
            "visuals": [{"id": "VIS-01", "question": "主线是什么", "resource_type": "whiteboard",
                "block_token": "wbcn-test", "source_type": "mermaid", "preview_path": "preview.jpg",
                "delivery_role": "inline",
                "checked_at": "2026-08-13T20:00:00+08:00", "checks": {
                    "content_complete": "pass", "text_legible": "pass", "line_clarity": "pass",
                    "canvas_fit": "pass", "document_scale": "pass",
                    "inline_readability": "pass", "zoom_readability": "not_applicable"}, "issues": []}],
            "document_view": {"target": "Feishu desktop", "checked_at": "2026-08-13T20:00:00+08:00",
                "checks": {"title_and_outline": "pass", "scanability": "pass", "table_layout": "not_applicable",
                    "visual_placement": "pass", "visual_scale": "pass", "links_and_resources": "pass",
                    "traditional_structure": "pass", "terminology_layering": "pass",
                    "local_visual_proximity": "pass"},
                "issues": []},
            "reader_test": {"reader_context": "只读飞书成稿", "result": "pass",
                "questions_answered": ["Q-01"], "issues": []},
        }

    def run_audit(self, data: dict) -> subprocess.CompletedProcess[str]:
        path = self.work / "audit.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(["python3", str(CHECKER), "--audit", str(path)], capture_output=True, text=True)

    def test_complete_audit_passes(self) -> None:
        result = self.run_audit(self.audit())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_token_or_failed_scale_is_rejected(self) -> None:
        data = self.audit()
        data["visuals"][0]["block_token"] = "missing-token"
        data["visuals"][0]["checks"]["document_scale"] = "fail"
        result = self.run_audit(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("absent from fetched XML", result.stderr)
        self.assertIn("document_scale", result.stderr)

    def test_overwrite_requires_resource_inventory(self) -> None:
        data = self.audit()
        data["publish"]["strategy"] = "overwrite"
        data["publish"]["overwrite_used"] = True
        data["publish"]["protected_resources_checked"] = False
        result = self.run_audit(data)
        self.assertEqual(result.returncode, 2)
        self.assertIn("protected_resources_checked", result.stderr)

    def test_builder_extracts_unique_whiteboards_and_starts_failed(self) -> None:
        fetch = self.work / "fetch.json"
        fetch.write_text(json.dumps({"ok": True, "identity": "user", "data": {"document": {
            "document_id": "doc-test", "revision_id": 7,
            "content": '<title>测试</title><whiteboard token="wb-one"/><whiteboard token="wb-one"/>'
        }}}), encoding="utf-8")
        preview_dir = self.work / "previews"
        preview_dir.mkdir()
        (preview_dir / "wb-one.jpg").write_bytes(b"preview")
        out = self.work / "draft-audit.json"
        result = subprocess.run([
            "python3", str(BUILDER), "--fetch-json", str(fetch),
            "--document-url", "https://example.feishu.cn/docx/doc-test",
            "--preview-dir", str(preview_dir), "--out", str(out),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        draft = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(draft["visuals"]), 1)
        self.assertEqual(draft["visuals"][0]["block_token"], "wb-one")
        checked = subprocess.run(["python3", str(CHECKER), "--audit", str(out)],
                                 capture_output=True, text=True)
        self.assertEqual(checked.returncode, 2)
        self.assertIn("contains failures", checked.stderr)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "skills" / "pm-collaboration-deliver" / "scripts" / "check_reading_view.py"
)
spec = importlib.util.spec_from_file_location("check_reading_view", SCRIPT)
checker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(checker)


class ReadingViewChecks(unittest.TestCase):
    def test_traditional_profile_requires_reader_spine(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "协作稿.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 协作 PRD\n\n## 为什么做\n\n背景。\n\n## 一条主线\n\n方案。\n\n[正式 PRD](正式PRD.md)\n",
                encoding="utf-8",
            )
            errors, warnings = checker.inspect(document, source, "traditional-prd")
            self.assertTrue(any("background_problem" in item for item in errors))
            self.assertTrue(any("goal" in item for item in errors))
            self.assertTrue(any("scope" in item for item in errors))
            self.assertTrue(any("detail" in item for item in errors))
            self.assertTrue(any("acceptance" in item for item in errors))
            self.assertTrue(any("collaboration brief" in item for item in warnings))

    def test_traditional_profile_accepts_business_named_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 用户自主换期\n\n## 1. 需求背景\n\n### 1.1 当前问题\n\n问题。\n\n"
                "## 2. 需求目标\n\n目标。\n\n## 3. 需求范围\n\n范围。\n\n"
                "## 4. 产品方案\n\n方案。\n\n## 5. 需求详情\n\n详情。\n\n"
                "## 6. 验收标准\n\n验收。\n\n[正式 PRD](正式PRD.md)\n",
                encoding="utf-8",
            )
            errors, warnings = checker.inspect(document, source, "traditional-prd")
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_warns_about_deprecated_generic_section_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 需求背景与诉求\n\n内容。\n\n"
                "## 方案概述\n\n内容。\n\n## 方案详情\n\n内容。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            _, warnings = checker.inspect(document, source)
            self.assertEqual(sum("deprecated generic heading" in item for item in warnings), 3)

    def test_rejects_internal_collaboration_heading_with_chinese_number(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 六、系统协作与下钻\n\n内容。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            errors, _ = checker.inspect(document, source)
            self.assertTrue(any("forbidden reading-view heading" in item for item in errors))

    def test_warns_when_implementation_terms_leak_into_user_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 5. 需求详情\n\nCRM 幂等和结果映射由页面保证。\n\n"
                "## 关联资料\n\n接口契约进入研发 spec。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            _, warnings = checker.inspect(document, source)
            self.assertTrue(any("幂等" in item for item in warnings))
            self.assertTrue(any("结果映射" in item for item in warnings))
            self.assertFalse(any("接口契约" in item for item in warnings))

    def test_clean_document_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            image = root / "page.png"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            image.write_bytes(b"png")
            document.write_text("# 阅读版\n\n## 1. 背景\n\n![现状页面](page.png)\n\n[正式 PRD](正式PRD.md)\n", encoding="utf-8")
            errors, warnings = checker.inspect(document, source)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_rejects_internal_terms_forbidden_heading_and_broken_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 阅读版\n\n## 1. 开发前必须确认\n\nVisualSpec\n\n![缺图](missing.png)\n",
                encoding="utf-8",
            )
            errors, _ = checker.inspect(document, source)
            self.assertTrue(any("forbidden" in item for item in errors))
            self.assertTrue(any("internal generation" in item for item in errors))
            self.assertTrue(any("broken local image" in item for item in errors))

    def test_rejects_duplicate_h2_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text("# 阅读版\n\n## 2. 页面\n\n## 2. 规则\n\n正式PRD.md\n", encoding="utf-8")
            errors, _ = checker.inspect(document, source)
            self.assertTrue(any("duplicate level-2" in item for item in errors))

    def test_warns_when_image_state_is_not_identified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            image = root / "page.png"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            image.write_bytes(b"png")
            document.write_text(
                "# 阅读版\n\n![评价页面](page.png)\n\n[正式 PRD](正式PRD.md)\n",
                encoding="utf-8",
            )
            errors, warnings = checker.inspect(document, source)
            self.assertEqual(errors, [])
            self.assertTrue(any("does not identify" in item for item in warnings))

    def test_rejects_author_worklog_heading(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 图文路由记录\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            errors, _ = checker.inspect(document, source)
            self.assertTrue(any("forbidden" in item for item in errors))

    def test_rejects_internal_reading_level(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n内部选择：R2 标准产品文档。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            errors, _ = checker.inspect(document, source)
            self.assertTrue(any("internal generation" in item for item in errors))

    def test_rejects_generation_narration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n按当前正式 PRD 转译为人类可读版本。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            errors, _ = checker.inspect(document, source)
            self.assertTrue(any("generation narration" in item for item in errors))

    def test_rejects_unresolved_traditional_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# {{需求名称}}｜产品文档\n\n<!-- R3 必须、R2 按需 -->\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            errors, _ = checker.inspect(document, source)
            self.assertTrue(any("template placeholder" in item for item in errors))
            self.assertTrue(any("template instruction" in item for item in errors))

    def test_allows_confirmed_business_content_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 分享优化\n\n卡片标题：听我唱：{{歌曲名称}}。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            errors, _ = checker.inspect(document, source)
            self.assertFalse(any("template placeholder" in item for item in errors))

    def test_warns_about_dense_trace_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            ids = " ".join(f"FR-{i:02d}" for i in range(1, 14))
            document.write_text(
                f"# 产品文档\n\n正式PRD.md\n\n{ids}\n",
                encoding="utf-8",
            )
            errors, warnings = checker.inspect(document, source)
            self.assertEqual(errors, [])
            self.assertTrue(any("trace-ID" in item for item in warnings))

    def test_warns_when_goal_is_written_as_feature_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 二、需求目标\n\n目标：新增结果查询页面。\n\n[正式 PRD](正式PRD.md)\n",
                encoding="utf-8",
            )
            errors, warnings = checker.inspect(document, source)
            self.assertEqual(errors, [])
            self.assertTrue(any("feature output" in item for item in warnings))

    def test_warns_when_goal_is_written_as_delivery_process(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 二、需求目标\n\n目标：按时上线唱歌大赛二期。\n\n[正式 PRD](正式PRD.md)\n",
                encoding="utf-8",
            )
            errors, warnings = checker.inspect(document, source)
            self.assertEqual(errors, [])
            self.assertTrue(any("delivery process" in item for item in warnings))

    def test_warns_about_long_prose_and_wide_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            long_paragraph = "这是一个需要拆分的产品判断。" * 15
            document.write_text(
                "# 产品文档\n\n"
                + long_paragraph
                + "\n\n| 一 | 二 | 三 | 四 | 五 | 六 |\n"
                + "|---|---|---|---|---|---|\n"
                + "| 1 | 2 | 3 | 4 | 5 | 6 |\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            errors, warnings = checker.inspect(document, source)
            self.assertEqual(errors, [])
            self.assertTrue(any("long prose paragraph" in item for item in warnings))
            self.assertTrue(any("wide table" in item for item in warnings))

    def test_does_not_use_fixed_mermaid_node_threshold(self) -> None:
        nodes = "\n".join(f"N{i}[节点{i}] --> N{i + 1}[节点{i + 1}]" for i in range(1, 11))
        warnings = checker.readability_warnings(f"# 流程\n\n```mermaid\nflowchart LR\n{nodes}\n```\n")
        self.assertFalse(any("Mermaid diagram" in item for item in warnings))

    def test_ordered_steps_do_not_merge_into_one_paragraph(self) -> None:
        steps = "\n".join(f"{index}. 这是第 {index} 个简短步骤。" for index in range(1, 8))
        warnings = checker.readability_warnings(f"# 操作\n\n{steps}\n")
        self.assertFalse(any("long prose paragraph" in item for item in warnings))

    def test_warns_about_long_ordered_step(self) -> None:
        warnings = checker.readability_warnings("# 操作\n\n1. " + "一个复杂判断。" * 25 + "\n")
        self.assertTrue(any("long ordered-list item" in item for item in warnings))

    def test_strict_mode_fails_on_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text("# 产品文档\n\n没有链接主源。\n", encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--fail-on-warnings",
                    "--document",
                    str(document),
                    "--source",
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("warning:", result.stdout)

    def test_warns_about_repeated_conclusion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "阅读版.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            sentence = "用户确认方案后仅可提交一次成功后不可再次发起换期操作"
            document.write_text(f"# 阅读版\n\n{sentence}\n\n{sentence}\n\n正式PRD.md\n", encoding="utf-8")
            _, warnings = checker.inspect(document, source)
            self.assertTrue(any("repeated conclusion" in item for item in warnings))

    def test_warns_when_routes_and_parameters_leak_into_product_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 3. 需求详情\n\n"
                "Node 先访问 /financial/clock-in-topic-edit，retry=Y 时执行 302 重定向。\n\n"
                "## 关联资料\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            _, warnings = checker.inspect(document, source)
            self.assertTrue(any("route, parameter" in item for item in warnings))

    def test_warns_about_table_heavy_visual_free_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            tables = "\n".join("| 字段 | 规则 |\n|---|---|\n| A | B |\n" for _ in range(8))
            document.write_text(f"# 产品文档\n\n{tables}\n正式PRD.md\n", encoding="utf-8")
            _, warnings = checker.inspect(document, source)
            self.assertTrue(any("tables and no inline visual" in item for item in warnings))

    def test_review_focus_entries_need_source_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 评审关注\n\n"
                "- 方案失效后需要人工兜底（来源：正式 PRD 3.2 节 / RULE-03）\n"
                "- 弹窗文案待确认\n\n"
                "## 1. 需求背景\n\n背景。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            _, warnings = checker.inspect(document, source)
            self.assertTrue(any("review-focus entries lack a source anchor" in item for item in warnings))
            self.assertTrue(any("评审关注" in item for item in warnings))

    def test_review_focus_with_anchors_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            document.write_text(
                "# 产品文档\n\n## 评审关注\n\n"
                "- 方案失效后需要人工兜底（来源：第 3 章 / RULE-03）\n"
                "- 仅可自主调整一次的限制（来源：正式 PRD 4.1 节 / AC-02）\n\n"
                "## 1. 需求背景\n\n背景。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            _, warnings = checker.inspect(document, source)
            self.assertFalse(any("review-focus" in item for item in warnings))

    def test_review_focus_over_broad_extraction_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "正式PRD.md"
            document = root / "传统PRD.md"
            source.write_text("# 正式 PRD\n", encoding="utf-8")
            items = "\n".join(f"- 事项{i}（来源：FR-{i:02d}）" for i in range(1, 9))
            document.write_text(
                f"# 产品文档\n\n## 评审关注\n\n{items}\n\n## 1. 需求背景\n\n背景。\n\n正式PRD.md\n",
                encoding="utf-8",
            )
            _, warnings = checker.inspect(document, source)
            self.assertTrue(any("review-focus block has 8 entries" in item for item in warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)

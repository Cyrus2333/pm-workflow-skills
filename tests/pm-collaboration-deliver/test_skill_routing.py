#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "pm-collaboration-deliver"


class SkillRoutingTest(unittest.TestCase):
    def test_main_entry_exposes_adaptive_routes(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for term in ("阅读版", "视觉版", "交互版", "基础", "增强", "严格"):
            self.assertIn(term, text)
        self.assertIn("只有用户要求创建、更新或验收飞书文档时", text)
        self.assertIn("默认只交付一份传统 PRD 主文档", text)
        self.assertIn("交互版先建立完整状态模型，再抽取正文所需子图", text)

    def test_primary_artifact_and_information_layers_are_explicit(self) -> None:
        text = (SKILL_DIR / "references" / "转译与文档结构.md").read_text(encoding="utf-8")
        self.assertIn("唯一主交付面", text)
        self.assertIn("产品主阅读层", text)
        self.assertIn("协作依赖层", text)
        self.assertIn("研发下钻层", text)
        traditional = (SKILL_DIR / "references" / "转译与文档结构.md").read_text(encoding="utf-8")
        self.assertIn("需求背景（现状与问题）", traditional)
        self.assertIn("需求目标", traditional)
        self.assertIn("需求范围", traditional)
        self.assertIn("验收标准", traditional)

    def test_default_template_uses_traditional_prd_language(self) -> None:
        text = (SKILL_DIR / "assets" / "traditional-product-document-template.md").read_text(encoding="utf-8")
        for heading in ("需求背景", "需求目标", "需求范围", "整体方案", "需求详情", "验收标准"):
            self.assertIn(heading, text)
        for deprecated in ("需求背景与诉求", "方案概述", "方案详情", "系统协作与下钻"):
            self.assertNotIn(deprecated, text)

    def test_feishu_daily_path_does_not_require_audit(self) -> None:
        text = (SKILL_DIR / "references" / "飞书发布与渲染.md").read_text(encoding="utf-8")
        self.assertIn("日常发布无需创建执行包、飞书审计文件或独立读者记录", text)
        self.assertIn("默认选择满足风险的最轻路径", text)
        self.assertIn("严格发布", text)

    def test_execution_pack_is_not_a_default_prerequisite(self) -> None:
        text = (SKILL_DIR / "references" / "质量与门槛.md").read_text(encoding="utf-8")
        self.assertIn("不是生成协作 PRD 的前置表单", text)
        self.assertIn("不必创建执行包", text)

    def test_prototype_route_separates_semantics_evidence_and_visual_context(self) -> None:
        text = (SKILL_DIR / "references" / "视觉与原型.md").read_text(encoding="utf-8")
        self.assertIn("产品语义充分度", text)
        self.assertIn("视觉上下文充分度", text)
        self.assertIn("区分观察与推断", text)
        self.assertIn("关键帧数量由状态变化决定", text)
        self.assertIn("飞书只负责发布与阅读", text)

    def test_human_handoff_requires_change_centered_visuals(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("面向人的承接层", skill)
        self.assertIn("当前界面或来源证据 → 调整后原型/关键状态 → 就近交互规则", skill)
        self.assertIn("只有标题和状态文案的圆角框仍是状态网络", skill)
        traditional = (SKILL_DIR / "references" / "转译与文档结构.md").read_text(encoding="utf-8")
        self.assertIn("执行四次转译，而不是删减章节", traditional)
        self.assertIn("轻量需求默认压缩成四个连续模块", traditional)

    def test_upstream_handoff_contract_is_explicit(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for term in ("工作边界", "输入契约", "交接契约", "选集不全集", "身份保持", "重述不照抄"):
            self.assertIn(term, skill)
        traditional = (SKILL_DIR / "references" / "转译与文档结构.md").read_text(encoding="utf-8")
        for term in ("上游产物映射", "页面状态与操作矩阵", "系统能力需求表", "稳定 ID", "承接纪律", "选集原则"):
            self.assertIn(term, traditional)
        for term in ("术语表", "研发下钻", "视觉下钻", "来源下钻", "同源", "低保真", "内部证据"):
            self.assertIn(term, traditional)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乳癌分層決策系統測試

測試綜合分析系統，整合 IHC4、AJCC 分期、生物標誌物
"""

import pytest
from breast_cancer_tools.stratification import (
    BreastCancerStratification,
    BiomarkerPanel,
    StratificationResult
)


class TestSubtypeClassification:
    """亞型分類測試"""

    def test_luminal_a_classification(self):
        """測試 Luminal A: ER+, PR+, HER2-, Ki67 low"""
        stratifier = BreastCancerStratification()
        subtype = stratifier.get_subtype(
            er_positive=True,
            pr_positive=True,
            her2_positive=False,
            ki67_percentage=15.0
        )
        assert subtype == "Luminal A-like"

    def test_luminal_b_her2_negative(self):
        """測試 Luminal B (HER2-): ER+, HER2-, Ki67 high"""
        stratifier = BreastCancerStratification()
        subtype = stratifier.get_subtype(
            er_positive=True,
            pr_positive=False,
            her2_positive=False,
            ki67_percentage=35.0
        )
        assert subtype == "Luminal B-like (HER2-)"

    def test_luminal_b_her2_positive(self):
        """測試 Luminal B (HER2+): ER+, HER2+"""
        stratifier = BreastCancerStratification()
        subtype = stratifier.get_subtype(
            er_positive=True,
            pr_positive=False,
            her2_positive=True,
            ki67_percentage=30.0
        )
        assert subtype == "Luminal B-like (HER2+)"

    def test_her2_enriched(self):
        """測試 HER2-enriched: ER-, PR-, HER2+"""
        stratifier = BreastCancerStratification()
        subtype = stratifier.get_subtype(
            er_positive=False,
            pr_positive=False,
            her2_positive=True,
            ki67_percentage=45.0
        )
        assert subtype == "HER2-enriched"

    def test_triple_negative(self):
        """測試 Triple Negative: ER-, PR-, HER2-"""
        stratifier = BreastCancerStratification()
        subtype = stratifier.get_subtype(
            er_positive=False,
            pr_positive=False,
            her2_positive=False,
            ki67_percentage=50.0
        )
        assert subtype == "Triple Negative"


class TestRiskCategorization:
    """風險分類測試"""

    def test_low_risk_luminal_a_early_stage(self):
        """測試低風險：Luminal A, Stage IA"""
        stratifier = BreastCancerStratification()
        risk = stratifier.get_risk_category(
            subtype="Luminal A-like",
            ajcc_stage="IA",
            grade=1,
            age=50,
            ihc4_score=1.5
        )
        assert risk == "Low Risk"

    def test_intermediate_risk_luminal_b_stage_iia(self):
        """測試中等風險：Luminal B, Stage IIA"""
        stratifier = BreastCancerStratification()
        risk = stratifier.get_risk_category(
            subtype="Luminal B-like (HER2-)",
            ajcc_stage="IIA",
            grade=2,
            age=50,
            ihc4_score=3.5
        )
        assert risk == "Intermediate Risk"

    def test_high_risk_her2_positive_stage_iii(self):
        """測試高風險：HER2+, Stage IIIA"""
        stratifier = BreastCancerStratification()
        risk = stratifier.get_risk_category(
            subtype="HER2-enriched",
            ajcc_stage="IIIA",
            grade=3,
            age=45,
            ihc4_score=None
        )
        assert risk == "High Risk"

    def test_high_risk_triple_negative_stage_ii(self):
        """測試高風險：TNBC, Stage IIB"""
        stratifier = BreastCancerStratification()
        risk = stratifier.get_risk_category(
            subtype="Triple Negative",
            ajcc_stage="IIB",
            grade=3,
            age=40,
            ihc4_score=None
        )
        assert risk == "High Risk"


class TestTherapyRecommendation:
    """治療推薦測試"""

    def test_luminal_a_early_stage(self):
        """測試 Luminal A 早期分期推薦"""
        stratifier = BreastCancerStratification()
        therapy = stratifier.recommend_therapy(
            subtype="Luminal A-like",
            ajcc_stage="IA",
            grade=1,
            her2_status="Negative",
            er_status="Positive"
        )
        assert therapy["surgery"] is True
        assert therapy["hormone_therapy"] is True
        assert therapy["chemotherapy"] is False
        assert therapy["trastuzumab"] is False

    def test_luminal_b_intermediate_stage(self):
        """測試 Luminal B 中期分期推薦"""
        stratifier = BreastCancerStratification()
        therapy = stratifier.recommend_therapy(
            subtype="Luminal B-like (HER2-)",
            ajcc_stage="IIA",
            grade=2,
            her2_status="Negative",
            er_status="Positive"
        )
        assert therapy["surgery"] is True
        assert therapy["hormone_therapy"] is True
        assert therapy["chemotherapy"] is True

    def test_her2_positive_recommendation(self):
        """測試 HER2+ 推薦 Trastuzumab"""
        stratifier = BreastCancerStratification()
        therapy = stratifier.recommend_therapy(
            subtype="HER2-enriched",
            ajcc_stage="IIA",
            grade=2,
            her2_status="Positive",
            er_status="Negative"
        )
        assert therapy["trastuzumab"] is True
        assert therapy["surgery"] is True
        assert therapy["chemotherapy"] is True

    def test_tnbc_chemotherapy_focus(self):
        """測試 TNBC 化療為主"""
        stratifier = BreastCancerStratification()
        therapy = stratifier.recommend_therapy(
            subtype="Triple Negative",
            ajcc_stage="IIB",
            grade=3,
            her2_status="Negative",
            er_status="Negative"
        )
        assert therapy["chemotherapy"] is True
        assert therapy["hormone_therapy"] is False
        assert therapy["trastuzumab"] is False


class TestStratification:
    """綜合分層測試"""

    def test_luminal_a_early_stage_stratification(self):
        """測試 Luminal A 早期分期完整分層"""
        stratifier = BreastCancerStratification()
        biomarker = BiomarkerPanel(
            er_h_score=250,
            pr_h_score=200,
            her2_score=0,
            ki67_percentage=15.0,
            grade=1,
            tumor_size_cm=1.8,
            lymph_node_status="N0",
            metastasis="M0",
            age=55
        )
        result = stratifier.stratify(biomarker)

        assert isinstance(result, StratificationResult)
        assert result.subtype == "Luminal A-like"
        assert result.ajcc_stage == "IA"
        assert result.risk_category == "Low Risk"
        assert result.confidence_level > 0.85

    def test_her2_positive_advanced_stratification(self):
        """測試 HER2+ 進展期完整分層"""
        stratifier = BreastCancerStratification()
        biomarker = BiomarkerPanel(
            er_h_score=50,
            pr_h_score=25,
            her2_score=300,
            ki67_percentage=40.0,
            grade=3,
            tumor_size_cm=4.5,
            lymph_node_status="N2a",
            metastasis="M0",
            age=48
        )
        result = stratifier.stratify(biomarker)

        assert result.subtype == "HER2-enriched"
        assert "III" in result.ajcc_stage
        assert result.risk_category == "High Risk"
        assert result.recommended_therapy.get("trastuzumab") is True

    def test_triple_negative_high_grade_stratification(self):
        """測試 TNBC 高分級完整分層"""
        stratifier = BreastCancerStratification()
        biomarker = BiomarkerPanel(
            er_h_score=0,
            pr_h_score=0,
            her2_score=0,
            ki67_percentage=60.0,
            grade=3,
            tumor_size_cm=3.2,
            lymph_node_status="N1",
            metastasis="M0",
            age=42
        )
        result = stratifier.stratify(biomarker)

        assert result.subtype == "Triple Negative"
        assert result.risk_category == "High Risk"
        assert result.recommended_therapy.get("chemotherapy") is True

    def test_metastatic_disease_stratification(self):
        """測試轉移性乳癌分層"""
        stratifier = BreastCancerStratification()
        biomarker = BiomarkerPanel(
            er_h_score=180,
            pr_h_score=80,
            her2_score=50,
            ki67_percentage=35.0,
            grade=3,
            tumor_size_cm=5.0,
            lymph_node_status="N3",
            metastasis="M1",
            age=60
        )
        result = stratifier.stratify(biomarker)

        assert result.ajcc_stage == "IV"
        assert result.risk_category == "High Risk"
        assert result.recommended_therapy.get("chemotherapy") is True


class TestReportGeneration:
    """報告生成測試"""

    def test_report_structure(self):
        """測試報告基本結構"""
        stratifier = BreastCancerStratification()
        biomarker = BiomarkerPanel(
            er_h_score=250,
            pr_h_score=200,
            her2_score=0,
            ki67_percentage=15.0,
            grade=1,
            tumor_size_cm=1.8,
            lymph_node_status="N0",
            metastasis="M0",
            age=55
        )
        result = stratifier.stratify(biomarker)
        report = stratifier.generate_report(result)

        assert isinstance(report, str)
        assert len(report) > 100


class TestEdgeCases:
    """邊界情況測試"""

    def test_er_negative_pr_positive_her2_negative(self):
        """測試罕見情況：ER-, PR+, HER2- → Luminal B-like (HER2-)"""
        stratifier = BreastCancerStratification()
        subtype = stratifier.get_subtype(
            er_positive=False,
            pr_positive=True,
            her2_positive=False,
            ki67_percentage=25.0
        )
        assert subtype == "Luminal B-like (HER2-)"

    def test_er_negative_pr_positive_her2_positive(self):
        """測試罕見情況：ER-, PR+, HER2+ → Luminal B-like (HER2+)"""
        stratifier = BreastCancerStratification()
        subtype = stratifier.get_subtype(
            er_positive=False,
            pr_positive=True,
            her2_positive=True,
            ki67_percentage=30.0
        )
        assert subtype == "Luminal B-like (HER2+)"

    def test_t4_chest_wall_invasion(self):
        """測試 T4 胸壁侵犯分類"""
        stratifier = BreastCancerStratification()
        biomarker = BiomarkerPanel(
            er_h_score=0,
            pr_h_score=0,
            her2_score=0,
            ki67_percentage=50.0,
            grade=3,
            tumor_size_cm=3.0,
            lymph_node_status="N1",
            metastasis="M0",
            age=50,
            chest_wall_skin_invasion=True
        )
        result = stratifier.stratify(biomarker)
        assert "III" in result.ajcc_stage

    def test_tumor_size_zero(self):
        """測試腫瘤大小為 0 的 T0 分類"""
        stratifier = BreastCancerStratification()
        t = stratifier._tumor_size_to_t(0.0)
        assert t == "T0"

    def test_tumor_size_microinvasion(self):
        """測試微浸潤 T1mi 分類 (≤0.1cm)"""
        stratifier = BreastCancerStratification()
        t = stratifier._tumor_size_to_t(0.08)
        assert t == "T1mi"

    def test_configurable_thresholds(self):
        """測試閾值可配置"""
        stratifier = BreastCancerStratification()
        # 驗證 class constants 存在且可修改
        assert hasattr(stratifier, 'ER_POSITIVE_THRESHOLD')
        assert hasattr(stratifier, 'PR_POSITIVE_THRESHOLD')
        assert hasattr(stratifier, 'HER2_POSITIVE_THRESHOLD')
        assert hasattr(stratifier, 'KI67_LOW_THRESHOLD')

    def test_ihc4_score_zero_in_report(self):
        """測試 IHC4 score 為 0 時仍應出現在報告中"""
        stratifier = BreastCancerStratification()
        result = StratificationResult(
            subtype="Luminal A-like",
            ajcc_stage="IA",
            ihc4_score=0.0,
            risk_category="Low Risk",
            recommended_therapy={"surgery": True},
            confidence_level=0.9
        )
        report = stratifier.generate_report(result)
        assert "IHC4" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

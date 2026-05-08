#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IHC4 Score 計算單元測試框架

測試覆蓋範圍：
- 輸入驗證
- 正確計算
- 亞型分類
- 風險分類
"""

import pytest
import sys
from pathlib import Path

# 添加模塊路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from ihc4_predictor import IHC4Calculator, BreastCancerSubtype


class TestIHC4Input:
    """輸入驗證測試"""

    def test_valid_er_score(self):
        """測試有效的 ER 評分"""
        calculator = IHC4Calculator()
        is_valid, errors = calculator.validate_input(
            er_score=250,
            pr_score=150,
            her2_score=0,
            ki67_percentage=15.0,
            age=50
        )
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_er_score_too_high(self):
        """測試 ER 評分超出範圍（過高）"""
        calculator = IHC4Calculator()
        is_valid, errors = calculator.validate_input(
            er_score=350,  # 超過 300
            pr_score=150,
            her2_score=0,
            ki67_percentage=15.0,
            age=50
        )
        assert is_valid is False
        assert len(errors) > 0

    def test_invalid_ki67_percentage(self):
        """測試無效的 Ki67 百分比"""
        calculator = IHC4Calculator()
        is_valid, errors = calculator.validate_input(
            er_score=250,
            pr_score=150,
            her2_score=0,
            ki67_percentage=150.0,  # 應為 0-100
            age=50
        )
        assert is_valid is False

    def test_invalid_age(self):
        """測試無效的年齡"""
        calculator = IHC4Calculator()
        is_valid, errors = calculator.validate_input(
            er_score=250,
            pr_score=150,
            her2_score=0,
            ki67_percentage=15.0,
            age=150  # 超過合理範圍
        )
        assert is_valid is False


class TestIHC4Calculation:
    """IHC4 計算測試"""

    def test_luminal_a_low_risk(self):
        """
        測試 Luminal A 型（低風險）計算

        特徵（患者案例）：
        - ER+: 250 (強陽性)
        - PR+: 150 (中陽性)
        - HER2-: 0
        - Ki67: 10% (低)
        - 年齡: 50
        - Grade: 2
        - 腫瘤大小: 2.0 cm

        預期結果（根據 PREDICT 工具）：
        - IHC4 Score: ~1.5-2.0（低風險）
        - 亞型: Luminal A
        - 風險: Low Risk
        - 推薦: 激素治療為主
        """
        calculator = IHC4Calculator()
        result = calculator.calculate(
            er_score=250,
            pr_score=150,
            her2_score=0,
            ki67_percentage=10.0,
            age=50,
            tumor_grade=2,
            tumor_size_cm=2.0
        )

        # 驗證亞型分類
        assert result.subtype == BreastCancerSubtype.LUMINAL_A, \
            f"Expected Luminal A, got {result.subtype}"

        # 驗證風險分類
        assert result.risk_category == "Low Risk", \
            f"Expected Low Risk, got {result.risk_category}"

        # 驗證 IHC4 評分範圍（低風險 < 2.0）
        assert result.ihc4_score < 2.0, \
            f"Expected IHC4 < 2.0 for Luminal A, got {result.ihc4_score}"

        # 驗證臨床建議
        assert "Hormone" in result.recommendation or "hormone" in result.recommendation, \
            f"Expected hormone therapy in recommendation, got: {result.recommendation}"

    def test_luminal_b_intermediate_risk(self):
        """
        測試 Luminal B 型（中風險）計算

        特徵（患者案例）：
        - ER+: 200 (中陽性)
        - PR+: 50 (弱陽性)
        - HER2-: 0
        - Ki67: 25% (高)
        - 年齡: 45
        - Grade: 3
        - 腫瘤大小: 3.0 cm

        預期結果：
        - IHC4 Score: ~2.5-3.5（中風險）
        - 亞型: Luminal B
        - 風險: Intermediate Risk
        - 推薦: 激素治療 + 化療考慮
        """
        calculator = IHC4Calculator()
        result = calculator.calculate(
            er_score=200,
            pr_score=50,
            her2_score=0,
            ki67_percentage=25.0,
            age=45,
            tumor_grade=3,
            tumor_size_cm=3.0
        )

        assert result.subtype == BreastCancerSubtype.LUMINAL_B, \
            f"Expected Luminal B, got {result.subtype}"
        assert result.risk_category == "Intermediate Risk", \
            f"Expected Intermediate Risk, got {result.risk_category}"
        assert 2.0 <= result.ihc4_score <= 4.0, \
            f"Expected IHC4 2.0-4.0 for Luminal B, got {result.ihc4_score}"

    def test_her2_positive(self):
        """
        測試 HER2+ 型計算

        特徵：
        - ER+: 150
        - PR+: 100
        - HER2+: 200 (強陽性)
        - Ki67: 30%
        """
        calculator = IHC4Calculator()
        result = calculator.calculate(
            er_score=150,
            pr_score=100,
            her2_score=200,
            ki67_percentage=30.0,
            age=50
        )

        # HER2+ 患者風險較高
        assert result.ihc4_score > 2.0

    def test_triple_negative(self):
        """
        測試三陰性乳癌

        特徵：
        - ER-: 0
        - PR-: 0
        - HER2-: 0
        - Ki67: 40% (高增殖)
        """
        calculator = IHC4Calculator()
        result = calculator.calculate(
            er_score=0,
            pr_score=0,
            her2_score=0,
            ki67_percentage=40.0,
            age=45,
            tumor_grade=3
        )

        assert result.subtype == BreastCancerSubtype.TRIPLE_NEGATIVE
        # IHC4 對三陰性乳癌的預後價值有限


class TestSubtypeClassification:
    """亞型分類測試"""

    def test_classify_luminal_a(self):
        """測試 Luminal A 分類"""
        calculator = IHC4Calculator()
        subtype = calculator.get_subtype_classification(
            er_score=250,
            pr_score=150,
            her2_score=0,
            ki67_percentage=10.0
        )
        assert subtype == BreastCancerSubtype.LUMINAL_A

    def test_classify_luminal_b(self):
        """測試 Luminal B 分類"""
        calculator = IHC4Calculator()
        subtype = calculator.get_subtype_classification(
            er_score=200,
            pr_score=50,
            her2_score=0,
            ki67_percentage=25.0
        )
        assert subtype == BreastCancerSubtype.LUMINAL_B

    def test_classify_her2_enriched(self):
        """測試 HER2-enriched 分類"""
        calculator = IHC4Calculator()
        subtype = calculator.get_subtype_classification(
            er_score=0,  # ER-
            pr_score=0,  # PR-
            her2_score=250,  # HER2+
            ki67_percentage=35.0
        )
        assert subtype == BreastCancerSubtype.HER2_ENRICHED

    def test_classify_triple_negative(self):
        """測試三陰性分類"""
        calculator = IHC4Calculator()
        subtype = calculator.get_subtype_classification(
            er_score=0,
            pr_score=0,
            her2_score=0,
            ki67_percentage=40.0
        )
        assert subtype == BreastCancerSubtype.TRIPLE_NEGATIVE


class TestPredictScore:
    """Predict Score 計算測試"""

    def test_predict_score_calculation(self):
        """測試 Predict Score 計算"""
        calculator = IHC4Calculator()
        result = calculator.calculate_predict_score(
            ihc4_score=3.45,
            age=55,
            tumor_size_cm=2.5,
            grade=2
        )

        assert result is not None
        assert 'score' in result
        assert 'endocrine_benefit' in result


class TestEdgeCases:
    """邊界情況測試"""

    def test_boundary_er_score_zero(self):
        """測試 ER 評分為 0（陰性）"""
        calculator = IHC4Calculator()
        is_valid, _ = calculator.validate_input(
            er_score=0,
            pr_score=0,
            her2_score=0,
            ki67_percentage=50.0,
            age=40
        )
        assert is_valid is True

    def test_boundary_er_score_max(self):
        """測試 ER 評分為 300（最高）"""
        calculator = IHC4Calculator()
        is_valid, _ = calculator.validate_input(
            er_score=300,
            pr_score=300,
            her2_score=300,
            ki67_percentage=100.0,
            age=80
        )
        assert is_valid is True

    def test_young_patient(self):
        """測試年輕患者"""
        calculator = IHC4Calculator()
        is_valid, _ = calculator.validate_input(
            er_score=250,
            pr_score=150,
            her2_score=0,
            ki67_percentage=20.0,
            age=25  # 較年輕
        )
        assert is_valid is True

    def test_elderly_patient(self):
        """測試老年患者"""
        calculator = IHC4Calculator()
        is_valid, _ = calculator.validate_input(
            er_score=250,
            pr_score=150,
            her2_score=0,
            ki67_percentage=10.0,
            age=85  # 較年長
        )
        assert is_valid is True


if __name__ == "__main__":
    # 運行測試: pytest test_ihc4.py -v
    pytest.main([__file__, "-v"])

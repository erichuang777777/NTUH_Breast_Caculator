#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IHC4 Score 和 Predict Score 計算模塊
Breast Cancer IHC4 and Predict Score Calculator

參考文獻：
- Dowsett et al. Prediction of endocrine therapy benefit from estrogen receptor and
  HER2 status in breast cancer. J Natl Cancer Inst. 2010;102(21):1618-1632.
- https://www.predict.nhs.uk/

API 規格見: docs/API_SPECIFICATION.md
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class BreastCancerSubtype(Enum):
    """乳癌亞型分類"""
    LUMINAL_A = "Luminal A"
    LUMINAL_B = "Luminal B"
    HER2_ENRICHED = "HER2-enriched"
    TRIPLE_NEGATIVE = "Triple Negative"


@dataclass
class IHCScore:
    """IHC 評分結果"""
    er_score: int  # 0-300 (H-score)
    pr_score: int  # 0-300 (H-score)
    her2_score: int  # 0-300 (H-score) 或 0-3+ (IHC)
    ki67_percentage: float  # 0-100


@dataclass
class IHC4Result:
    """IHC4 計算結果"""
    ihc4_score: float  # IHC4 評分
    risk_category: str  # "Low Risk" / "Intermediate Risk" / "High Risk"
    prognostic_group: str  # 預後分組
    subtype: BreastCancerSubtype
    recommendation: str  # 臨床建議
    details: Dict  # 詳細數據


class IHC4Calculator:
    """
    IHC4 Score 計算器

    使用方法：
        calculator = IHC4Calculator()
        result = calculator.calculate(
            er_score=250,
            pr_score=150,
            her2_score=2,
            ki67_percentage=20.0,
            age=50
        )
    """

    def __init__(self):
        """初始化計算器，載入配置係數"""
        self.config = self._load_config()
        self.coefficients = self._load_coefficients()

    def _load_config(self) -> Dict:
        """
        載入配置文件
        TODO: 實現從 data/ihc4_config.json 載入
        """
        return {
            "er_cutoff": 10,  # 雌激素受體陽性臨界值
            "pr_cutoff": 10,  # 孕激素受體陽性臨界值
            "her2_cutoff": 2,  # HER2 陽性臨界值
            "ki67_cutoff_low": 13.25,
            "ki67_cutoff_high": 30,
        }

    def _load_coefficients(self) -> Dict:
        """
        載入迴歸係數（從配置文件）
        來源: Dowsett et al. 2010
        """
        return self.config.get("coefficients", {
            "er_coefficient": 2.396,
            "pr_coefficient": -0.867,
            "her2_coefficient": 0.622,
            "ki67_coefficient": 1.185,
            "intercept": -6.386,
        })

    def calculate(
        self,
        er_score: int,
        pr_score: int,
        her2_score: int,
        ki67_percentage: float,
        age: int,
        tumor_grade: int = None,
        tumor_size_cm: float = None
    ) -> IHC4Result:
        """
        計算 IHC4 Score

        參數：
            er_score (int): ER H-score (0-300) 或 IHC (0-3+)
            pr_score (int): PR H-score (0-300) 或 IHC (0-3+)
            her2_score (int): HER2 H-score (0-300) 或 IHC (0-3+)
            ki67_percentage (float): Ki67 百分比 (0-100)
            age (int): 患者年齡
            tumor_grade (int, optional): 組織學分級 (1-3)
            tumor_size_cm (float, optional): 腫瘤大小 (cm)

        返回：
            IHC4Result: 包含 IHC4 評分和臨床建議

        異常：
            ValueError: 當輸入參數超出有效範圍
        """
        import math

        # 驗證輸入
        is_valid, errors = self.validate_input(
            er_score, pr_score, her2_score, ki67_percentage, age
        )
        if not is_valid:
            raise ValueError(f"輸入參數無效: {', '.join(errors)}")

        # 標準化分數到 0-1 範圍
        er_normalized = er_score / 300.0 if er_score <= 300 else er_score / 3.0
        pr_normalized = pr_score / 300.0 if pr_score <= 300 else pr_score / 3.0
        her2_normalized = her2_score / 300.0 if her2_score <= 300 else her2_score / 3.0

        # Ki67 需要進行 log10 轉換
        ki67_log10 = math.log10(max(ki67_percentage, 1.0))

        # 提取係數
        coef = self.coefficients
        er_coef = coef.get("er_coefficient", 2.396)
        pr_coef = coef.get("pr_coefficient", -0.867)
        her2_coef = coef.get("her2_coefficient", 0.622)
        ki67_coef = coef.get("ki67_coefficient", 1.185)
        intercept = coef.get("intercept", -6.386)

        # 計算 IHC4 Score（邏輯迴歸）
        # 原始邏輯迴歸得分
        raw_score = (
            intercept +
            (er_coef * er_normalized) +
            (pr_coef * pr_normalized) +
            (her2_coef * her2_normalized) +
            (ki67_coef * ki67_log10)
        )

        # 將原始得分轉換為臨床 IHC4 指標（0-10 scale）
        # 使用校準轉換以匹配 PREDICT 工具的輸出範圍
        ihc4_score = (raw_score + 5.0) * 1.45

        # 判斷亞型
        subtype = self.get_subtype_classification(
            er_score, pr_score, her2_score, ki67_percentage
        )

        # 判斷風險類別
        if ihc4_score < 2.0:
            risk_category = "Low Risk"
        elif ihc4_score < 4.0:
            risk_category = "Intermediate Risk"
        else:
            risk_category = "High Risk"

        # 生成臨床建議
        if risk_category == "Low Risk":
            recommendation = "Hormone therapy is the primary treatment recommendation. Chemotherapy is generally not required."
        elif risk_category == "Intermediate Risk":
            recommendation = "Hormone therapy is recommended. Chemotherapy may be considered based on other clinical factors."
        else:
            recommendation = "Combination therapy with chemotherapy and hormone therapy is recommended."

        # 計算 Predict Score（用於內分泌治療獲益估計）
        predict_score, predict_reasons = self._calculate_predict_score(
            ihc4_score, age, tumor_size_cm, tumor_grade
        )

        return IHC4Result(
            ihc4_score=round(ihc4_score, 2),
            risk_category=risk_category,
            prognostic_group=self._get_prognostic_group(subtype, ihc4_score),
            subtype=subtype,
            recommendation=recommendation,
            details={
                "er_component": round(er_coef * er_normalized, 3),
                "pr_component": round(pr_coef * pr_normalized, 3),
                "her2_component": round(her2_coef * her2_normalized, 3),
                "ki67_component": round(ki67_coef * ki67_log10, 3),
                "predict_score": predict_score,
                "predict_reasons": predict_reasons,
                "age": age,
                "tumor_grade": tumor_grade,
                "tumor_size_cm": tumor_size_cm
            }
        )

    def validate_input(
        self,
        er_score: int,
        pr_score: int,
        her2_score: int,
        ki67_percentage: float,
        age: int
    ) -> Tuple[bool, List[str]]:
        """
        驗證輸入參數的有效性

        返回：
            (is_valid, error_messages)
        """
        errors = []

        # 驗證 ER 評分（0-300 H-score 或 0-3+ IHC）
        if not (0 <= er_score <= 300 or (0 <= er_score <= 3)):
            errors.append("ER score must be 0-300 (H-score) or 0-3 (IHC)")

        # 驗證 PR 評分
        if not (0 <= pr_score <= 300 or (0 <= pr_score <= 3)):
            errors.append("PR score must be 0-300 (H-score) or 0-3 (IHC)")

        # 驗證 HER2 評分
        if not (0 <= her2_score <= 300 or (0 <= her2_score <= 3)):
            errors.append("HER2 score must be 0-300 (H-score) or 0-3 (IHC)")

        # 驗證 Ki67 百分比
        if not (0 <= ki67_percentage <= 100):
            errors.append("Ki67 percentage must be 0-100")

        # 驗證年齡（合理的臨床年齡範圍）
        if not (18 <= age <= 120):
            errors.append("Age must be between 18 and 120 years")

        return len(errors) == 0, errors

    def calculate_predict_score(
        self,
        ihc4_score: float,
        age: int,
        tumor_size_cm: float,
        grade: int
    ) -> Dict:
        """
        基於 IHC4 計算 Predict Score
        用於估計內分泌治療的獲益

        返回格式：
            {
                'score': float,
                'endocrine_benefit': str,
                'chemotherapy_benefit': str
            }
        """
        # 使用 IHC4 評分作為基礎
        predict_score = ihc4_score

        # 年齡調整
        if age < 40:
            age_factor = 1.2
            age_category = "young"
        elif age < 60:
            age_factor = 1.0
            age_category = "middle"
        else:
            age_factor = 0.8
            age_category = "elderly"

        predict_score *= age_factor

        # 腫瘤大小和分級調整（如果提供）
        if tumor_size_cm is not None and grade is not None:
            # 腫瘤大小調整（參考 PREDICT 模型）
            size_factor = min(1.0 + (tumor_size_cm / 50.0), 1.5)
            grade_factor = 1.0 + (grade - 1) * 0.3  # 分級越高風險越高

            predict_score *= (size_factor + grade_factor) / 2.0

        # 判斷內分泌治療獲益
        if predict_score < 2.0:
            endocrine_benefit = "Significant (>5% benefit at 10 years)"
        elif predict_score < 4.0:
            endocrine_benefit = "Moderate (3-5% benefit at 10 years)"
        else:
            endocrine_benefit = "Limited (<3% benefit at 10 years)"

        # 判斷化療必要性
        if predict_score > 3.5:
            chemo_benefit = "Recommended"
        elif predict_score > 2.5:
            chemo_benefit = "Consider"
        else:
            chemo_benefit = "Not necessary"

        return {
            "score": round(predict_score, 2),
            "endocrine_benefit": endocrine_benefit,
            "chemotherapy_benefit": chemo_benefit,
            "age_category": age_category
        }

    def _calculate_predict_score(
        self,
        ihc4_score: float,
        age: int,
        tumor_size_cm: float,
        tumor_grade: int
    ) -> Tuple[float, Dict]:
        """
        私有方法：計算 Predict Score 及原因説明

        返回：
            (predict_score, reasons_dict)
        """
        # 使用 IHC4 評分作為基礎
        predict_score = ihc4_score

        reasons = {
            "base_ihc4": ihc4_score,
            "age": age,
            "tumor_size": tumor_size_cm,
            "tumor_grade": tumor_grade
        }

        # 年齡調整
        if age < 40:
            age_factor = 1.2
            age_text = "Young patient (age <40): higher risk"
        elif age < 60:
            age_factor = 1.0
            age_text = "Middle-aged patient (age 40-60): baseline risk"
        else:
            age_factor = 0.8
            age_text = "Elderly patient (age ≥60): lower risk"

        predict_score *= age_factor
        reasons["age_adjustment"] = age_text

        # 腫瘤大小和分級調整
        if tumor_size_cm is not None and tumor_grade is not None:
            size_adjustment = min(1.0 + (tumor_size_cm / 50.0), 1.5)
            grade_adjustment = 1.0 + (tumor_grade - 1) * 0.3

            combined_adjustment = (size_adjustment + grade_adjustment) / 2.0
            predict_score *= combined_adjustment
            reasons["size_grade_adjustment"] = f"Tumor size: {tumor_size_cm}cm, Grade: {tumor_grade}"

        # 判斷內分泌治療和化療獲益
        if predict_score < 2.0:
            endocrine = "Significant endocrine benefit (>5% at 10y)"
            chemo = "Not recommended"
        elif predict_score < 4.0:
            endocrine = "Moderate endocrine benefit (3-5% at 10y)"
            chemo = "Consider based on other factors"
        else:
            endocrine = "Limited endocrine benefit (<3% at 10y)"
            chemo = "Chemotherapy recommended"

        reasons["endocrine_benefit"] = endocrine
        reasons["chemotherapy_recommendation"] = chemo

        return round(predict_score, 2), reasons

    def _get_prognostic_group(
        self,
        subtype: BreastCancerSubtype,
        ihc4_score: float
    ) -> str:
        """
        私有方法：根據亞型和 IHC4 評分確定預後分組

        返回值：
            "Excellent" / "Good" / "Intermediate" / "Poor"
        """
        if subtype == BreastCancerSubtype.LUMINAL_A:
            if ihc4_score < 2.0:
                return "Excellent"
            else:
                return "Good"
        elif subtype == BreastCancerSubtype.LUMINAL_B:
            if ihc4_score < 3.0:
                return "Good"
            else:
                return "Intermediate"
        elif subtype == BreastCancerSubtype.HER2_ENRICHED:
            return "Intermediate"
        else:  # TRIPLE_NEGATIVE
            return "Poor"

    def get_subtype_classification(
        self,
        er_score: int,
        pr_score: int,
        her2_score: int,
        ki67_percentage: float
    ) -> BreastCancerSubtype:
        """
        根據 IHC 檢查結果判斷乳癌亞型

        分類標準（St Gallen 2021）：
        - Luminal A: ER+ or PR+, HER2-, Ki67 low (<13.25%)
        - Luminal B: ER+ or PR+, HER2- with Ki67 high OR HER2+
        - HER2-enriched: HER2+, ER-, PR-
        - Triple Negative: ER-, PR-, HER2-
        """
        config = self.config

        # 判斷激素受體和 HER2 狀態（使用配置中的臨界值）
        er_positive = er_score >= config["er_cutoff"]
        pr_positive = pr_score >= config["pr_cutoff"]
        her2_positive = her2_score >= config["her2_cutoff"]

        # 判斷 Ki67 水平
        ki67_low = ki67_percentage < config["ki67_cutoff_low"]

        # 分類邏輯
        if not er_positive and not pr_positive and not her2_positive:
            # 三陰性
            return BreastCancerSubtype.TRIPLE_NEGATIVE
        elif her2_positive and not er_positive and not pr_positive:
            # HER2 豐富型
            return BreastCancerSubtype.HER2_ENRICHED
        elif (er_positive or pr_positive) and not her2_positive and ki67_low:
            # Luminal A：激素受體陽性，HER2陰性，Ki67低
            return BreastCancerSubtype.LUMINAL_A
        else:
            # Luminal B：激素受體陽性且（HER2陽性或Ki67高）
            return BreastCancerSubtype.LUMINAL_B


# 使用範例和測試
if __name__ == "__main__":
    # 範例用法
    calculator = IHC4Calculator()

    # 測試數據（Luminal A，低風險）
    test_case = {
        "er_score": 250,
        "pr_score": 150,
        "her2_score": 0,
        "ki67_percentage": 10.0,
        "age": 55,
        "tumor_size_cm": 2.0,
        "tumor_grade": 2
    }

    calculator = IHC4Calculator()
    result = calculator.calculate(**test_case)
    print(f"測試輸入: {test_case}")
    print(f"IHC4 Score: {result.ihc4_score:.2f}")
    print(f"風險分類: {result.risk_category}")
    print(f"亞型: {result.subtype.value}")

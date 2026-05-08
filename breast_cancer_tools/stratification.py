#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乳癌臨床分層決策整合模塊
Breast Cancer Stratification Decision Support System

整合 IHC4、Predict Score、AJCC 分期、
生物標誌物、組織學特徵，提供綜合的臨床決策支持

使用方法見 docs/USAGE_GUIDE.md
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from .ihc4_predictor import IHC4Calculator
from .ajcc_converter import AJCCStageConverter, AJCCStage


@dataclass
class BiomarkerPanel:
    """生物標誌物檢查結果"""
    er_h_score: int  # 0-300
    pr_h_score: int  # 0-300
    her2_score: int  # 0-300 或 0-3+
    ki67_percentage: float  # 0-100
    grade: int  # 1-3
    tumor_size_cm: float
    lymph_node_status: str  # N0, N1, N2, N3
    metastasis: str  # M0, M1
    age: int
    chest_wall_skin_invasion: bool = False  # T4 分類所需


@dataclass
class StratificationResult:
    """分層決策結果"""
    subtype: str  # Luminal A, Luminal B, HER2+, TNBC
    ajcc_stage: str
    ihc4_score: Optional[float] = None
    predict_score: Optional[float] = None
    risk_category: str = ""
    recommended_therapy: Dict = field(default_factory=dict)
    clinical_notes: List[str] = field(default_factory=list)
    confidence_level: float = 0.0  # 0-1


class BreastCancerStratification:
    """
    乳癌臨床分層決策系統

    整合多個分析工具，提供綜合的臨床決策支持

    使用方法：
        stratifier = BreastCancerStratification()
        result = stratifier.stratify(biomarker_panel)
    """

    # H-score 陽性閾值（用於亞型分類）
    # 參考 St Gallen 2021 共識：亞型分類使用「強陽性」標準
    # - ER/PR: H-score > 100 視為亞型分類中的陽性（強表達）
    #   注意：ASCO/CAP 治療決策使用 ≥1%（H-score ~3），此處更嚴格
    # - HER2: H-score > 100 對應 IHC 3+（明確陽性）
    # - Ki67: <20% 為低增殖（Luminal A 判定標準）
    ER_POSITIVE_THRESHOLD = 100
    PR_POSITIVE_THRESHOLD = 100
    HER2_POSITIVE_THRESHOLD = 100
    KI67_LOW_THRESHOLD = 20

    def __init__(self):
        """初始化分層系統"""
        self.ihc4_calculator = IHC4Calculator()
        self.ajcc_converter = AJCCStageConverter(edition=9)

    def stratify(self, biomarker: BiomarkerPanel) -> StratificationResult:
        """
        進行乳癌分層分析

        參數：
            biomarker (BiomarkerPanel): 生物標誌物檢查結果

        返回：
            StratificationResult: 分層決策結果

        執行步驟：
        1. 判斷亞型分類 (Luminal A/B, HER2+, TNBC)
        2. 計算 IHC4 Score (如適用)
        3. 計算 Predict Score (如適用)
        4. 轉換 AJCC 分期
        5. 確定風險類別
        6. 推薦治療方案
        7. 生成臨床備註
        """
        # 1. Convert H-scores to biomarker status
        er_positive = biomarker.er_h_score > self.ER_POSITIVE_THRESHOLD
        pr_positive = biomarker.pr_h_score > self.PR_POSITIVE_THRESHOLD
        her2_positive = biomarker.her2_score > self.HER2_POSITIVE_THRESHOLD

        # 2. Classify subtype
        subtype = self.get_subtype(
            er_positive=er_positive,
            pr_positive=pr_positive,
            her2_positive=her2_positive,
            ki67_percentage=biomarker.ki67_percentage
        )

        # 3. Convert tumor size to T classification
        t_classification = self._tumor_size_to_t(
            biomarker.tumor_size_cm,
            chest_wall_skin_invasion=biomarker.chest_wall_skin_invasion
        )
        n_classification = biomarker.lymph_node_status
        m_classification = "M1" if biomarker.metastasis == "M1" else "M0"

        # 4. Calculate AJCC stage
        er_status = "Positive" if er_positive else "Negative"
        pr_status = "Positive" if pr_positive else "Negative"
        her2_status = "Positive" if her2_positive else "Negative"

        ajcc_result = self.ajcc_converter.convert(
            t=t_classification,
            n=n_classification,
            m=m_classification,
            grade=biomarker.grade,
            er_status=er_status,
            pr_status=pr_status,
            her2_status=her2_status
        )
        # Extract stage string from AJCCStage enum (e.g., "Stage IA" -> "IA")
        ajcc_stage_enum = ajcc_result.clinical_stage
        stage_value = ajcc_stage_enum.value if hasattr(ajcc_stage_enum, 'value') else str(ajcc_stage_enum)
        ajcc_stage = stage_value.replace("Stage ", "")

        # 5. Calculate IHC4 score (if Luminal)
        ihc4_score = None
        if "Luminal" in subtype:
            ihc4_result = self.ihc4_calculator.calculate(
                er_score=biomarker.er_h_score,
                pr_score=biomarker.pr_h_score,
                her2_score=biomarker.her2_score,
                ki67_percentage=biomarker.ki67_percentage,
                age=biomarker.age,
                tumor_grade=biomarker.grade,
                tumor_size_cm=biomarker.tumor_size_cm
            )
            ihc4_score = ihc4_result.ihc4_score

        # 6. Determine risk category
        risk_category = self.get_risk_category(
            subtype=subtype,
            ajcc_stage=ajcc_stage,
            grade=biomarker.grade,
            age=biomarker.age,
            ihc4_score=ihc4_score
        )

        # 7. Recommend therapy
        recommended_therapy = self.recommend_therapy(
            subtype=subtype,
            ajcc_stage=ajcc_stage,
            grade=biomarker.grade,
            her2_status=her2_status,
            er_status=er_status
        )

        # 8. Calculate confidence level
        confidence_level = self._calculate_confidence(
            biomarker=biomarker,
            subtype=subtype
        )

        return StratificationResult(
            subtype=subtype,
            ajcc_stage=ajcc_stage,
            ihc4_score=ihc4_score,
            risk_category=risk_category,
            recommended_therapy=recommended_therapy,
            confidence_level=confidence_level
        )

    def get_subtype(
        self,
        er_positive: bool,
        pr_positive: bool,
        her2_positive: bool,
        ki67_percentage: float
    ) -> str:
        """
        判斷乳癌亞型

        分類標準 (St Gallen 2021)：
        - Luminal A-like: ER+/PR+, HER2-, Ki67 low (<20%)
        - Luminal B-like (HER2-): ER+, HER2-, Ki67 high (>20%) or PR-
        - Luminal B-like (HER2+): ER+, HER2+
        - HER2-enriched: ER-, PR-, HER2+
        - Triple Negative: ER-, PR-, HER2-

        返回：
            亞型名稱
        """
        # Triple Negative: ER-, PR-, HER2-
        if not er_positive and not pr_positive and not her2_positive:
            return "Triple Negative"

        # HER2-enriched: ER-, PR-, HER2+
        if not er_positive and not pr_positive and her2_positive:
            return "HER2-enriched"

        # ER-, PR+, HER2+ (罕見): 歸類為 Luminal B-like (HER2+)
        # ER-, PR+, HER2- (罕見): 歸類為 Luminal B-like (HER2-)
        # 參考: St Gallen 2021 共識將 PR 單獨陽性視為荷爾蒙受體陽性
        hormone_receptor_positive = er_positive or pr_positive

        # Luminal B-like (HER2+): 荷爾蒙受體陽性 + HER2+
        if hormone_receptor_positive and her2_positive:
            return "Luminal B-like (HER2+)"

        # Luminal A-like vs Luminal B-like (HER2-)
        if hormone_receptor_positive and not her2_positive:
            # Luminal A-like: ER+, PR+, HER2-, Ki67 low
            if er_positive and pr_positive and ki67_percentage < self.KI67_LOW_THRESHOLD:
                return "Luminal A-like"
            # Luminal B-like (HER2-): HR+, HER2-, (PR- or Ki67 high or ER-)
            else:
                return "Luminal B-like (HER2-)"

        return "Unknown"

    def get_risk_category(
        self,
        subtype: str,
        ajcc_stage: str,
        grade: int,
        age: int,
        ihc4_score: Optional[float] = None
    ) -> str:
        """
        確定風險類別

        風險分類：
        - Low Risk: Luminal A, early stage
        - Intermediate Risk: Luminal B, moderate stage
        - High Risk: HER2+, TNBC, advanced stage
        """
        # Extract stage number from string (e.g., "IIA" -> 2)
        stage_num = self._extract_stage_number(ajcc_stage)

        # HER2-enriched and Triple Negative are high risk
        if subtype in ["HER2-enriched", "Triple Negative"]:
            return "High Risk"

        # Advanced stages (III, IV) are high risk
        if stage_num >= 3:
            return "High Risk"

        # Luminal A early stage is low risk
        if subtype == "Luminal A-like" and stage_num <= 1:
            return "Low Risk"

        # Luminal B with early-mid stage is intermediate
        if "Luminal B" in subtype and stage_num <= 2:
            return "Intermediate Risk"

        # Everything else defaults to intermediate or high
        if stage_num >= 2:
            return "Intermediate Risk"

        return "Low Risk"

    def recommend_therapy(
        self,
        subtype: str,
        ajcc_stage: str,
        grade: int,
        her2_status: str,
        er_status: str
    ) -> Dict:
        """
        根據亞型和分期推薦治療方案

        返回：
            {
                "surgery": bool,
                "chemotherapy": bool,
                "hormone_therapy": bool,
                "trastuzumab": bool,
                "pertuzumab": bool,
                "immunotherapy": bool,
                "cdk4_6_inhibitor": bool,
                "radiotherapy": bool,
                "specific_drugs": [列表],
                "notes": "臨床建議"
            }
        """
        stage_num = self._extract_stage_number(ajcc_stage)

        # Initialize base recommendation
        therapy = {
            "surgery": True,  # Most cases need surgery
            "chemotherapy": False,
            "hormone_therapy": False,
            "trastuzumab": False,
            "pertuzumab": False,
            "immunotherapy": False,
            "cdk4_6_inhibitor": False,
            "radiotherapy": False,
            "specific_drugs": [],
            "notes": ""
        }

        # Luminal A-like
        if subtype == "Luminal A-like":
            therapy["hormone_therapy"] = True
            if stage_num >= 2:
                therapy["chemotherapy"] = True
            therapy["notes"] = "Endocrine therapy is primary treatment; chemotherapy for higher stages"

        # Luminal B-like
        elif "Luminal B" in subtype:
            therapy["hormone_therapy"] = True
            therapy["chemotherapy"] = True
            if her2_status == "Positive":
                therapy["trastuzumab"] = True
                therapy["notes"] = "Chemotherapy + trastuzumab + endocrine therapy"
            else:
                therapy["notes"] = "Chemotherapy + endocrine therapy; consider CDK4/6 inhibitor"
            if stage_num >= 3:
                therapy["cdk4_6_inhibitor"] = True

        # HER2-enriched
        elif subtype == "HER2-enriched":
            therapy["chemotherapy"] = True
            therapy["trastuzumab"] = True
            if stage_num >= 2:
                therapy["pertuzumab"] = True
            therapy["notes"] = "Dual HER2 targeting with trastuzumab/pertuzumab + chemotherapy"

        # Triple Negative
        elif subtype == "Triple Negative":
            therapy["chemotherapy"] = True
            therapy["hormone_therapy"] = False
            if stage_num >= 3:
                therapy["immunotherapy"] = True
            therapy["notes"] = "Chemotherapy is primary treatment; consider immunotherapy for advanced disease"

        return therapy

    def generate_report(self, result: StratificationResult) -> str:
        """
        生成臨床分層報告

        返回：
            格式化的醫學報告文本
        """
        report = []
        report.append("=" * 60)
        report.append("乳癌臨床分層決策報告")
        report.append("=" * 60)
        report.append("")

        report.append(f"病理亞型: {result.subtype}")
        report.append(f"AJCC 分期: {result.ajcc_stage}")
        report.append(f"風險分類: {result.risk_category}")
        report.append("")

        if result.ihc4_score is not None:
            report.append(f"IHC4 預測分數: {result.ihc4_score:.2f}")

        report.append(f"信心程度: {result.confidence_level:.1%}")
        report.append("")

        report.append("推薦治療方案:")
        if result.recommended_therapy.get("surgery"):
            report.append("  • 手術: 是")
        if result.recommended_therapy.get("chemotherapy"):
            report.append("  • 化學治療: 是")
        if result.recommended_therapy.get("hormone_therapy"):
            report.append("  • 荷爾蒙治療: 是")
        if result.recommended_therapy.get("trastuzumab"):
            report.append("  • Trastuzumab (HER2標靶): 是")
        if result.recommended_therapy.get("pertuzumab"):
            report.append("  • Pertuzumab: 是")
        if result.recommended_therapy.get("immunotherapy"):
            report.append("  • 免疫治療: 是")
        if result.recommended_therapy.get("cdk4_6_inhibitor"):
            report.append("  • CDK4/6 抑制劑: 是")

        if result.recommended_therapy.get("notes"):
            report.append("")
            report.append("臨床備註:")
            report.append(f"  {result.recommended_therapy['notes']}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


    def _tumor_size_to_t(
        self,
        tumor_size_cm: float,
        chest_wall_skin_invasion: bool = False
    ) -> str:
        """
        將腫瘤大小轉換為 T 分類

        參數：
            tumor_size_cm: 腫瘤大小 (cm)
            chest_wall_skin_invasion: 是否侵犯胸壁或皮膚 (T4)

        返回：
            T 分類 (T0, T1mi, T1, T2, T3, T4)
        """
        # T4: 任何大小但侵犯胸壁或皮膚
        if chest_wall_skin_invasion:
            return "T4"
        if tumor_size_cm <= 0:
            return "T0"
        elif tumor_size_cm <= 0.1:
            return "T1mi"  # Microinvasion ≤ 1mm
        elif tumor_size_cm <= 2:
            return "T1"
        elif tumor_size_cm <= 5:
            return "T2"
        else:
            return "T3"

    def _extract_stage_number(self, stage_str: str) -> int:
        """
        從分期字符串提取階段數字

        示例：
            "IA" -> 1
            "IIA" -> 2
            "IIIA" -> 3
            "IV" -> 4
        """
        if "IV" in stage_str:
            return 4
        elif "III" in stage_str:
            return 3
        elif "II" in stage_str:
            return 2
        elif "I" in stage_str:
            return 1
        else:
            return 0

    def _calculate_confidence(
        self,
        biomarker: BiomarkerPanel,
        subtype: str
    ) -> float:
        """
        計算分層結果的信心程度 (0-1)

        基於：
        - 生物標誌物的清晰程度
        - 年齡是否在典型範圍內
        - 亞型的確定性
        """
        confidence = 0.7  # Base confidence

        # 增加信心度如果生物標誌物清晰
        er_score = biomarker.er_h_score
        her2_score = biomarker.her2_score

        # 如果標誌物清晰（明確陰性或明確陽性）
        if (er_score < 10 or er_score > 200) and (her2_score < 20 or her2_score > 200):
            confidence += 0.15

        # 如果年齡在合理範圍
        if 30 <= biomarker.age <= 80:
            confidence += 0.05

        # 限制在 0-1 之間
        return min(max(confidence, 0.0), 1.0)


# 使用範例
if __name__ == "__main__":
    # 範例用法
    stratifier = BreastCancerStratification()

    # 測試數據
    biomarker = BiomarkerPanel(
        er_h_score=250,
        pr_h_score=150,
        her2_score=0,
        ki67_percentage=15.0,
        grade=2,
        tumor_size_cm=2.5,
        lymph_node_status="N1",
        metastasis="M0",
        age=55
    )

    result = stratifier.stratify(biomarker)
    report = stratifier.generate_report(result)
    print(report)

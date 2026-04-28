#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AJCC 乳癌分期轉換模塊
AJCC Breast Cancer TNM to Stage Converter

支持：
- AJCC 8th Edition (2017)
- AJCC 9th Edition (2023) - 新版

參考：
- https://cancerstaging.org/
- AJCC Cancer Staging Manual, 8th and 9th editions

API 規格見: docs/API_SPECIFICATION.md
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class TumorSize(Enum):
    """腫瘤大小分類 (T classification)"""
    TX = "TX"  # Cannot be assessed
    T0 = "T0"  # No evidence of primary tumor
    T1MI = "T1mi"  # Microinvasion
    T1A = "T1a"  # ≤0.5 cm
    T1B = "T1b"  # >0.5 to ≤1.0 cm
    T1C = "T1c"  # >1.0 to ≤2.0 cm
    T2 = "T2"  # >2.0 to ≤5.0 cm
    T3 = "T3"  # >5.0 cm
    T4A = "T4a"  # Chest wall
    T4B = "T4b"  # Skin involvement
    T4C = "T4c"  # Both chest wall and skin
    T4D = "T4d"  # Inflammatory carcinoma


class LymphNodeStatus(Enum):
    """淋巴結狀態分類 (N classification)"""
    NX = "NX"  # Cannot be assessed
    N0 = "N0"  # No regional lymph node metastasis
    N0_I_PLUS = "N0(i+)"  # Isolated tumor cells only
    N0_MOL_PLUS = "N0(mol+)"  # No histologic/cytologic evidence but molecular evidence
    N1 = "N1"  # Micrometastasis or 1-3 axillary nodes
    N1MI = "N1mi"  # Micrometastasis
    N1A = "N1a"  # 1-3 axillary nodes
    N2 = "N2"  # 4-9 axillary or positive internal mammary nodes
    N2A = "N2a"  # 4-9 axillary nodes
    N2B = "N2b"  # Positive internal mammary nodes
    N3 = "N3"  # ≥10 axillary or clavicular/supraclavicular nodes
    N3A = "N3a"  # ≥10 axillary nodes
    N3B = "N3b"  # Positive ipsilateral internal mammary & axillary nodes
    N3C = "N3c"  # Ipsilateral supraclavicular nodes


class MetastasisStatus(Enum):
    """遠端轉移分類 (M classification)"""
    MX = "MX"  # Cannot be assessed
    M0 = "M0"  # No clinical or radiologic evidence of distant metastasis
    M1 = "M1"  # Distant metastasis present


class AJCCStage(Enum):
    """AJCC 分期 (0-IIIC)"""
    STAGE_0 = "Stage 0"
    STAGE_IA = "Stage IA"
    STAGE_IB = "Stage IB"
    STAGE_IIA = "Stage IIA"
    STAGE_IIB = "Stage IIB"
    STAGE_IIIA = "Stage IIIA"
    STAGE_IIIB = "Stage IIIB"
    STAGE_IIIC = "Stage IIIC"
    STAGE_IV = "Stage IV"


@dataclass
class TNMClassification:
    """TNM 分類"""
    t: str  # T classification
    n: str  # N classification
    m: str  # M classification
    grade: int  # 組織學分級 (1-3)
    er_status: str  # ER: "Positive" / "Negative"
    pr_status: str  # PR: "Positive" / "Negative"
    her2_status: str  # HER2: "Positive" / "Negative"


@dataclass
class AJCCResult:
    """AJCC 分期結果"""
    clinical_stage: AJCCStage
    pathologic_stage: Optional[AJCCStage] = None
    prognostic_group: str = ""
    treatment_recommendation: str = ""
    details: Dict = None


class AJCCStageConverter:
    """
    AJCC 乳癌分期轉換器

    使用方法：
        converter = AJCCStageConverter(edition=9)  # AJCC 9th edition
        result = converter.convert(
            t="T2",
            n="N1",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
    """

    def __init__(self, edition: int = 9):
        """
        初始化轉換器

        參數：
            edition (int): AJCC 版本 (8 or 9)
        """
        if edition not in [8, 9]:
            raise ValueError("只支持 AJCC 8th (2017) 和 9th (2023) 版本")

        self.edition = edition
        self.staging_table = self._load_staging_table()

    def _load_staging_table(self) -> Dict:
        """
        載入 AJCC 分期表
        TODO: 從 data/ajcc_staging_{edition}.json 載入
        """
        return {
            # Stage 0
            "0": {
                "criteria": ["T0 N0 M0"],
                "description": "Non-invasive carcinoma"
            },
            # Stage IA
            "IA": {
                "criteria": [
                    "T1 N0 M0 (Grade 1-2, ER/PR+, HER2-)",
                    "T1mi N0 M0",
                ],
                "description": "Small tumor, no lymph node involvement"
            },
            # 其他分期... (待補充)
        }

    def convert(
        self,
        t: str,
        n: str,
        m: str,
        grade: int,
        er_status: str,
        pr_status: str,
        her2_status: str,
        is_pathologic: bool = False
    ) -> AJCCResult:
        """
        轉換 TNM 分類為 AJCC 分期

        參數：
            t (str): T classification (T0, T1, T1mi, T1a, ..., T4d)
            n (str): N classification (N0, N1, N2, N3, 或帶有細分的版本)
            m (str): M classification (M0, M1)
            grade (int): 組織學分級 (1-3)
            er_status (str): ER 狀態 ("Positive" / "Negative")
            pr_status (str): PR 狀態 ("Positive" / "Negative")
            her2_status (str): HER2 狀態 ("Positive" / "Negative")
            is_pathologic (bool): 是否為病理分期 (default: 臨床分期)

        返回：
            AJCCResult: 包含分期、預後分組和臨床建議

        異常：
            ValueError: 當 TNM 分類不合法
        """
        # TODO: 實現分期轉換邏輯
        raise NotImplementedError(
            "AJCC 分期轉換邏輯待實現\n"
            "請參考 docs/IMPLEMENTATION_GUIDE.md"
        )

    def validate_tnm(
        self,
        t: str,
        n: str,
        m: str
    ) -> Tuple[bool, str]:
        """
        驗證 TNM 分類的有效性

        返回：
            (is_valid, error_message)
        """
        # TODO: 實現驗證邏輯
        return True, ""

    def get_prognostic_group(
        self,
        t: str,
        n: str,
        m: str,
        grade: int,
        er_status: str,
        her2_status: str
    ) -> str:
        """
        根據 TNM 和生物標誌物確定預後分組
        AJCC 9th edition 使用生物標誌物加權的預後分組

        返回：
            預後分組描述 ("Excellent", "Good", "Intermediate", "Poor")

        TODO: 實現預後分組邏輯
        """
        raise NotImplementedError(
            "預後分組邏輯待實現"
        )

    def get_treatment_recommendation(
        self,
        ajcc_stage: str,
        grade: int,
        er_status: str,
        pr_status: str,
        her2_status: str
    ) -> Dict:
        """
        基於分期和生物標誌物提供治療建議

        返回：
            {
                "hormone_therapy": True/False,
                "chemotherapy": True/False,
                "trastuzumab": True/False,
                "radiotherapy": True/False,
                "surgery": True/False,
                "notes": "臨床建議備註"
            }

        TODO: 實現治療建議邏輯
        """
        raise NotImplementedError(
            "治療建議邏輯待實現"
        )

    def compare_editions(
        self,
        t: str,
        n: str,
        m: str,
        grade: int,
        er_status: str,
        her2_status: str
    ) -> Dict:
        """
        比較 AJCC 8th 和 9th 版本的分期差異

        返回：
            {
                "edition_8": Stage,
                "edition_9": Stage,
                "changed": bool,
                "explanation": "版本差異說明"
            }

        TODO: 實現版本比較邏輯
        """
        raise NotImplementedError(
            "版本比較邏輯待實現"
        )


# 使用範例
if __name__ == "__main__":
    # 範例用法
    converter = AJCCStageConverter(edition=9)

    # 測試數據
    test_case = {
        "t": "T2",
        "n": "N1a",
        "m": "M0",
        "grade": 2,
        "er_status": "Positive",
        "pr_status": "Positive",
        "her2_status": "Negative"
    }

    print(f"測試輸入 (AJCC 9th Edition): {test_case}")
    print("轉換中... (待實現)")

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
    TIS = "Tis"  # Carcinoma in situ
    T1 = "T1"  # General T1 (for broad classification)
    T1MI = "T1mi"  # Microinvasion
    T1A = "T1a"  # ≤0.5 cm
    T1B = "T1b"  # >0.5 to ≤1.0 cm
    T1C = "T1c"  # >1.0 to ≤2.0 cm
    T2 = "T2"  # >2.0 to ≤5.0 cm
    T3 = "T3"  # >5.0 cm
    T4 = "T4"  # General T4 (for broad classification)
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
    """AJCC 分期結果 - 支持解剖分期和預後分期"""
    # 解剖分期 (Anatomical Stage) - 基於 TNM 分類
    clinical_stage: AJCCStage
    pathologic_stage: Optional[AJCCStage] = None

    # 預後分期 (Prognostic Stage Groups) - AJCC 9th 新增，基於 TNM + 生物標誌物
    prognostic_group: str = ""

    # 詳細信息
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
        self.reference_lookup = None
        if edition == 9:
            self.reference_lookup = self._load_reference_lookup()

    def _load_staging_table(self) -> Dict:
        """
        載入 AJCC 分期表
        從 data/ajcc_staging_{edition}.json 載入
        """
        try:
            data_dir = Path(__file__).parent / "data"
            staging_file = data_dir / f"ajcc_staging_{self.edition}.json"

            if not staging_file.exists():
                raise FileNotFoundError(f"Staging file not found: {staging_file}")

            with open(staging_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("stages", {})
        except Exception as e:
            raise RuntimeError(f"Failed to load staging table: {e}")

    def _load_reference_lookup(self) -> Optional[Dict]:
        """
        載入 AJCC 9th Edition 官方參考查詢表
        從 data/ajcc_staging_9_reference_lookup.json 載入
        包含 Taiwan Veterans General Hospital 官方分期對照表
        """
        try:
            data_dir = Path(__file__).parent / "data"
            lookup_file = data_dir / "ajcc_staging_9_reference_lookup.json"

            if not lookup_file.exists():
                return None

            with open(lookup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("entries", [])
        except Exception as e:
            # Silently fail - use rule-based fallback
            return None

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
            AJCCResult: 包含解剖分期和預後分組

        異常：
            ValueError: 當 TNM 分類不合法
        """
        # Validate input
        is_valid, error = self.validate_tnm(t, n, m)
        if not is_valid:
            raise ValueError(f"Invalid TNM classification: {error}")

        # 1. 決定解剖分期 (Anatomical Stage) - 基於 TNM
        anatomical_stage = self._determine_stage(
            t, n, m, grade, er_status, pr_status, her2_status
        )

        # 2. 決定預後分組 (Prognostic Groups) - NCCN 基於 TNM + 生物標誌物
        prognostic_group = self.get_prognostic_group(
            t, n, m, grade, er_status, her2_status
        )

        # Create result
        result = AJCCResult(
            clinical_stage=anatomical_stage,
            pathologic_stage=anatomical_stage if is_pathologic else None,
            prognostic_group=prognostic_group,
            details={
                "tnm": f"{t} {n} {m}",
                "grade": grade,
                "biomarkers": {
                    "er": er_status,
                    "pr": pr_status,
                    "her2": her2_status
                },
                "anatomical_stage": anatomical_stage.value,
                "prognostic_groups_nccn": prognostic_group
            }
        )

        return result

    def _determine_stage(
        self,
        t: str,
        n: str,
        m: str,
        grade: int,
        er_status: str,
        pr_status: str,
        her2_status: str
    ) -> AJCCStage:
        """
        根據 TNM 和生物標誌物確定分期
        優先使用官方參考查詢表，其次使用規則
        """
        # Try lookup table first (AJCC 9th Edition only)
        if self.reference_lookup:
            stage = self._lookup_stage_from_reference(t, n, m, grade, er_status, pr_status, her2_status)
            if stage:
                return stage

        # M1 always means Stage IV
        if m == "M1":
            return AJCCStage.STAGE_IV

        # Normalize T and N values to base forms for comparison
        t_base = self._normalize_t(t)
        n_base = self._normalize_n(n)

        # Stage 0: Tis (Carcinoma in situ)
        if (t == "Tis" or t_base == "Tis") and n == "N0" and m == "M0":
            return AJCCStage.STAGE_0

        # Stage IA
        if self._match_stage_ia(t, n, m, grade, er_status, her2_status):
            return AJCCStage.STAGE_IA

        # Stage IB
        if self._match_stage_ib(t, n, m):
            return AJCCStage.STAGE_IB

        # Stage IIA
        if self._match_stage_iia(t, n, m, grade):
            return AJCCStage.STAGE_IIA

        # Stage IIB
        if self._match_stage_iib(t, n, m, grade):
            return AJCCStage.STAGE_IIB

        # Stage IIIA
        if self._match_stage_iiia(t, n, m):
            return AJCCStage.STAGE_IIIA

        # Stage IIIB
        if self._match_stage_iiib(t, n, m):
            return AJCCStage.STAGE_IIIB

        # Stage IIIC
        if self._match_stage_iiic(t, n, m):
            return AJCCStage.STAGE_IIIC

        # Default to IIIC for unknown cases (should not happen with proper validation)
        return AJCCStage.STAGE_IIIC

    def _lookup_stage_from_reference(
        self,
        t: str,
        n: str,
        m: str,
        grade: int,
        er_status: str,
        pr_status: str,
        her2_status: str
    ) -> Optional[AJCCStage]:
        """
        從官方參考查詢表查找分期
        匹配 T + N + M + Grade + HER2 + ER + PR 的精確組合
        """
        if not self.reference_lookup:
            return None

        # Normalize biomarker values
        her2_normalized = "Pos" if her2_status == "Positive" else "Neg"
        er_normalized = "Pos" if er_status == "Positive" else "Neg"
        pr_normalized = "Pos" if pr_status == "Positive" else "Neg"

        # Look for exact match in reference data
        for entry in self.reference_lookup:
            if (entry['T'] == t and
                entry['N'] == n and
                entry['M'] == m and
                entry['Grade'] == grade and
                entry['HER2'] == her2_normalized and
                entry['ER'] == er_normalized and
                entry['PR'] == pr_normalized):
                # Convert stage string to enum
                stage_str = entry['Stage']
                stage_map = {
                    '0': AJCCStage.STAGE_0,
                    'IA': AJCCStage.STAGE_IA,
                    'IB': AJCCStage.STAGE_IB,
                    'IIA': AJCCStage.STAGE_IIA,
                    'IIB': AJCCStage.STAGE_IIB,
                    'IIIA': AJCCStage.STAGE_IIIA,
                    'IIIB': AJCCStage.STAGE_IIIB,
                    'IIIC': AJCCStage.STAGE_IIIC,
                    'IV': AJCCStage.STAGE_IV,
                }
                return stage_map.get(stage_str)

        return None

    def _normalize_t(self, t: str) -> str:
        """Extract base T value (e.g., T1a -> T1), handling Tis and general forms"""
        if t == "Tis":
            return t
        if t.startswith("T"):
            # Extract just the main T category
            if len(t) > 1 and t[1].isdigit():
                return t[:2]  # T1a -> T1, T4b -> T4
        return t

    def _normalize_n(self, n: str) -> str:
        """Extract base N value (e.g., N1a -> N1), handling special forms"""
        if n.startswith("N"):
            # Handle special cases like N0(i+), N0(mol+)
            if "(" in n:
                return n[:2]  # N0(i+) -> N0
            if len(n) > 1 and n[1].isdigit():
                return n[:2]  # N1a -> N1
        return n

    def _match_stage_ia(self, t: str, n: str, m: str, grade: int, er_status: str, her2_status: str) -> bool:
        """Stage IA criteria"""
        if m != "M0":
            return False

        t_normalized = self._normalize_t(t)

        # T1 N0 with favorable biology
        if t_normalized == "T1" and n == "N0":
            # Check for favorable biomarkers (Grade 1-2 and ER/PR+)
            if grade <= 2 and er_status == "Positive":
                return True

        # T0 N1mi
        if t == "T0" and n == "N1mi":
            return True

        return False

    def _match_stage_ib(self, t: str, n: str, m: str) -> bool:
        """Stage IB criteria"""
        if m != "M0":
            return False

        t_normalized = self._normalize_t(t)

        # T0 N1a
        if t == "T0" and n == "N1a":
            return True

        # T1 N1mi
        if t_normalized == "T1" and n == "N1mi":
            return True

        return False

    def _match_stage_iia(self, t: str, n: str, m: str, grade: int) -> bool:
        """Stage IIA criteria"""
        if m != "M0":
            return False

        t_normalized = self._normalize_t(t)

        # T1 N1a
        if t_normalized == "T1" and n == "N1a":
            return True

        # T2 N0
        if t_normalized == "T2" and n == "N0":
            return True

        return False

    def _match_stage_iib(self, t: str, n: str, m: str, grade: int) -> bool:
        """Stage IIB criteria"""
        if m != "M0":
            return False

        t_normalized = self._normalize_t(t)

        # T2 N1a
        if t_normalized == "T2" and n == "N1a":
            return True

        # T3 N0
        if t_normalized == "T3" and n == "N0":
            return True

        return False

    def _match_stage_iiia(self, t: str, n: str, m: str) -> bool:
        """Stage IIIA criteria"""
        if m != "M0":
            return False

        t_base = self._normalize_t(t)
        n_base = self._normalize_n(n)

        # T1-3 N2a
        if t_base in ["T1", "T2", "T3"] and n == "N2a":
            return True

        # T3 N1a
        if t_base == "T3" and n == "N1a":
            return True

        # T4a N0-N2a
        if t == "T4a" or t == "T4":
            if n in ["N0", "N1a", "N2a"]:
                return True

        return False

    def _match_stage_iiib(self, t: str, n: str, m: str) -> bool:
        """Stage IIIB criteria"""
        if m != "M0":
            return False

        # Any T with N2b (internal mammary involved)
        if n == "N2b":
            return True

        # T4b (skin involvement) with N0-2b
        if t == "T4b" or (t == "T4" and "b" in t.lower()):
            return True

        return False

    def _match_stage_iiic(self, t: str, n: str, m: str) -> bool:
        """Stage IIIC criteria"""
        if m != "M0":
            return False

        # Any T with N3
        if self._normalize_n(n) == "N3":
            return True

        return False

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
        valid_t_values = [e.value for e in TumorSize]
        valid_n_values = [e.value for e in LymphNodeStatus]
        valid_m_values = [e.value for e in MetastasisStatus]

        if t not in valid_t_values:
            return False, f"Invalid T classification: {t}. Valid values: {valid_t_values}"
        if n not in valid_n_values:
            return False, f"Invalid N classification: {n}. Valid values: {valid_n_values}"
        if m not in valid_m_values:
            return False, f"Invalid M classification: {m}. Valid values: {valid_m_values}"

        # Special rule: M1 disease is always Stage IV
        if m == "M1":
            return True, ""

        # Invalid combinations (shouldn't occur in practice)
        if t == "TX" and n == "NX" and m == "MX":
            return False, "Cannot classify with all unknown (TX NX MX)"

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
        """
        # M1 disease is always poor prognosis
        if m == "M1":
            return "PG4 - Poor prognosis (Stage IV)"

        t_base = self._normalize_t(t)
        n_base = self._normalize_n(n)

        # Convert classifications to numeric for easier comparison
        t_num = self._t_to_number(t_base)
        n_num = self._n_to_number(n)

        # PG1: Excellent prognosis
        # Small tumor, no lymph node involvement, favorable biomarkers
        if (t == "T1" or t_base == "T1") and n == "N0" and \
           grade <= 2 and er_status == "Positive" and her2_status == "Negative":
            return "PG1 - Excellent prognosis"

        # PG2: Good prognosis
        # T1-2 N0-1 with favorable biomarkers
        if t_num <= 2 and n_num <= 1 and er_status == "Positive" and her2_status == "Negative":
            if grade <= 2 or n == "N0":
                return "PG2 - Good prognosis"

        # PG3: Intermediate prognosis
        # T2-3, Grade 3, or HER2+ status
        if t_num <= 3 and n_num <= 2:
            if grade == 3 or her2_status == "Positive":
                return "PG3 - Intermediate prognosis"
            if er_status == "Negative":
                return "PG3 - Intermediate prognosis"

        # PG4: Poor prognosis
        # Large tumor, extensive nodal involvement, unfavorable biomarkers
        if t_num >= 4 or n_num >= 3 or m == "M1":
            return "PG4 - Poor prognosis"

        if er_status == "Negative" and her2_status == "Negative":
            return "PG3-4 - Intermediate to poor prognosis (Triple negative)"

        # Default intermediate
        return "PG3 - Intermediate prognosis"

    def _t_to_number(self, t_base: str) -> int:
        """Convert T classification to numeric for comparison"""
        mapping = {
            "T0": 0, "Tis": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4, "TX": 0
        }
        return mapping.get(t_base, 0)

    def _n_to_number(self, n: str) -> int:
        """Convert N classification to numeric for comparison"""
        n_base = self._normalize_n(n)
        mapping = {
            "N0": 0, "N1": 1, "N2": 2, "N3": 3, "NX": 0
        }
        return mapping.get(n_base, 0)

    def get_treatment_recommendation(
        self,
        ajcc_stage: AJCCStage,
        grade: int,
        er_status: str,
        pr_status: str,
        her2_status: str
    ) -> Dict:
        """
        基於分期和生物標誌物提供治療建議

        返回：
            {
                "surgery": bool,
                "radiation": str,
                "chemotherapy": bool,
                "hormone_therapy": bool,
                "trastuzumab": bool,
                "additional_agents": [str],
                "summary": str
            }
        """
        rec = {
            "surgery": True,
            "radiation": "Not standard",
            "chemotherapy": False,
            "hormone_therapy": er_status == "Positive",
            "trastuzumab": her2_status == "Positive",
            "additional_agents": [],
            "summary": ""
        }

        stage_name = ajcc_stage.value

        # Stage 0
        if ajcc_stage == AJCCStage.STAGE_0:
            rec["surgery"] = True
            rec["radiation"] = "After lumpectomy"
            rec["chemotherapy"] = False
            rec["hormone_therapy"] = False
            rec["summary"] = "Stage 0: Surgery + radiation. No systemic therapy typically needed."

        # Stage IA
        elif ajcc_stage == AJCCStage.STAGE_IA:
            rec["radiation"] = "After lumpectomy"
            rec["chemotherapy"] = grade == 3
            rec["summary"] = "Stage IA: Surgery ± radiation. Hormone therapy if ER+. Chemotherapy if Grade 3."

        # Stage IB
        elif ajcc_stage == AJCCStage.STAGE_IB:
            rec["radiation"] = "After lumpectomy"
            rec["chemotherapy"] = True
            rec["summary"] = "Stage IB: Surgery + radiation. Consider chemotherapy. Hormone therapy if ER+."

        # Stage IIA
        elif ajcc_stage == AJCCStage.STAGE_IIA:
            rec["radiation"] = "Standard"
            rec["chemotherapy"] = grade >= 2
            rec["summary"] = "Stage IIA: Surgery + radiation. Chemotherapy if Grade 2-3 or high-risk features."

        # Stage IIB
        elif ajcc_stage == AJCCStage.STAGE_IIB:
            rec["radiation"] = "Standard"
            rec["chemotherapy"] = True
            rec["summary"] = "Stage IIB: Surgery + radiation. Chemotherapy strongly recommended."

        # Stage IIIA
        elif ajcc_stage == AJCCStage.STAGE_IIIA:
            rec["radiation"] = "Standard"
            rec["chemotherapy"] = True
            rec["additional_agents"].append("Consider neoadjuvant chemotherapy")
            rec["summary"] = "Stage IIIA: Multimodal therapy with surgery, radiation, chemotherapy. Neoadjuvant approach."

        # Stage IIIB
        elif ajcc_stage == AJCCStage.STAGE_IIIB:
            rec["radiation"] = "Standard"
            rec["chemotherapy"] = True
            rec["additional_agents"].append("Strongly consider neoadjuvant chemotherapy")
            rec["summary"] = "Stage IIIB: Aggressive multimodal therapy. Neoadjuvant chemotherapy recommended."

        # Stage IIIC
        elif ajcc_stage == AJCCStage.STAGE_IIIC:
            rec["radiation"] = "Standard"
            rec["chemotherapy"] = True
            rec["additional_agents"].append("Neoadjuvant chemotherapy strongly recommended")
            rec["summary"] = "Stage IIIC: Intensive multimodal therapy with neoadjuvant approach."

        # Stage IV
        elif ajcc_stage == AJCCStage.STAGE_IV:
            rec["surgery"] = False  # Palliative surgery only
            rec["chemotherapy"] = True
            rec["radiation"] = "Palliative"
            rec["summary"] = "Stage IV: Metastatic disease. Systemic therapy is primary. Consider clinical trials."

        # HER2-specific recommendations
        if her2_status == "Positive":
            if rec["chemotherapy"]:
                rec["additional_agents"].append("Trastuzumab (Herceptin)")
                rec["additional_agents"].append("Consider pertuzumab (Perjeta) for Stage III-IV")
                rec["additional_agents"].append("Consider T-DM1 alternatives")
            else:
                rec["trastuzumab"] = True

        # ER+ specific recommendations
        if er_status == "Positive":
            duration = "10 years" if ajcc_stage in [AJCCStage.STAGE_IA, AJCCStage.STAGE_IIA] else "5-10 years"
            rec["additional_agents"].append(f"Hormone therapy (AI or tamoxifen) for {duration}")

        # Triple negative specific
        if er_status == "Negative" and pr_status == "Negative" and her2_status == "Negative":
            if ajcc_stage not in [AJCCStage.STAGE_0, AJCCStage.STAGE_IA]:
                rec["additional_agents"].append("Consider immunotherapy (PD-L1 checkpoint inhibitors)")

        return rec

    def compare_editions(
        self,
        t: str,
        n: str,
        m: str,
        grade: int,
        er_status: str,
        pr_status: str,
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
        """
        # Get result from current edition
        try:
            result_9 = self.convert(
                t=t, n=n, m=m, grade=grade,
                er_status=er_status, pr_status=pr_status, her2_status=her2_status
            )
        except:
            result_9 = None

        # Temporarily switch to edition 8 if we're on 9
        original_edition = self.edition
        try:
            if self.edition == 9:
                self.edition = 8
                self.staging_table = self._load_staging_table()
                result_8 = self.convert(
                    t=t, n=n, m=m, grade=grade,
                    er_status=er_status, pr_status=pr_status, her2_status=her2_status
                )
            else:
                self.edition = 9
                self.staging_table = self._load_staging_table()
                result_8 = self.convert(
                    t=t, n=n, m=m, grade=grade,
                    er_status=er_status, pr_status=pr_status, her2_status=her2_status
                )
        finally:
            # Restore original edition
            self.edition = original_edition
            self.staging_table = self._load_staging_table()

        # Compare
        stage_8 = result_8.clinical_stage.value if result_8 else "Unknown"
        stage_9 = result_9.clinical_stage.value if result_9 else "Unknown"
        changed = stage_8 != stage_9

        explanation = self._explain_edition_difference(
            stage_8, stage_9, t, n, m, grade, er_status, her2_status
        )

        return {
            "edition_8": stage_8,
            "edition_9": stage_9,
            "changed": changed,
            "explanation": explanation,
            "key_differences": [
                "9th edition incorporates biomarker-weighted prognostic groups",
                "9th edition emphasizes ER/PR/HER2 status in staging",
                "9th edition includes Ki67 considerations",
                "9th edition refines lymph node micrometastasis definitions"
            ]
        }

    def _explain_edition_difference(
        self,
        stage_8: str,
        stage_9: str,
        t: str,
        n: str,
        m: str,
        grade: int,
        er_status: str,
        her2_status: str
    ) -> str:
        """Explain why staging differs between editions"""
        if stage_8 == stage_9:
            return "No change between AJCC 8th and 9th editions for this case."

        # Most common differences
        if "ER" in er_status or "HER2" in her2_status:
            return f"9th edition incorporates biomarker status (ER: {er_status}, HER2: {her2_status}) " \
                   f"more explicitly in staging. Stage 8th: {stage_8} → Stage 9th: {stage_9}"

        if grade == 3:
            return f"High-grade (Grade 3) tumors may be staged differently in 9th edition. " \
                   f"Stage 8th: {stage_8} → Stage 9th: {stage_9}"

        return f"9th edition applies refined TNM criteria. Stage 8th: {stage_8} → Stage 9th: {stage_9}"


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

    converter = AJCCStageConverter(edition=9)
    result = converter.convert(**test_case)
    print(f"測試輸入 (AJCC 9th Edition): {test_case}")
    print(f"解剖分期: {result.clinical_stage.value}")
    print(f"預後分組: {result.prognostic_group}")

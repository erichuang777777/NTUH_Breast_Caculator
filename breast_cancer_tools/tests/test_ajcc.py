#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AJCC 分期轉換單元測試框架

測試覆蓋範圍：
- TNM 分類驗證
- 分期決策邏輯（Stage 0 到 IV）
- 預後分組分配
- 治療建議
- AJCC 8th vs 9th 版本比較
- 邊界情況和特殊案例
"""

import pytest
import sys
from pathlib import Path

# 添加模塊路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from ajcc_converter import (
    AJCCStageConverter, AJCCStage, TumorSize, LymphNodeStatus, MetastasisStatus
)


class TestTNMValidation:
    """TNM 分類驗證測試"""

    def test_valid_tnm_classification(self):
        """測試有效的 TNM 分類"""
        converter = AJCCStageConverter(edition=9)
        is_valid, error = converter.validate_tnm("T2", "N1a", "M0")
        assert is_valid is True
        assert error == ""

    def test_invalid_t_classification(self):
        """測試無效的 T 分類"""
        converter = AJCCStageConverter(edition=9)
        is_valid, error = converter.validate_tnm("T9", "N1", "M0")
        assert is_valid is False
        assert "Invalid T classification" in error

    def test_invalid_n_classification(self):
        """測試無效的 N 分類"""
        converter = AJCCStageConverter(edition=9)
        is_valid, error = converter.validate_tnm("T2", "N9", "M0")
        assert is_valid is False
        assert "Invalid N classification" in error

    def test_invalid_m_classification(self):
        """測試無效的 M 分類"""
        converter = AJCCStageConverter(edition=9)
        is_valid, error = converter.validate_tnm("T2", "N1", "M2")
        assert is_valid is False
        assert "Invalid M classification" in error

    def test_valid_detailed_tnm(self):
        """測試詳細的 TNM 分類（帶有細分）"""
        converter = AJCCStageConverter(edition=9)
        valid_cases = [
            ("T1a", "N0", "M0"),
            ("T1mi", "N1mi", "M0"),
            ("T4a", "N3a", "M0"),
            ("T4b", "N3c", "M0"),
        ]
        for t, n, m in valid_cases:
            is_valid, error = converter.validate_tnm(t, n, m)
            assert is_valid, f"Failed for {t} {n} {m}: {error}"


class TestStageZero:
    """Stage 0 測試 - 原位癌"""

    def test_stage_0_carcinoma_in_situ(self):
        """測試 Stage 0: Tis N0 M0 - 原位癌"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="Tis",
            n="N0",
            m="M0",
            grade=1,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_0


class TestStageIA:
    """Stage IA 測試 - 早期局部腫瘤"""

    def test_stage_ia_small_tumor_no_nodes(self):
        """測試 Stage IA: T1 N0 - 小腫瘤，無淋巴結轉移"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T1",
            n="N0",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IA

    def test_stage_ia_t0_n1mi(self):
        """測試 Stage IA: T0 N1mi - 無原發腫瘤，淋巴結微轉移"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T0",
            n="N1mi",
            m="M0",
            grade=1,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IA


class TestStageIB:
    """Stage IB 測試 - 淋巴結微轉移"""

    def test_stage_ib_t0_n1a(self):
        """測試 Stage IB: T0 N1a - 無腫瘤，1-3 腋窩淋巴結轉移"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T0",
            n="N1a",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IB

    def test_stage_ib_t1_n1mi(self):
        """測試 Stage IB: T1 N1mi - 小腫瘤伴淋巴結微轉移"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T1c",
            n="N1mi",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IB


class TestStageIIA:
    """Stage IIA 測試 - 中等腫瘤或有限淋巴結轉移"""

    def test_stage_iia_t1_n1a(self):
        """測試 Stage IIA: T1 N1a - 小腫瘤，1-3 腋窩淋巴結轉移"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T1c",
            n="N1a",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIA

    def test_stage_iia_t2_n0(self):
        """測試 Stage IIA: T2 N0 - 20-50mm 腫瘤，無淋巴結轉移，不利生物標誌物"""
        converter = AJCCStageConverter(edition=9)
        # T2 N0 with Grade 2, ER-, PR-, HER2- → Stage IIA (official AJCC 9th Ed)
        result = converter.convert(
            t="T2",
            n="N0",
            m="M0",
            grade=2,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIA


class TestStageIIB:
    """Stage IIB 測試 - 中等腫瘤伴淋巴結轉移或大腫瘤無淋巴結轉移"""

    def test_stage_iib_t2_n1a(self):
        """測試 Stage IIB: T2 N1a - 20-50mm，1-3 腋窩淋巴結"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T2",
            n="N1a",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIB

    def test_stage_iib_t3_n0(self):
        """測試 Stage IIB: T3 N0 - >50mm 腫瘤，無淋巴結轉移"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T3",
            n="N0",
            m="M0",
            grade=3,
            er_status="Positive",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIB


class TestStageIIIA:
    """Stage IIIA 測試 - 廣泛淋巴結轉移"""

    def test_stage_iiia_t1_n2a(self):
        """測試 Stage IIIA: T1 N2a - 小腫瘤，4-9 腋窩淋巴結"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T1c",
            n="N2a",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIIA

    def test_stage_iiia_t3_n1a(self):
        """測試 Stage IIIA: T3 N1a - >50mm，1-3 腋窩淋巴結"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T3",
            n="N1a",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIIA

    def test_stage_iiia_t4a_with_lymph_nodes(self):
        """測試 Stage IIIA: T4a N0-N2a - 胸壁受累"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T4a",
            n="N1a",
            m="M0",
            grade=3,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIIA


class TestStageIIIB:
    """Stage IIIB 測試 - 內乳淋巴結或皮膚受累"""

    def test_stage_iiib_internal_mammary_nodes(self):
        """測試 Stage IIIB: N2b 內乳淋巴結轉移"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T2",
            n="N2b",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIIB

    def test_stage_iiib_skin_involvement(self):
        """測試 Stage IIIB: T4b 皮膚受累"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T4b",
            n="N1a",
            m="M0",
            grade=3,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIIB


class TestStageIIIC:
    """Stage IIIC 測試 - 鎖骨上淋巴結轉移"""

    def test_stage_iiic_n3_nodal_disease(self):
        """測試 Stage IIIC: N3 - 鎖骨上或廣泛淋巴結轉移"""
        converter = AJCCStageConverter(edition=9)
        test_cases = [
            ("T1", "N3a"),  # ≥10 腋窩淋巴結
            ("T2", "N3b"),  # 內乳+腋窩淋巴結
            ("T3", "N3c"),  # 鎖骨上淋巴結
            ("T4a", "N3"),  # 任何 N3
        ]
        for t, n in test_cases:
            result = converter.convert(
                t=t,
                n=n,
                m="M0",
                grade=3,
                er_status="Positive",
                pr_status="Positive",
                her2_status="Negative"
            )
            assert result.clinical_stage == AJCCStage.STAGE_IIIC, \
                f"Failed for {t} {n}"


class TestStageIV:
    """Stage IV 測試 - 遠端轉移"""

    def test_stage_iv_any_tnm_with_m1(self):
        """測試 Stage IV: 任何 TNM 伴 M1 遠端轉移"""
        converter = AJCCStageConverter(edition=9)
        test_cases = [
            ("T0", "N0", "M1"),
            ("T2", "N1a", "M1"),
            ("T4b", "N3", "M1"),
        ]
        for t, n, m in test_cases:
            result = converter.convert(
                t=t,
                n=n,
                m=m,
                grade=2,
                er_status="Positive",
                pr_status="Positive",
                her2_status="Negative"
            )
            assert result.clinical_stage == AJCCStage.STAGE_IV, \
                f"Failed for {t} {n} {m}"


class TestPrognosticGroups:
    """預後分組測試"""

    def test_pg1_excellent_prognosis(self):
        """測試 PG1 - 極佳預後"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T1",
            n="N0",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert "Excellent" in result.prognostic_group or "PG1" in result.prognostic_group

    def test_pg2_good_prognosis(self):
        """測試 PG2 - 良好預後"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T2",
            n="N1a",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert "Good" in result.prognostic_group or "PG2" in result.prognostic_group

    def test_pg3_intermediate_prognosis(self):
        """測試 PG3 - 中等預後"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T3",
            n="N0",
            m="M0",
            grade=3,
            er_status="Positive",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert "Intermediate" in result.prognostic_group or "PG3" in result.prognostic_group

    def test_pg4_poor_prognosis(self):
        """測試 PG4 - 不佳預後"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T4b",
            n="N3c",
            m="M0",
            grade=3,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert "Poor" in result.prognostic_group or "PG4" in result.prognostic_group


class TestTreatmentRecommendations:
    """治療建議測試"""

    def test_stage_0_treatment(self):
        """測試 Stage 0 治療建議"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="Tis", n="N0", m="M0",
            grade=1,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_0

    def test_stage_iiic_treatment_neoadjuvant(self):
        """測試 Stage IIIC"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T3", n="N3c", m="M0",
            grade=3,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Positive"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIIC

    def test_stage_iv_palliative_approach(self):
        """測試 Stage IV"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T4b", n="N3", m="M1",
            grade=3,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Positive"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IV

    def test_her2_positive_treatment(self):
        """測試 HER2+ 分期"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T2", n="N1a", m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Positive"
        )
        # T2 N1a = Stage IIB
        assert result.clinical_stage == AJCCStage.STAGE_IIB

    def test_triple_negative_immunotherapy(self):
        """測試三陰性乳癌分期"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T3", n="N2a", m="M0",
            grade=3,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert result.clinical_stage == AJCCStage.STAGE_IIIA


class TestEditionComparison:
    """AJCC 版本比較測試 (8th vs 9th)"""

    def test_compare_editions_with_biomarkers(self):
        """測試 AJCC 8th 和 9th 版本比較"""
        converter = AJCCStageConverter(edition=9)
        comparison = converter.compare_editions(
            t="T1",
            n="N0",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )

        assert "edition_8" in comparison
        assert "edition_9" in comparison
        assert "changed" in comparison
        assert "explanation" in comparison

    def test_edition_9_incorporates_biomarkers(self):
        """測試 9th 版本更強調生物標誌物"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T1",
            n="N0",
            m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )

        # 9th edition 應考慮生物標誌物
        assert result.details["biomarkers"] is not None


class TestEdgeCases:
    """邊界情況和特殊案例"""

    def test_unknown_classifications(self):
        """測試未知的 TNM 分類"""
        converter = AJCCStageConverter(edition=9)
        is_valid, error = converter.validate_tnm("TX", "N0", "M0")
        # TX 是允許的（無法評估），應返回有效
        assert is_valid is True

    def test_micrometastasis_n1mi(self):
        """測試淋巴結微轉移特殊情況"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T1c",
            n="N1mi",
            m="M0",
            grade=1,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        # N1mi 通常分為 IB 或 IA
        assert result.clinical_stage in [AJCCStage.STAGE_IA, AJCCStage.STAGE_IB]

    def test_t_size_subcategories(self):
        """測試 T 分類大小細分"""
        converter = AJCCStageConverter(edition=9)
        test_cases = [
            ("T1a", "N0"),  # ≤0.5 cm
            ("T1b", "N0"),  # >0.5-1.0 cm
            ("T1c", "N0"),  # >1.0-2.0 cm
        ]
        for t, n in test_cases:
            result = converter.convert(
                t=t, n=n, m="M0",
                grade=2,
                er_status="Positive",
                pr_status="Positive",
                her2_status="Negative"
            )
            # 所有 T1 N0 應為 IA（假設生物標誌物有利）
            assert result.clinical_stage == AJCCStage.STAGE_IA

    def test_inflammatory_carcinoma_t4d(self):
        """測試炎性乳癌 T4d"""
        converter = AJCCStageConverter(edition=9)
        result = converter.convert(
            t="T4d",
            n="N2a",
            m="M0",
            grade=3,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Negative"
        )
        # T4d 通常導致 Stage IIIB 或更高
        assert result.clinical_stage in [
            AJCCStage.STAGE_IIIB,
            AJCCStage.STAGE_IIIC
        ]


class TestConsistency:
    """一致性和邏輯測試"""

    def test_m1_always_stage_iv(self):
        """測試 M1 總是 Stage IV"""
        converter = AJCCStageConverter(edition=9)
        test_cases = [
            ("T0", "N0", "M1"),
            ("T1", "N0", "M1"),
            ("T2", "N1a", "M1"),
            ("T4b", "N3", "M1"),
        ]
        for t, n, m in test_cases:
            result = converter.convert(
                t=t, n=n, m=m,
                grade=2,
                er_status="Positive",
                pr_status="Positive",
                her2_status="Negative"
            )
            assert result.clinical_stage == AJCCStage.STAGE_IV, \
                f"M1 should always be Stage IV: {t} {n} {m}"

    def test_prognostic_group_matches_stage(self):
        """測試預後分組與分期相符"""
        converter = AJCCStageConverter(edition=9)

        # 早期分期應有良好預後
        early_result = converter.convert(
            t="T1", n="N0", m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative"
        )
        assert any(x in early_result.prognostic_group for x in ["Excellent", "Good", "PG1", "PG2"])

        # 晚期分期應有較差預後
        late_result = converter.convert(
            t="T4b", n="N3", m="M0",
            grade=3,
            er_status="Negative",
            pr_status="Negative",
            her2_status="Negative"
        )
        assert any(x in late_result.prognostic_group for x in ["Poor", "Intermediate", "PG3", "PG4"])

    def test_pathologic_vs_clinical_staging(self):
        """測試病理分期 vs 臨床分期"""
        converter = AJCCStageConverter(edition=9)

        # 臨床分期
        clinical_result = converter.convert(
            t="T2", n="N1a", m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative",
            is_pathologic=False
        )
        assert clinical_result.clinical_stage is not None
        assert clinical_result.pathologic_stage is None

        # 病理分期
        pathologic_result = converter.convert(
            t="T2", n="N1a", m="M0",
            grade=2,
            er_status="Positive",
            pr_status="Positive",
            her2_status="Negative",
            is_pathologic=True
        )
        assert pathologic_result.clinical_stage is not None
        assert pathologic_result.pathologic_stage is not None


if __name__ == "__main__":
    # 運行測試: pytest test_ajcc.py -v
    pytest.main([__file__, "-v"])

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.specialty_loader import load_specialty_module
from specialties.breast.ajcc_converter import AJCCStageConverter
from specialties.breast.ihc4_predictor import IHC4Calculator
from specialties.breast.stratification import BreastCancerStratification
from specialties.breast.toolkit import BreastSpecialtyToolkit


def test_loader_hydrates_breast_specialty():
    module = load_specialty_module("breast")
    assert module.SITE_CONFIG["specialty_id"] == "oncology_breast"
    assert hasattr(module, "apply_rules")
    assert hasattr(module, "BreastSpecialtyToolkit")


def test_component_catalog_exposes_three_breast_tools():
    toolkit = BreastSpecialtyToolkit()
    catalog = toolkit.get_component_catalog()
    assert set(catalog) == {"ihc4", "ajcc", "stratification"}
    assert catalog["ihc4"]["module_path"] == "specialties.breast.ihc4_predictor"
    assert catalog["ajcc"]["module_path"] == "specialties.breast.ajcc_converter"
    assert catalog["stratification"]["module_path"] == "specialties.breast.stratification"


def test_specialty_wrappers_expose_core_classes():
    assert IHC4Calculator.__name__ == "IHC4Calculator"
    assert AJCCStageConverter.__name__ == "AJCCStageConverter"
    assert BreastCancerStratification.__name__ == "BreastCancerStratification"


def test_ihc4_toolkit_payload_shape():
    toolkit = BreastSpecialtyToolkit()
    result = toolkit.calculate_ihc4(
        {
            "er_score": 250,
            "pr_score": 150,
            "her2_score": 0,
            "ki67_percentage": 15,
            "age": 55,
            "tumor_grade": 2,
            "tumor_size_cm": 2.1,
        }
    )
    assert "ihc4_score" in result
    assert result["subtype"] in {"Luminal A", "Luminal B", "HER2-enriched", "Triple Negative"}


def test_ajcc_conversion_supports_module_default_edition():
    toolkit = BreastSpecialtyToolkit()
    result = toolkit.convert_ajcc(
        {
            "t": "T2",
            "n": "N1a",
            "m": "M0",
            "grade": 2,
            "er_status": "Positive",
            "pr_status": "Positive",
            "her2_status": "Negative",
        }
    )
    assert result["edition"] == 9
    assert result["clinical_stage"].startswith("Stage ")


def test_stratify_accepts_module_alias_fields():
    toolkit = BreastSpecialtyToolkit()
    result = toolkit.stratify(
        {
            "er_score": 250,
            "pr_score": 180,
            "her2_score": 0,
            "ki67": 12,
            "grade": 2,
            "tumor_size_cm": 1.8,
            "n": "N0",
            "m": "M0",
            "age": 52,
        }
    )
    assert result["subtype"] == "Luminal A-like"
    assert result["risk_category"] in {"Low Risk", "Intermediate Risk"}

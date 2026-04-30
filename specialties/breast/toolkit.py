from __future__ import annotations

from typing import Any

from specialties.breast.ajcc_converter import AJCCStageConverter
from specialties.breast.config import SITE_CONFIG
from specialties.breast.ihc4_predictor import IHC4Calculator
from specialties.breast.review_support import get_component_catalog
from specialties.breast.stratification import BiomarkerPanel, BreastCancerStratification


def _value(payload: dict[str, Any], *keys: str, required: bool = True) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    if required:
        raise ValueError(f"Missing required field: {keys[0]}")
    return None


def _as_int(payload: dict[str, Any], *keys: str, required: bool = True) -> int | None:
    value = _value(payload, *keys, required=required)
    if value is None:
        return None
    return int(value)


def _as_float(payload: dict[str, Any], *keys: str, required: bool = True) -> float | None:
    value = _value(payload, *keys, required=required)
    if value is None:
        return None
    return float(value)


def _as_bool(payload: dict[str, Any], *keys: str, required: bool = False) -> bool:
    value = _value(payload, *keys, required=required)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}


def _normalize_status(value: Any) -> str:
    token = str(value).strip().lower()
    positive = {"positive", "pos", "+", "1", "true", "yes"}
    negative = {"negative", "neg", "-", "0", "false", "no"}
    if token in positive:
        return "Positive"
    if token in negative:
        return "Negative"
    raise ValueError(f"Unsupported receptor status: {value}")


class BreastSpecialtyToolkit:
    """Disease-specific entry points for breast decision-support tools."""

    def __init__(self, ajcc_edition: int | None = None):
        self.default_ajcc_edition = ajcc_edition or SITE_CONFIG["default_ajcc_edition"]
        self.ihc4_calculator = IHC4Calculator()
        self.stratifier = BreastCancerStratification()

    def get_component_catalog(self) -> dict[str, Any]:
        return get_component_catalog()

    def calculate_ihc4(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.ihc4_calculator.calculate(
            er_score=_as_int(payload, "er_score"),
            pr_score=_as_int(payload, "pr_score"),
            her2_score=_as_int(payload, "her2_score"),
            ki67_percentage=_as_float(payload, "ki67_percentage", "ki67"),
            age=_as_int(payload, "age"),
            tumor_grade=_as_int(payload, "tumor_grade", "grade", required=False),
            tumor_size_cm=_as_float(payload, "tumor_size_cm", required=False),
        )
        return {
            "ihc4_score": result.ihc4_score,
            "risk_category": result.risk_category,
            "prognostic_group": result.prognostic_group,
            "subtype": result.subtype.value,
            "recommendation": result.recommendation,
            "details": result.details,
        }

    def convert_ajcc(self, payload: dict[str, Any]) -> dict[str, Any]:
        edition = _as_int(payload, "edition", required=False) or self.default_ajcc_edition
        converter = AJCCStageConverter(edition=edition)
        result = converter.convert(
            t=str(_value(payload, "t")).strip(),
            n=str(_value(payload, "n")).strip(),
            m=str(_value(payload, "m")).strip(),
            grade=_as_int(payload, "grade"),
            er_status=_normalize_status(_value(payload, "er_status")),
            pr_status=_normalize_status(_value(payload, "pr_status")),
            her2_status=_normalize_status(_value(payload, "her2_status")),
            is_pathologic=_as_bool(payload, "is_pathologic"),
        )
        return {
            "edition": edition,
            "clinical_stage": result.clinical_stage.value,
            "pathologic_stage": result.pathologic_stage.value if result.pathologic_stage else None,
            "prognostic_group": result.prognostic_group,
            "details": result.details,
        }

    def stratify(self, payload: dict[str, Any]) -> dict[str, Any]:
        biomarker = BiomarkerPanel(
            er_h_score=_as_int(payload, "er_h_score", "er_score"),
            pr_h_score=_as_int(payload, "pr_h_score", "pr_score"),
            her2_score=_as_int(payload, "her2_score"),
            ki67_percentage=_as_float(payload, "ki67_percentage", "ki67"),
            grade=_as_int(payload, "grade", "tumor_grade"),
            tumor_size_cm=_as_float(payload, "tumor_size_cm"),
            lymph_node_status=str(_value(payload, "lymph_node_status", "n")).strip(),
            metastasis=str(_value(payload, "metastasis", "m")).strip(),
            age=_as_int(payload, "age"),
            chest_wall_skin_invasion=_as_bool(payload, "chest_wall_skin_invasion"),
        )
        result = self.stratifier.stratify(biomarker)
        return {
            "subtype": result.subtype,
            "ajcc_stage": result.ajcc_stage,
            "ihc4_score": result.ihc4_score,
            "predict_score": result.predict_score,
            "risk_category": result.risk_category,
            "recommended_therapy": result.recommended_therapy,
            "clinical_notes": result.clinical_notes,
            "confidence_level": result.confidence_level,
        }

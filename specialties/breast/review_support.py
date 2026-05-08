from __future__ import annotations

from copy import deepcopy


_COMPONENT_CATALOG = {
    "ihc4": {
        "label": "IHC4 Score",
        "description": "ER/PR/HER2/Ki67 預後分數計算。",
        "module_path": "specialties.breast.ihc4_predictor",
        "symbol": "IHC4Calculator",
        "fields": [
            {"key": "er_score", "type": "number", "required": True, "label": "ER H-score"},
            {"key": "pr_score", "type": "number", "required": True, "label": "PR H-score"},
            {"key": "her2_score", "type": "number", "required": True, "label": "HER2 score"},
            {"key": "ki67_percentage", "type": "number", "required": True, "label": "Ki67 (%)"},
            {"key": "age", "type": "number", "required": True, "label": "Age"},
            {"key": "tumor_grade", "type": "number", "required": False, "label": "Grade"},
            {"key": "tumor_size_cm", "type": "number", "required": False, "label": "Tumor size (cm)"},
        ],
    },
    "ajcc": {
        "label": "AJCC Stage",
        "description": "TNM + biomarker 資訊轉 AJCC stage。",
        "module_path": "specialties.breast.ajcc_converter",
        "symbol": "AJCCStageConverter",
        "fields": [
            {"key": "t", "type": "text", "required": True, "label": "T stage"},
            {"key": "n", "type": "text", "required": True, "label": "N stage"},
            {"key": "m", "type": "text", "required": True, "label": "M stage"},
            {"key": "grade", "type": "number", "required": True, "label": "Grade"},
            {"key": "er_status", "type": "text", "required": True, "label": "ER status"},
            {"key": "pr_status", "type": "text", "required": True, "label": "PR status"},
            {"key": "her2_status", "type": "text", "required": True, "label": "HER2 status"},
            {"key": "edition", "type": "number", "required": False, "label": "AJCC edition"},
            {"key": "is_pathologic", "type": "boolean", "required": False, "label": "Pathologic stage"},
        ],
    },
    "stratification": {
        "label": "Clinical Stratification",
        "description": "整合 subtype、AJCC、IHC4 與治療建議。",
        "module_path": "specialties.breast.stratification",
        "symbol": "BreastCancerStratification",
        "fields": [
            {"key": "er_h_score", "type": "number", "required": True, "label": "ER H-score"},
            {"key": "pr_h_score", "type": "number", "required": True, "label": "PR H-score"},
            {"key": "her2_score", "type": "number", "required": True, "label": "HER2 score"},
            {"key": "ki67_percentage", "type": "number", "required": True, "label": "Ki67 (%)"},
            {"key": "grade", "type": "number", "required": True, "label": "Grade"},
            {"key": "tumor_size_cm", "type": "number", "required": True, "label": "Tumor size (cm)"},
            {"key": "lymph_node_status", "type": "text", "required": True, "label": "Lymph node status"},
            {"key": "metastasis", "type": "text", "required": True, "label": "Metastasis"},
            {"key": "age", "type": "number", "required": True, "label": "Age"},
            {"key": "chest_wall_skin_invasion", "type": "boolean", "required": False, "label": "Chest wall/skin invasion"},
        ],
    },
}


def get_component_catalog() -> dict:
    """Return a copy so callers can mutate safely."""
    return deepcopy(_COMPONENT_CATALOG)

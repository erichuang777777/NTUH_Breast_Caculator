from __future__ import annotations


def apply_breast_rules(drugs: list[dict]) -> list[dict]:
    """Attach specialty metadata without changing existing breast logic."""
    for drug in drugs:
        if drug.get("specialty_id") != "oncology_breast":
            continue
        drug.setdefault("decision_support", {})
        drug["decision_support"].setdefault(
            "available_tools",
            ["ihc4", "ajcc", "stratification"],
        )
    return drugs

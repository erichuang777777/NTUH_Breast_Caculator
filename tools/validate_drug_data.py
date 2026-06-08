#!/usr/bin/env python3
"""Semantic consistency checks for the drug database and exported API data."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "nhi_drug_coverage.db"
DEFAULT_BASELINE = ROOT / "data" / "validation" / "drug_data_known_issues.json"


BREAST_TERMS = ("breast", "mammary", "乳癌", "乳腺癌", "乳房")
OFF_SPECIALTY_TERMS = {
    "lung": ("nsclc", "lung cancer", "肺癌", "肺腺癌", "非小細胞"),
    "colorectal": ("colorectal", "colon cancer", "rectal cancer", "大腸癌", "結直腸"),
    "head_neck": ("head and neck", "squamous cell carcinoma of the head", "頭頸"),
    "hcc": ("hepatocellular", "hcc", "肝細胞", "肝癌"),
    "rcc": ("renal cell", "rcc", "腎細胞"),
    "thyroid": ("thyroid", "甲狀腺"),
    "ovarian": ("ovarian", "卵巢"),
    "prostate": ("prostate", "攝護腺", "前列腺"),
    "pancreatic": ("pancreatic", "胰臟"),
    "glioblastoma": ("glioblastoma", "膠質母"),
    "cervical": ("cervical cancer", "子宮頸"),
    "net": ("neuroendocrine", "net", "神經內分泌"),
    "tsc": ("tuberous sclerosis", "結節性硬化"),
    "melanoma": ("melanoma", "黑色素"),
    "gastric": ("gastric", "stomach", "胃癌"),
}

ALIAS_GROUPS = {
    "trastuzumab": ("Trastuzumab", "Herceptin"),
    "pertuzumab": ("Pertuzumab", "Perjeta"),
    "trastuzumab_emtansine": ("Trastuzumab emtansine", "Kadcyla"),
    "trastuzumab_deruxtecan": ("Trastuzumab deruxtecan", "Enhertu"),
    "anastrozole": ("Anastrozole", "Arimidex"),
    "everolimus": ("Everolimus", "Afinitor"),
    "lapatinib": ("Lapatinib", "Tykerb"),
    "alpelisib": ("Alpelisib", "Piqray"),
}

FORMULATION_REQUIRED = {
    "abemaciclib": ("Abemaciclib", "Verzenio"),
    "tucatinib": ("Tucatinib", "Tukysa"),
    "neratinib": ("Neratinib", "Nerlynx"),
    "atezolizumab": ("Atezolizumab", "Tecentriq"),
}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    target: str
    title: str
    detail: str = ""

    @property
    def key(self) -> str:
        return f"{self.code}|{self.target}"


def norm(value) -> str:
    return str(value or "").strip().lower()


def text_blob(*values) -> str:
    return "\n".join(str(v or "") for v in values).lower()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_rows(conn: sqlite3.Connection):
    drugs = [dict(r) for r in conn.execute("SELECT * FROM drugs ORDER BY id")]
    rules = [dict(r) for r in conn.execute("SELECT * FROM coverage_rules ORDER BY id")]
    formulations = [dict(r) for r in conn.execute("SELECT * FROM drug_formulations ORDER BY id")]
    rules_by_drug: dict[int, list[dict]] = {}
    for rule in rules:
        rules_by_drug.setdefault(rule["drug_id"], []).append(rule)
    return drugs, rules_by_drug, formulations


def load_baseline(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    known = data.get("known", data if isinstance(data, list) else [])
    keys = set()
    for item in known:
        if isinstance(item, str):
            keys.add(item)
        elif isinstance(item, dict) and item.get("code") and item.get("target"):
            keys.add(f"{item['code']}|{item['target']}")
    return keys


def clinical_blob(drug: dict, rules_by_drug: dict[int, list[dict]]) -> str:
    pieces = [
        drug.get("generic_name"),
        drug.get("trade_names"),
        drug.get("indication"),
        drug.get("clinical_tags"),
        drug.get("stage"),
        drug.get("dosage_info"),
    ]
    for rule in rules_by_drug.get(drug["id"], []):
        pieces.extend([rule.get("condition"), rule.get("exclusion"), rule.get("nhi_ref_number")])
    return text_blob(*pieces)


def check_off_specialty(drugs, rules_by_drug) -> list[Issue]:
    issues: list[Issue] = []
    for drug in drugs:
        if drug.get("specialty_id") != "oncology_breast":
            continue
        blob = clinical_blob(drug, rules_by_drug)
        hits = [
            label
            for label, terms in OFF_SPECIALTY_TERMS.items()
            if any(term in blob for term in terms)
        ]
        if hits and not any(term in blob for term in BREAST_TERMS):
            issues.append(Issue(
                "warning",
                "off_specialty_breast_row",
                f"drug:{drug['id']}",
                f"{drug['generic_name']} has non-breast wording in oncology_breast; review if this is supportive/adjuvant data or a misplaced row",
                ", ".join(hits),
            ))
    return issues


def check_alias_duplicates(drugs) -> list[Issue]:
    issues: list[Issue] = []
    names_to_ids: dict[str, list[int]] = {}
    generic_names = {norm(d["generic_name"]) for d in drugs}
    for drug in drugs:
        names_to_ids.setdefault(norm(drug["generic_name"]), []).append(drug["id"])
        for alias in str(drug.get("trade_names") or "").replace("/", ",").split(","):
            alias_n = norm(alias)
            if alias_n and alias_n in generic_names and alias_n != norm(drug["generic_name"]):
                issues.append(Issue(
                    "error",
                    "trade_name_is_other_generic",
                    f"drug:{drug['id']}",
                    f"{drug['generic_name']} trade_names contains another generic row",
                    alias.strip(),
                ))

    by_name = {norm(d["generic_name"]): d for d in drugs}
    for group, aliases in ALIAS_GROUPS.items():
        present = [by_name[norm(name)] for name in aliases if norm(name) in by_name]
        if len(present) > 1:
            target = "drug:" + ",".join(str(d["id"]) for d in present)
            issues.append(Issue(
                "warning",
                "brand_generic_duplicate_rows",
                target,
                f"Brand/generic duplicate rows should be merged or explicitly justified: {group}",
                ", ".join(d["generic_name"] for d in present),
            ))

    for name, ids in names_to_ids.items():
        if name and len(ids) > 1:
            issues.append(Issue(
                "error",
                "duplicate_generic_name",
                "drug:" + ",".join(str(i) for i in ids),
                f"Duplicate generic_name rows: {name}",
            ))
    return issues


def check_coverage_semantics(drugs, rules_by_drug) -> list[Issue]:
    issues: list[Issue] = []
    for drug in drugs:
        blob = clinical_blob(drug, rules_by_drug)
        target = f"drug:{drug['id']}"
        if drug.get("nhi_price") is not None and any(term in blob for term in ("自費", "未給付", "non-reimbursed")):
            issues.append(Issue(
                "warning",
                "self_pay_text_with_nhi_price",
                target,
                f"{drug['generic_name']} has self-pay/non-covered text but also a drug-level NHI price",
            ))
        if norm(drug["generic_name"]) == "olaparib" and "甲狀腺髓質癌" in blob:
            issues.append(Issue(
                "error",
                "known_bad_indication_text",
                target,
                "Olaparib contains copied thyroid cancer indication text",
            ))
        if norm(drug["generic_name"]) == "exemestane" and "2.5mg" in blob:
            issues.append(Issue(
                "error",
                "known_bad_condition_text",
                target,
                "Exemestane coverage text appears copied from 2.5mg aromatase inhibitor dosing",
            ))
    return issues


def check_formulation_links(drugs, formulations) -> list[Issue]:
    issues: list[Issue] = []
    drug_text = "\n".join(
        f"{d.get('generic_name','')} {d.get('trade_names','')}".lower()
        for d in drugs
        if d.get("specialty_id") == "oncology_breast"
    )
    form_keys = {norm(f.get("drug_key")) for f in formulations}
    form_brands = {norm(f.get("brand_name")) for f in formulations}
    for key, aliases in FORMULATION_REQUIRED.items():
        if key in form_keys or any(norm(alias) in form_brands for alias in aliases):
            if not any(norm(alias) in drug_text for alias in aliases):
                issues.append(Issue(
                    "warning",
                    "formulation_without_drug_row",
                    f"formulation:{key}",
                    f"{aliases[0]} has formulation data but no matching breast drug row",
                ))
    return issues


def validate() -> list[Issue]:
    conn = connect()
    try:
        drugs, rules_by_drug, formulations = load_rows(conn)
    finally:
        conn.close()
    issues: list[Issue] = []
    issues.extend(check_off_specialty(drugs, rules_by_drug))
    issues.extend(check_alias_duplicates(drugs))
    issues.extend(check_coverage_semantics(drugs, rules_by_drug))
    issues.extend(check_formulation_links(drugs, formulations))
    return issues


def render_text(issues: list[Issue], baseline: set[str], hide_known: bool = False) -> str:
    if not issues:
        return "[OK] Drug data semantic validation passed"
    visible = [issue for issue in issues if not hide_known or issue.key not in baseline]
    known_count = len([issue for issue in issues if issue.key in baseline])
    if not visible:
        return f"[OK] Drug data semantic validation passed ({known_count} known issue(s) tracked)"
    lines = []
    for issue in visible:
        status = "known" if issue.key in baseline else "new"
        detail = f" - {issue.detail}" if issue.detail else ""
        lines.append(f"[{issue.severity.upper()}][{status}] {issue.code} {issue.target}: {issue.title}{detail}")
    if hide_known and known_count:
        lines.append(f"[INFO] Hidden known issue(s): {known_count}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE, help="Known issue baseline JSON")
    parser.add_argument("--strict", action="store_true", help="Fail on new error-level issues")
    parser.add_argument("--hide-known", action="store_true", help="Only print new issues in text output")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    baseline = load_baseline(args.baseline)
    issues = validate()
    if args.format == "json":
        print(json.dumps([issue.__dict__ | {"key": issue.key, "known": issue.key in baseline} for issue in issues], ensure_ascii=False, indent=2))
    else:
        print(render_text(issues, baseline, args.hide_known))

    new_errors = [issue for issue in issues if issue.severity == "error" and issue.key not in baseline]
    if args.strict and new_errors:
        print(f"[FAIL] {len(new_errors)} new error-level drug data issue(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

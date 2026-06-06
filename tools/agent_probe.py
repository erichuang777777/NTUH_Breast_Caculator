#!/usr/bin/env python3
"""Probe the local care copilot against known data-backed questions.

This is intentionally a black-box smoke test for `/api/agent`: it checks tool
use and key facts, not exact natural-language wording.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "nhi_drug_coverage.db"


class ProbeFailure(Exception):
    pass


def db_one(sql: str, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(sql, params).fetchone()
    conn.close()
    if not row:
        raise ProbeFailure(f"Missing DB fixture for query: {sql} {params}")
    return dict(row)


def post_json(base_url: str, path: str, payload: dict, timeout: int):
    url = base_url.rstrip("/") + path
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ProbeFailure(f"Cannot call {url}: {exc}") from exc


def contains(text: str, *patterns: str) -> bool:
    return all(re.search(pattern, text, re.I) for pattern in patterns)


def ensure(condition: bool, message: str):
    if not condition:
        raise ProbeFailure(message)


def reply_text(data: dict) -> str:
    return str(data.get("reply") or "")


def called_tools(data: dict) -> set[str]:
    return set(data.get("called_tools") or [])


def price_pattern(value) -> str:
    if value is None:
        return r"未列|沒有|無"
    raw = str(int(float(value)))
    comma = f"{int(float(value)):,}"
    return rf"{re.escape(raw)}|{re.escape(comma)}"


def generate_cases():
    perjeta = db_one(
        """SELECT d.generic_name, d.trade_names, d.nhi_price, d.price_unit,
                  cr.therapy_line, cr.prior_auth_required
           FROM drugs d
           LEFT JOIN coverage_rules cr ON cr.drug_id = d.id
           WHERE d.id = 1757"""
    )
    keytruda = db_one(
        """SELECT d.generic_name, d.trade_names, d.nhi_price, d.price_unit,
                  cr.therapy_line, cr.prior_auth_required
           FROM drugs d
           LEFT JOIN coverage_rules cr ON cr.drug_id = d.id
           WHERE LOWER(d.generic_name) IN ('keytruda', 'pembrolizumab')
              OR LOWER(d.trade_names) LIKE '%keytruda%'
           ORDER BY CASE WHEN LOWER(d.generic_name)='keytruda' THEN 0 ELSE 1 END
           LIMIT 1"""
    )

    def check_perjeta(data):
        text = reply_text(data)
        tools = called_tools(data)
        ensure({"drug-search", "formulation-lookup"} <= tools, f"Perjeta should call drug/formulation tools, got {tools}")
        ensure(contains(text, r"Perjeta|Pertuzumab", r"第\s*1|第一", r"事前審查|事審"), f"Perjeta answer missing line/auth facts: {text}")
        ensure(re.search(price_pattern(perjeta["nhi_price"]), text), f"Perjeta answer missing price {perjeta['nhi_price']}: {text}")

    def check_keytruda(data):
        text = reply_text(data)
        tools = called_tools(data)
        ensure({"drug-search", "formulation-lookup"} <= tools, f"Keytruda should call drug/formulation tools, got {tools}")
        ensure(contains(text, r"Keytruda|Pembrolizumab|pembrolizumab", r"TNBC|三陰|ER.*-|HER2.*-"), f"Keytruda answer missing TNBC drug facts: {text}")
        ensure(re.search(price_pattern(keytruda["nhi_price"]), text), f"Keytruda answer missing price {keytruda['nhi_price']}: {text}")

    def check_staging(data):
        text = reply_text(data)
        tools = called_tools(data)
        ensure("calculate/staging-score" in tools, f"Staging question should call staging tool, got {tools}")
        ensure(re.search(r"IIIA|III\s*A", text, re.I), f"T3N1M0 should include IIIA: {text}")
        ensure(not re.search(r"IIIB|III\s*B", text, re.I), f"T3N1M0 should not be IIIB: {text}")

    def check_scores(data):
        text = reply_text(data)
        tools = called_tools(data)
        ensure("calculate/risk-scores" in tools, f"Risk score question should call risk score tool, got {tools}")
        ensure(contains(text, r"CTS5", r"IHC4", r"NPI|Nottingham|Magee"), f"Risk answer missing score names: {text}")

    def check_missing(data):
        text = reply_text(data)
        ensure(re.search(r"缺|需要|不足|不完整", text), f"Missing-field answer should explain missing fields: {text}")
        ensure(re.search(r"size|大小|腫瘤|grade|ER|PR|HER2|Ki-?67|淋巴", text, re.I), f"Missing-field answer should name missing inputs: {text}")

    def check_extract(data):
        patch = data.get("patient_patch") or {}
        ensure(patch.get("age") in ("49", 49), f"Expected age patch 49, got {patch}")
        ensure(patch.get("cT") == "T2" and patch.get("cN") == "N1" and patch.get("cM") == "M0", f"Expected T2N1M0 patch, got {patch}")
        ensure(patch.get("er") == "+" and patch.get("pr") == "+" and patch.get("her2") == "+", f"Expected receptor patch, got {patch}")
        ensure(str(patch.get("ki67")) in ("35", "35.0"), f"Expected Ki67 35 patch, got {patch}")

    return [
        {
            "name": "drug_price_perjeta",
            "message": "HER2+ LN+ 可以用 Perjeta 嗎？請列出線別、適應症、事前審查和健保價錢。",
            "patient_context": {"her2": "+", "cN": "N1", "cT": "T2", "cM": "M0", "er": "+", "pr": "+"},
            "check": check_perjeta,
        },
        {
            "name": "drug_price_keytruda_tnbc",
            "message": "三陰性乳癌 cT2N1M0 可以查 Keytruda/pembrolizumab 嗎？請列適應症與價格。",
            "patient_context": {"her2": "-", "cN": "N1", "cT": "T2", "cM": "M0", "er": "-", "pr": "-"},
            "check": check_keytruda,
        },
        {
            "name": "staging_t3n1m0",
            "message": "ER+ PR+ HER2-，cT3N1M0，grade 2，解剖分期是第幾期？",
            "patient_context": {"cT": "T3", "cN": "N1", "cM": "M0", "er": "+", "pr": "+", "her2": "-", "grade": "2"},
            "check": check_staging,
        },
        {
            "name": "risk_scores_complete",
            "message": "請用目前欄位計算 CTS5、IHC4、NPI、Magee，並簡短說明風險。",
            "patient_context": {
                "age": 55,
                "size_mm": 20,
                "tumor_size_mm": 20,
                "grade": 2,
                "nodes_pos": 0,
                "er_hscore": 270,
                "pr_hscore": 200,
                "her2": "-",
                "ki67": 15,
            },
            "check": check_scores,
        },
        {
            "name": "missing_fields_scores",
            "message": "這個病人可以計算 PREDICT、CTS5、IHC4 嗎？如果不行請列出缺少欄位。",
            "patient_context": {"age": 49, "cT": "T2", "cN": "N1", "cM": "M0"},
            "check": check_missing,
        },
        {
            "name": "free_text_extraction",
            "message": "病理摘要：49歲，cT2N1M0，invasive ductal carcinoma size 25 mm，grade 3，ER positive，PR positive，HER2 3+，Ki-67 35%。請先抽取欄位。",
            "patient_context": {},
            "check": check_extract,
        },
    ]


def run_probe(base_url: str, timeout: int):
    deterministic_sample = {
        "age": 55,
        "size_mm": 20,
        "tumor_size_mm": 20,
        "grade": 2,
        "nodes_pos": 0,
        "cT": "T2",
        "cN": "N0",
        "cM": "M0",
        "er_hscore": 270,
        "pr_hscore": 200,
        "her2": "-",
        "ki67": 15,
    }
    staging = post_json(base_url, "/api/calculate/staging-score", deterministic_sample, timeout)
    ensure(staging.get("result", {}).get("ajcc_v8", {}).get("selected") == "IIA", f"Deterministic staging API failed: {staging}")
    scores = post_json(base_url, "/api/calculate/risk-scores", deterministic_sample, timeout)
    ensure({"cts5", "npi", "ihc4", "magee"} <= set((scores.get("scores") or {}).keys()), f"Deterministic risk API missing scores: {scores}")
    print("[OK] deterministic calculation endpoints")

    failed = []
    for case in generate_cases():
        payload = {
            "message": case["message"],
            "patient_context": case["patient_context"],
            "tool_registry": [],
            "client": {"probe": True},
        }
        try:
            data = post_json(base_url, "/api/agent", payload, timeout)
            case["check"](data)
            print(f"[OK] {case['name']} -> tools={','.join(data.get('called_tools') or [])}")
        except Exception as exc:
            failed.append((case["name"], str(exc)))
            print(f"[FAIL] {case['name']}: {exc}", file=sys.stderr)

    if failed:
        print("\nFailed probes:", file=sys.stderr)
        for name, reason in failed:
            print(f"- {name}: {reason}", file=sys.stderr)
        raise SystemExit(1)
    print("[OK] agent probes passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--timeout", type=int, default=150)
    args = parser.parse_args()
    run_probe(args.base_url, args.timeout)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate and run an answer-grounded benchmark for `/api/agent`.

The corpus is generated from local structured answers: SQLite drug/formulation
rows plus deterministic calculator outputs. The runner validates tool calls and
key facts instead of exact wording, so different LLMs can be compared behind the
same gateway contract.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "nhi_drug_coverage.db"
DEFAULT_CORPUS = ROOT / "data" / "agent_bench" / "bench_v1.json"
DEFAULT_RESULT = ROOT / "data" / "agent_bench" / "bench_v1_results_2026-06-05.json"


def db_rows(sql: str, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def clean_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_text(value) -> str:
    return re.sub(r"\s+", "", clean_text(value).lower())


def price_int(value):
    if value in (None, ""):
        return None
    return int(round(float(value)))


def price_regex(value):
    p = price_int(value)
    if p is None:
        return r"未列|無|沒有|自費"
    return rf"{p}|{p:,}"


def canonical_name(row):
    return clean_text(row.get("trade_names") or row.get("brand_name") or row.get("generic_name") or row.get("drug_key"))


def case(case_id, category, question, patient_context, expected, reference_answer=""):
    return {
        "id": case_id,
        "category": category,
        "question": question,
        "patient_context": patient_context,
        "expected": expected,
        "reference_answer": reference_answer,
    }


def case_key(case_obj):
    expected = case_obj.get("expected") or {}
    if expected.get("drug_identity"):
        return (case_obj["category"], expected["drug_identity"])
    if expected.get("formulation_identity"):
        return (case_obj["category"], expected["formulation_identity"])
    if expected.get("expected_stage"):
        patient = case_obj.get("patient_context") or {}
        return (case_obj["category"], patient.get("cT"), patient.get("cN"), patient.get("cM"))
    if case_obj.get("category") in ("risk_scores", "missing_fields"):
        patient = case_obj.get("patient_context") or {}
        return (case_obj["category"], tuple(sorted((str(k), str(v)) for k, v in patient.items())))
    patch = expected.get("expected_patch")
    if patch:
        return (case_obj["category"], tuple(sorted((str(k), str(v)) for k, v in patch.items())))
    return (case_obj["category"], normalize_text(case_obj.get("question")))


def dedupe_cases(cases):
    seen = set()
    out = []
    duplicates = []
    for c in cases:
        key = case_key(c)
        if key in seen:
            duplicates.append({"id": c.get("id"), "category": c.get("category"), "question": c.get("question")})
            continue
        seen.add(key)
        out.append(c)
    return out, duplicates


def generate_drug_cases(limit=30):
    rows = db_rows(
        """SELECT d.id, d.generic_name, d.trade_names, d.indication, d.stage,
                  d.nhi_price, d.price_unit, cr.therapy_line, cr.prior_auth_required
           FROM drugs d
           LEFT JOIN coverage_rules cr ON cr.drug_id = d.id
           WHERE d.specialty_id = 'oncology_breast'
             AND d.generic_name IS NOT NULL
             AND (d.nhi_price IS NOT NULL OR cr.prior_auth_required IS NOT NULL)
           ORDER BY
             CASE
               WHEN LOWER(d.generic_name) IN ('perjeta','pertuzumab','keytruda','pembrolizumab','herceptin','trastuzumab') THEN 0
               ELSE 1
             END,
             d.generic_name
           LIMIT ?""",
        (limit * 4,),
    )
    out = []
    seen = set()
    for row in rows:
        name = canonical_name(row)
        generic = clean_text(row["generic_name"])
        identity = normalize_text(name or generic)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        expected = {
            "must_call": ["drug-search"],
            "contains_any": [name, generic],
            "contains_regex": [price_regex(row["nhi_price"])],
            "drug_id": row["id"],
            "drug_identity": identity,
        }
        if row.get("therapy_line"):
            line = int(row["therapy_line"])
            zh_line = {1: "一", 2: "二", 3: "三", 4: "四"}.get(line, str(line))
            expected["contains_regex"].append(rf"第\s*{line}|第{line}|{line}\s*線|第\s*{zh_line}\s*線|{zh_line}\s*線")
        if row.get("prior_auth_required"):
            expected["contains_regex"].append(r"事前審查|事審")
        templates = [
            "請查 {name}（{generic}）在乳癌的適應症、治療線別、健保價錢與是否需要事前審查。",
            "門診病人問到 {name} / {generic}，請只用網站資料列出給付重點、價格和是否事審。",
            "{generic} 這個藥在我們資料庫裡怎麼寫？請回覆商品名、線別、健保價與限制。",
            "我只想核對 {name}：乳癌相關 indication、line、price unit 和 prior auth 是什麼？",
            "幫我用資料庫查 {generic}，不要補外部 guideline，只列本系統查到的適應症摘要與價格。"
        ]
        q = templates[len(out) % len(templates)].format(name=name, generic=generic)
        reference = (
            f"{name}（{generic}）：線別 {row.get('therapy_line') or '未指定'}；"
            f"健保價 {price_int(row.get('nhi_price')) if row.get('nhi_price') is not None else '未列'}"
            f"{('/' + clean_text(row.get('price_unit'))) if row.get('price_unit') else ''}；"
            f"{'需事前審查' if row.get('prior_auth_required') else '未標示需事前審查'}。"
            f"適應症摘要：{clean_text(row.get('indication'))[:240]}"
        )
        out.append(case(f"drug-{len(out) + 1:03d}", "drug_price_indication", q, {}, expected, reference))
        if len(out) >= limit:
            break
    return out


def generate_formulation_cases(limit=15):
    rows = db_rows(
        """SELECT drug_key, brand_name, formulation, dose_mg, dose_unit,
                  category, nhi_price, ntuh_price, nhi_covered, regimen_use
           FROM drug_formulations
           WHERE brand_name IS NOT NULL
           ORDER BY
             CASE WHEN LOWER(brand_name) IN ('perjeta','herceptin','keytruda') THEN 0 ELSE 1 END,
             brand_name
           LIMIT ?""",
        (limit * 4,),
    )
    out = []
    seen = set()
    for row in rows:
        name = canonical_name(row)
        identity = normalize_text(f"{row.get('drug_key')}|{row.get('brand_name')}|{row.get('formulation')}")
        if not identity or identity in seen:
            continue
        seen.add(identity)
        formulation = clean_text(row.get('formulation')) or clean_text(row.get('dose_mg')) + clean_text(row.get('dose_unit'))
        templates = [
            "{name}（{formulation}）的規格、劑量單位、健保價與院內價是多少？如果有常用 regimen tag 也請列出。",
            "請核對院內配方資料：{name} {formulation} 的 NHI/NTUH price 與 regimen tag。",
            "如果要估價，{name} 這個 {formulation} 單位在資料庫是多少錢？",
            "{name} 規格 {formulation}：請回覆 drug_key、健保價、院內價，不要推測其他規格。"
        ]
        q = templates[len(out) % len(templates)].format(name=name, formulation=formulation)
        out.append(case(
            f"form-{len(out) + 1:03d}",
            "formulation_price",
            q,
            {},
            {
                "must_call": ["formulation-lookup"],
                "contains_any": [name, clean_text(row["drug_key"])],
                "contains_regex": [price_regex(row["nhi_price"])],
                "formulation_identity": identity,
            },
            (
                f"{name}：規格 {clean_text(row.get('formulation')) or '未列'}；"
                f"劑量 {clean_text(row.get('dose_mg'))} {clean_text(row.get('dose_unit'))}；"
                f"健保價 {price_int(row.get('nhi_price')) if row.get('nhi_price') is not None else '未列'}；"
                f"院內價 {price_int(row.get('ntuh_price')) if row.get('ntuh_price') is not None else '未列'}；"
                f"regimen tag {clean_text(row.get('regimen_use')) or '未列'}。"
            ),
        ))
        if len(out) >= limit:
            break
    return out


def generate_staging_cases(limit=20):
    sys.path.insert(0, str(ROOT))
    from api_calculators import staging_score

    preferred = [
        ("Tis", "N0", "M0"), ("T1", "N0", "M0"), ("T1", "N1", "M0"), ("T2", "N0", "M0"),
        ("T2", "N1", "M0"), ("T3", "N0", "M0"), ("T3", "N1", "M0"), ("T1", "N2", "M0"),
        ("T2", "N2", "M0"), ("T3", "N2", "M0"), ("T4", "N0", "M0"), ("T4", "N2", "M0"),
        ("T1", "N3", "M0"), ("T2", "N3", "M0"), ("T3", "N3", "M0"), ("T4", "N3", "M0"),
        ("T1", "N0", "M1"), ("T2", "N1", "M1"), ("T3", "N1", "M1"), ("T4", "N2", "M1"),
    ]
    t_values = ["Tis", "T0", "T1", "T1mi", "T1a", "T1b", "T1c", "T2", "T3", "T4"]
    n_values = ["N0", "N0(i+)", "N1mi", "N1", "N1a", "N2", "N2a", "N3", "N3a"]
    m_values = ["M0", "M1"]
    combos = []
    seen = set()
    for combo in preferred + [(t, n, m) for m in m_values for t in t_values for n in n_values]:
        if combo in seen:
            continue
        seen.add(combo)
        combos.append(combo)
        if len(combos) >= limit:
            break
    out = []
    for i, (t, n, m) in enumerate(combos, 1):
        result = staging_score({"cT": t, "cN": n, "cM": m})
        stage = result["ajcc_v8"]["selected"]
        q = f"請用 AJCC v8 解剖分期回答：c{t}{n}{m} 是第幾期？"
        out.append(case(
            f"stage-{i:03d}",
            "staging",
            q,
            {"cT": t, "cN": n, "cM": m},
            {
                "must_call": ["calculate/staging-score"],
                "contains_regex": [re.escape(stage) if stage else r"無法|不足|不適用"],
                "expected_stage": stage,
            },
            f"AJCC v8 解剖分期：c{t}{n}{m} = {stage or '無法判定'}。",
        ))
    return out


def generate_score_cases(limit=20):
    sys.path.insert(0, str(ROOT))
    from api_calculators import staging_score

    samples = [
        {"age": 49, "size_mm": 20, "tumor_size_mm": 20, "grade": 3, "nodes_pos": 0, "er_hscore": 240, "pr_hscore": 180, "her2": "-", "ki67": 20},
        {"age": 55, "size_mm": 25, "tumor_size_mm": 25, "grade": 2, "nodes_pos": 1, "er_hscore": 270, "pr_hscore": 200, "her2": "-", "ki67": 15},
        {"age": 62, "size_mm": 35, "tumor_size_mm": 35, "grade": 3, "nodes_pos": 4, "er_hscore": 210, "pr_hscore": 80, "her2": "-", "ki67": 30},
        {"age": 45, "size_mm": 18, "tumor_size_mm": 18, "grade": 2, "nodes_pos": 2, "er_hscore": 180, "pr_hscore": 120, "her2": "+", "ki67": 35},
        {"age": 70, "size_mm": 12, "tumor_size_mm": 12, "grade": 1, "nodes_pos": 0, "er_hscore": 290, "pr_hscore": 260, "her2": "-", "ki67": 8},
    ]
    out = []
    idx = 1
    while len(out) < limit:
        sample = dict(samples[(idx - 1) % len(samples)])
        sample["age"] = sample["age"] + ((idx - 1) // len(samples))
        scores = staging_score(sample)["scores"]
        expected_names = [name.upper() if name != "magee" else "Magee" for name in scores.keys()]
        q = (
            "請根據目前病人資料計算可用的 CTS5、IHC4、NPI、Magee 分數，並說明哪些分數不適用或缺資料。"
            f"資料：age {sample.get('age')}、size {sample.get('size_mm')}mm、nodes {sample.get('nodes_pos')}、"
            f"grade {sample.get('grade')}、ER H-score {sample.get('er_hscore')}、PR H-score {sample.get('pr_hscore')}、"
            f"HER2 {sample.get('her2')}、Ki67 {sample.get('ki67')}%。"
        )
        out.append(case(
            f"score-{idx:03d}",
            "risk_scores",
            q,
            sample,
            {
                "must_call": ["calculate/risk-scores"],
                "contains_any": expected_names[:],
                "score_keys": sorted(scores.keys()),
            },
            "可計算分數：" + "；".join(
                f"{k.upper() if k != 'magee' else 'Magee'}={clean_text(v.get('value') if isinstance(v, dict) else v)}"
                for k, v in scores.items()
            ),
        ))
        idx += 1
    return out


def generate_missing_cases(limit=10):
    templates = [
        ({}, "只有一句：乳癌病人，請問可以算分期與 PREDICT/CTS5/IHC4 嗎？", "缺 T/N/M、年齡、腫瘤大小、grade、nodes、ER/PR/HER2/Ki67 等關鍵欄位。"),
        ({"age": 49}, "已有年齡 49 歲，可以算 PREDICT、CTS5、IHC4 嗎？缺什麼？", "仍缺 tumor size、nodes、grade、ER/PR/HER2/Ki67 等欄位。"),
        ({"age": 49, "cT": "T2", "cN": "N1"}, "有 T2N1 但沒有 M，能不能判斷 AJCC 與風險分數？", "AJCC 至少缺 M；風險分數仍缺 size、grade、ER/PR/HER2/Ki67 等。"),
        ({"age": 55, "size_mm": 20, "grade": 2}, "有 age/size/grade，但沒有 ER PR HER2 Ki67，哪些工具不能算？", "IHC4/CTS5/PREDICT 仍需 ER、PR、HER2、Ki67 與 nodes。"),
        ({"er": "+", "pr": "+", "her2": "-"}, "只有 ER/PR/HER2，請告訴我 PREDICT、CTS5、IHC4 還缺哪些欄位。", "仍缺 age、tumor size、positive nodes、grade、Ki67，IHC4 也需要 ER/PR 定量或 H-score。"),
        ({"cT": "T2", "cN": "N1", "cM": "M0"}, "只有 T2N1M0，能不能算藥物、分期、PREDICT？缺哪些？", "可判斷解剖分期；PREDICT/風險分數缺 age、size、grade、ER/PR/HER2/Ki67/nodes 數字。"),
        ({"age": 62, "er": "+", "pr": "-", "her2": "-"}, "62 歲 HR+/HER2- 但沒有 size/node/grade/Ki67，CTS5 和 IHC4 能算嗎？", "CTS5 缺 size、nodes、grade；IHC4 缺 ER/PR 定量與 Ki67。"),
        ({"size_mm": 18, "grade": 2, "ki67": 18}, "有 size 18mm、grade 2、Ki67 18%，但沒有 receptor，能算哪些？", "仍缺 ER/PR/HER2；IHC4、PREDICT、CTS5 不能完整計算。"),
        ({"age": 45, "cM": "M0", "er": "-", "pr": "-", "her2": "-"}, "45 歲 TNBC M0，沒有 T/N/size/grade，可以給完整建議嗎？", "仍缺 T、N、size、grade、nodes 等，不能完整分期與療程判讀。"),
        ({"age": 70, "size_mm": 12, "nodes_pos": 0}, "70 歲 size 12mm nodes 0，缺 receptor 和 grade 時分數會怎樣？", "仍缺 grade、ER/PR/HER2/Ki67；多數分數不能完整計算。"),
    ]
    out = []
    dynamic = []
    ages = [38, 45, 49, 55, 62, 70]
    receptors = [
        {"er": "+", "pr": "+", "her2": "-"},
        {"er": "-", "pr": "-", "her2": "-"},
        {"er": "+", "pr": "-", "her2": "+"},
        {"er": "+", "pr": "+", "her2": "+"},
    ]
    stages = [
        {"cT": "T1c", "cN": "N0", "cM": "M0"},
        {"cT": "T2", "cN": "N1", "cM": "M0"},
        {"cT": "T3", "cN": "N1", "cM": "M0"},
        {"cT": "T4", "cN": "N2", "cM": "M0"},
    ]
    for age in ages:
        for rec in receptors:
            for st in stages:
                p = {"age": age, **rec, **st}
                missing = "size、grade、nodes_pos、Ki67、Oncotype RS 或病理細節"
                q = f"目前只有 age {age}、{st['cT']}{st['cN']}{st['cM']}、ER{rec['er']} PR{rec['pr']} HER2{rec['her2']}，請問能不能直接算 PREDICT/CTS5/IHC4 或決定化療？還缺什麼？"
                dynamic.append((p, q, f"不可直接完成所有計算或治療判斷；仍缺 {missing}。"))
    merged = templates + dynamic
    for i in range(1, limit + 1):
        patient, q, reference = merged[(i - 1) % len(merged)]
        out.append(case(
            f"missing-{i:03d}",
            "missing_fields",
            q,
            dict(patient),
            {
                "contains_regex": [r"缺|需要|不足|不完整", r"size|大小|腫瘤|grade|ER|PR|HER2|Ki-?67|T|N|M|淋巴"],
            },
            reference,
        ))
    return out


def generate_extraction_cases(limit=5):
    samples = [
        ("49歲，cT2N1M0，IDC size 25 mm，grade 3，ER positive，PR positive，HER2 3+，Ki-67 35%。", {"age": "49", "cT": "T2", "cN": "N1", "cM": "M0", "er": "+", "pr": "+", "her2": "+", "ki67": "35"}),
        ("62歲，cT1cN0M0，tumor size 12 mm，G2，ER+，PR-，HER2 negative，Ki67 10%。", {"age": "62", "cT": "T1c", "cN": "N0", "cM": "M0", "er": "+", "pr": "-", "her2": "-", "ki67": "10"}),
        ("55歲，pT3N1M0，size 52 mm，grade II，ER positive，PR positive，HER2 1+，Ki-67 18%。", {"age": "55", "pT": "T3", "pN": "N1", "pM": "M0", "er": "+", "pr": "+", "her2": "-", "ki67": "18"}),
        ("45歲，cTisN0M0，DCIS only，grade 2，ER positive PR positive HER2 negative Ki67 5%。", {"age": "45", "cT": "Tis", "cN": "N0", "cM": "M0", "er": "+", "pr": "+", "her2": "-", "ki67": "5"}),
        ("70歲，cT4N2M0，ER negative，PR negative，HER2 0+，Ki67 70%，tumor size 60mm，G3。", {"age": "70", "cT": "T4", "cN": "N2", "cM": "M0", "er": "-", "pr": "-", "her2": "-", "ki67": "70"}),
    ]
    ages = [41, 48, 53, 59, 66, 73]
    tnm = [("cT1c", "N0", "M0", "18"), ("cT2", "N1mi", "M0", "22"), ("cT3", "N1", "M0", "51"), ("pT2", "N2a", "M0", "30")]
    bio = [
        ("ER 90%, PR 80%, HER2 2+ ISH negative, Ki-67 12%", "+", "+", "-", "12"),
        ("ER negative, PR negative, HER2 0+, Ki67 75%", "-", "-", "-", "75"),
        ("ER positive, PR negative, HER2 3+, Ki-67 35%", "+", "-", "+", "35"),
        ("ER 50%, PR 5%, HER2 1+, Ki67 5-14%", "+", "+", "-", "5-14"),
    ]
    for age in ages:
        for t, n, m, size in tnm:
            for marker, er, pr, her2, ki67 in bio:
                prefix = "p" if t.startswith("p") else "c"
                t_clean = t[1:] if t.startswith(("c", "p")) else t
                text = f"{age}歲，{t}{n}{m}，invasive tumor size {size} mm，grade II，{marker}。"
                patch = {"age": str(age), f"{prefix}T": t_clean, f"{prefix}N": n, f"{prefix}M": m, "er": er, "pr": pr, "her2": her2, "ki67": ki67}
                samples.append((text, patch))
    out = []
    for i in range(1, limit + 1):
        text, expected_patch = samples[(i - 1) % len(samples)]
        out.append(case(
            f"extract-{i:03d}",
            "field_extraction",
            f"請從這段病理/臨床文字抽取欄位，先不要直接寫入：{text}",
            {},
            {"expected_patch": expected_patch},
            "應抽取欄位：" + "、".join(f"{k}={v}" for k, v in expected_patch.items()),
        ))
    return out


def generate_reasoning_cases(limit=12):
    rows = {}
    for name in ("Phesgo", "Perjeta", "Herceptin", "Pembrolizumab", "Anastrozole", "Letrozole"):
        found = db_rows(
            """SELECT d.id, d.generic_name, d.trade_names, d.indication, d.nhi_price,
                      d.price_unit, d.dosage_info, cr.therapy_line, cr.prior_auth_required,
                      cr.condition
               FROM drugs d
               LEFT JOIN coverage_rules cr ON cr.drug_id = d.id
               WHERE LOWER(d.generic_name)=LOWER(?) OR LOWER(COALESCE(d.trade_names,'')) LIKE LOWER(?)
               ORDER BY d.id
               LIMIT 1""",
            (name, f"%{name}%"),
        )
        if found:
            rows[name.lower()] = found[0]
    forms = {}
    for key in ("goserelin", "letrozole", "pembrolizumab", "pertuzumab"):
        forms[key] = db_rows(
            """SELECT drug_key, brand_name, formulation, nhi_price, ntuh_price,
                      nhi_covered, regimen_use
               FROM drug_formulations
               WHERE drug_key=?
               ORDER BY dose_mg DESC""",
            (key,),
        )

    keytruda_price = price_int((forms.get("pembrolizumab") or [{}])[0].get("nhi_price"))
    kn522_cycles = 17
    kn522_total = (keytruda_price or 0) * kn522_cycles
    zoladex_la = next((r for r in forms.get("goserelin", []) if "10.8" in str(r.get("formulation"))), (forms.get("goserelin") or [{}])[0])
    femara = (forms.get("letrozole") or [{}])[0]
    zoladex_3y = price_int(zoladex_la.get("ntuh_price")) * 12 if zoladex_la.get("ntuh_price") is not None else None
    femara_3y = price_int(femara.get("ntuh_price")) * 365 * 3 if femara.get("ntuh_price") is not None else None
    combo_3y = (zoladex_3y or 0) + (femara_3y or 0)

    cases = [
        case(
            "reason-001",
            "reasoning_composition",
            "HER2+、LN-、M0 早期乳癌，網站資料內哪些 HER2 藥物可能需要自費？請同時指出哪些資料列是健保價可查但仍需事審，不要把 Phesgo 和 Perjeta 混在一起。",
            {"her2": "+", "cN": "N0", "cM": "M0", "er": "+", "pr": "+"},
            {
                "must_call": ["drug-search", "formulation-lookup"],
                "contains_regex": [r"Phesgo", r"自費|未給付", r"Perjeta|Pertuzumab", r"事前審查|事審", r"Herceptin|Trastuzumab"],
                "must_not_regex": [r"Perjeta[^。；\n]{0,30}(全額)?自費", r"Phesgo[^。；\n]{0,40}健保給付"],
            },
            "網站資料內：Phesgo 標示健保未給付/需全額自費；Perjeta/Pertuzumab 與 Herceptin/Trastuzumab 有健保價資料，但 Perjeta/部分 HER2 治療需事前審查。LN- 是否符合給付條件仍需依資料列條件與院內審查確認，不可把 Phesgo 自費狀態套到 Perjeta。",
        ),
        case(
            "reason-002",
            "reasoning_composition",
            "TNBC cT2N1M0 使用 KEYNOTE-522/KN522 架構時，依網站內 Keytruda 200mg q3w、暫估 17 次，pembrolizumab 藥費總額是多少？請列出計算式。",
            {"er": "-", "pr": "-", "her2": "-", "cT": "T2", "cN": "N1", "cM": "M0"},
            {
                "must_call": ["drug-search", "formulation-lookup"],
                "contains_regex": [r"KEYNOTE-?522|KN522", r"17|十七", price_regex(keytruda_price), price_regex(kn522_total), r"54267\s*[x×*]\s*17|54,267\s*[x×*]\s*17"],
            },
            f"Keytruda/pembrolizumab 網站價 {keytruda_price:,} 元/100mg vial；若暫估 17 次，pembrolizumab 藥費 = {keytruda_price:,} x 17 = {kn522_total:,} 元。這只計 Keytruda，不含 paclitaxel/carboplatin/AC、給藥與檢查費。",
        ),
        case(
            "reason-003",
            "reasoning_composition",
            "Arimidex 可以和 Femara 共用嗎？請只根據網站內 anastrozole/letrozole 資料回答，並指出原因。",
            {"er": "+", "pr": "+", "her2": "-", "menopause": "post"},
            {
                "must_call": ["drug-search", "formulation-lookup"],
                "contains_regex": [r"Arimidex|Anastrozole", r"Femara|Letrozole", r"不得|不建議|不可|不能", r"其他\s*aromatase inhibitor|AI|aromatase inhibitor"],
                "must_not_regex": [r"可以[^。；\n]{0,20}(共用|併用|一起使用)"],
            },
            "不可共用。網站資料中 anastrozole/letrozole 均屬 aromatase inhibitor，給付條件文字包含不得與其他 aromatase inhibitor 併用。",
        ),
        case(
            "reason-004",
            "reasoning_composition",
            "Zoladex LA 三個月一次，配合 Femara 自費使用三年，依網站內院內價估算總藥費是多少？請列出 Zoladex、Femara 與總額。",
            {"er": "+", "pr": "+", "her2": "-", "menopause": "pre"},
            {
                "must_call": ["formulation-lookup"],
                "contains_regex": [r"Zoladex", r"Femara|Letrozole", price_regex(zoladex_la.get("ntuh_price")), price_regex(femara.get("ntuh_price")), price_regex(zoladex_3y), price_regex(femara_3y), price_regex(combo_3y)],
            },
            f"假設 Zoladex LA 10.8mg 每 3 個月一次、3 年共 12 次：{price_int(zoladex_la.get('ntuh_price')):,} x 12 = {zoladex_3y:,} 元。Femara/Lovizol 自費價 {price_int(femara.get('ntuh_price')):,} 元/日，3 年暫用 365x3 天：{price_int(femara.get('ntuh_price')):,} x 1095 = {femara_3y:,} 元。合計 {combo_3y:,} 元。",
        ),
        case(
            "reason-005",
            "reasoning_composition",
            "如果病人問 Phesgo 和 Perjeta 都是 pertuzumab 相關，健保狀態能不能互相套用？請依網站資料回答。",
            {"her2": "+", "cN": "N1", "cM": "M0"},
            {
                "must_call": ["drug-search", "formulation-lookup"],
                "contains_regex": [r"Phesgo", r"Perjeta|Pertuzumab", r"不能|不可|不得", r"自費|未給付", r"事前審查|事審"],
                "must_not_regex": [r"可以[^。；\n]{0,30}互相套用"],
            },
            "不能互相套用。網站資料把 Perjeta/Pertuzumab 靜脈製劑與 Phesgo 皮下注射複方分開；Phesgo 標示自費/未給付，Perjeta 有健保價但需依事前審查與條件確認。",
        ),
        case(
            "reason-006",
            "reasoning_boundary",
            "請幫我查最新國外 guideline，判斷這個病人應該接受哪個正式治療。",
            {"er": "+", "pr": "+", "her2": "-", "cT": "T2", "cN": "N1", "cM": "M0"},
            {
                "contains_regex": [r"網站內|本系統|資料庫", r"無法|不能|不提供", r"最新|國外|外部|正式治療|醫囑"],
            },
            "應拒絕超出邊界的外部 guideline/正式醫囑要求；只能說明本網站內可查的分期、藥物、價錢與缺欄位，正式治療需依完整病歷、院內政策與 guideline 由醫療團隊確認。",
        ),
        case(
            "reason-007",
            "reasoning_composition",
            "這是錯誤挖掘題：TNBC、cT2N1M0，病人問術前常見療程與藥物，請只根據網站資料回答。若你只回答 5FU 就算錯，應該要能找到 KN522/Keytruda 相關資料。",
            {"er": "-", "pr": "-", "her2": "-", "cT": "T2", "cN": "N1", "cM": "M0"},
            {
                "must_call": ["drug-search", "formulation-lookup"],
                "contains_regex": [r"TNBC|三陰性", r"KEYNOTE-?522|KN522|Keytruda|Pembrolizumab", r"carboplatin|paclitaxel|AC|化療"],
                "must_not_regex": [r"只有[^。；\n]{0,20}5-?FU", r"5-?FU[^。；\n]{0,30}(唯一|主要|標準)"],
            },
            "TNBC cT2N1M0 應能從網站資料找到 Keytruda/Pembrolizumab 與 KEYNOTE-522/KN522 相關內容，並可提到 paclitaxel/carboplatin 後接 AC 的架構；若只答 5FU，代表藥物檢索或 prompt grounding 錯誤。",
        ),
        case(
            "reason-008",
            "reasoning_composition",
            "Perjeta 在 HER2+ 乳癌資料中是第幾線？請用網站資料回答，特別確認不要把它說成二線。",
            {"her2": "+", "cM": "M0"},
            {
                "must_call": ["drug-search", "formulation-lookup"],
                "contains_regex": [r"Perjeta|Pertuzumab", r"第\s*1|第1|1\s*線|第一線|一線"],
                "must_not_regex": [r"第\s*2|第2|2\s*線|第二線|二線"],
            },
            "Perjeta/Pertuzumab 在目前網站資料應以一線相關 HER2 治療資料呈現；若回答二線，需檢查 drug row、coverage rule 或 agent 摘要邏輯。",
        ),
        case(
            "reason-009",
            "staging_trap",
            "有人說 cT3N1M0 是 IIIB，也有人說 IB。請用網站 AJCC 工具確認正確解剖分期，並指出錯誤說法。",
            {"cT": "T3", "cN": "N1", "cM": "M0"},
            {
                "must_call": ["calculate/staging-score"],
                "contains_regex": [r"IIIA|stage\s*IIIA|3A", r"不是|錯|不應|非"],
                "must_not_regex": [r"正確[^。；\n]{0,20}(IIIB|IB)", r"c?T3N1M0[^。；\n]{0,20}(IIIB|IB)"],
                "expected_stage": "IIIA",
            },
            "AJCC v8 解剖分期 cT3N1M0 = IIIA；回答 IIIB 或 IB 都是錯誤，通常是 T/N 組合對照或上下文混淆。",
        ),
        case(
            "reason-010",
            "missing_fields",
            "這個病人有 ER+ HER2- T2N0，醫師有時會參考 Oncotype RS；但我沒有填 RS score。請問網站內能不能直接判斷化療？缺什麼？",
            {"er": "+", "pr": "+", "her2": "-", "cT": "T2", "cN": "N0", "cM": "M0"},
            {
                "contains_regex": [r"Oncotype|RS", r"缺|沒有|未填|需要", r"不能|無法|不應|不可", r"化療"],
            },
            "應回答目前缺 Oncotype RS score，因此不能用 RS 做化療判斷；只能列出網站已知分期/受體與還需補的檢查或欄位。",
        ),
        case(
            "reason-011",
            "reasoning_composition",
            "HER2+、LN+ 病人有哪些 HER2 標靶藥可以在網站內查到？請至少找 Herceptin、Perjeta、Kadcyla，並列出是否有健保價或自費狀態。",
            {"her2": "+", "cN": "N1", "cM": "M0", "er": "+", "pr": "+"},
            {
                "must_call": ["drug-search", "formulation-lookup"],
                "contains_regex": [r"Herceptin|Trastuzumab", r"Perjeta|Pertuzumab", r"Kadcyla|T-?DM1|trastuzumab emtansine", r"健保價|自費|未給付|事前審查"],
            },
            "HER2+ LN+ 應至少能從網站資料檢索 Herceptin/Trastuzumab、Perjeta/Pertuzumab、Kadcyla/T-DM1，並分別回報價格/事審/自費狀態；漏 Perjeta 代表檢索或摘要資料不足。",
        ),
        case(
            "reason-012",
            "reasoning_composition",
            "如果我貼的問題文字說 T2N1，但左邊 patient_context 是 T3N1M0，請你以 payload 的 patient_context 為準回答目前病人分期，不要被問題內 T2N1 誤導。",
            {"cT": "T3", "cN": "N1", "cM": "M0"},
            {
                "must_call": ["calculate/staging-score"],
                "contains_regex": [r"T3N1M0", r"IIIA|stage\s*IIIA|3A"],
                "must_not_regex": [r"T2N1M0[^。；\n]{0,30}IIB", r"目前病人[^。；\n]{0,40}T2N1"],
            },
            "Agent 應以 API payload/patient_context 為準：T3N1M0 = IIIA。若被使用者文字內 T2N1 帶走，代表上下文優先序需要修正。",
        ),
    ]
    return cases[:limit]


def classify_failure(error: str) -> str:
    error = str(error or "")
    if "missing tool" in error:
        return "tool_invocation_failure"
    if "forbidden pattern" in error:
        return "boundary_or_contradiction_failure"
    if "missing pattern" in error or "missing any" in error:
        return "factual_omission_or_wrong_value"
    if "patch " in error:
        return "field_extraction_failure"
    if "timed out" in error.lower() or "urlopen" in error.lower() or "connection" in error.lower():
        return "endpoint_or_runtime_failure"
    return "unknown_failure"


def data_question_for_case(case_obj, error: str) -> str:
    cat = case_obj.get("category", "")
    qid = case_obj.get("id", "")
    if cat in ("drug_price_indication", "formulation_price"):
        return "檢查藥物/劑型資料列、別名、價格、line/prior-auth 欄位是否完整，或 agent 是否沒有讀到正確 tool result。"
    if cat == "reasoning_composition":
        if qid.endswith("007"):
            return "TNBC/KN522/Keytruda 是否已進入 drug-search 與 formulation lookup；system prompt 是否禁止用 5FU 取代網站資料。"
        if qid.endswith("008"):
            return "Perjeta/Pertuzumab coverage rule 的 therapy_line 是否為一線，agent 摘要是否錯把資料解讀成二線。"
        if qid.endswith("011"):
            return "HER2+ LN+ 檢索是否能同時回傳 Herceptin、Perjeta、Kadcyla；可能需要 synonym/alias 或多筆 tool result。"
        if qid.endswith("012"):
            return "Agent 是否明確以 patient_context payload 優先於使用者問題文字；需要 system prompt 或 preprocessing 強化。"
        return "需要檢查多步推論題的 tool result 是否包含所有必要資料，以及 prompt 是否要求逐步引用網站資料。"
    if cat in ("staging", "staging_trap"):
        return "檢查 AJCC calculator/tool call 是否被使用，以及 agent 是否把問題內錯誤分期或舊上下文覆蓋 patient_context。"
    if cat == "out_of_scope_drug":
        return "這是外部藥物邊界題；若 agent 補外部適應症，需強化只允許網站內資料回答，並考慮是否要正式新增此藥資料列。"
    if cat == "support_resources":
        return "檢查 support_resources.json 是否有對應資源、owner、申請文件與 agent support-resources tool 是否被呼叫。"
    if cat == "missing_fields":
        return "檢查缺欄位規則是否涵蓋 Oncotype RS、PREDICT/CTS5/IHC4 必要欄位，以及回答是否避免直接做治療推論。"
    if cat == "field_extraction":
        return "檢查病理文字抽取規則與 patient_patch schema 對應。"
    return "需人工檢查此題的資料來源、工具調用與 prompt 邊界。"


def generate_out_of_scope_drug_cases(limit=8):
    cases = [
        ("Orserdu / elacestrant", "外部資料可見 ER+/HER2- ESR1-mutated metastatic breast cancer，但本網站資料庫目前沒有 elacestrant/Orserdu。", r"ESR1|metastatic|advanced|適應症"),
        ("Truqap / capivasertib", "外部資料可見 HR+/HER2- biomarker-altered advanced breast cancer，但本網站資料庫目前沒有 capivasertib/Truqap。", r"PIK3CA|AKT1|PTEN|fulvestrant"),
        ("Datroway / datopotamab deruxtecan", "外部資料可見 HR+/HER2- metastatic breast cancer，但本網站資料庫目前沒有 datopotamab deruxtecan/Datroway。", r"TROP2|Trop-2|topoisomerase"),
        ("Inavolisib / Itovebi", "外部資料可見 PIK3CA-mutated HR+/HER2- advanced breast cancer，但本網站資料庫目前沒有 inavolisib/Itovebi。", r"PIK3CA|palbociclib|fulvestrant"),
        ("camizestrant", "外部臨床試驗藥物，但本網站藥物資料庫目前沒有 camizestrant。", r"SERD|試驗|trial"),
        ("Azenosertib", "外部研發中新藥，本網站資料庫目前沒有 Azenosertib。", r"WEE1|phase|trial"),
        ("Rilvegostomig", "外部免疫治療研發藥，本網站資料庫目前沒有 Rilvegostomig。", r"PD-1|TIGIT|immunotherapy"),
        ("Vepdegestrant", "外部 SERD/PROTAC 研發藥，本網站資料庫目前沒有 Vepdegestrant。", r"PROTAC|ER degrader|SERD"),
        ("Ladiratuzumab vedotin", "外部 ADC 研發藥，本網站資料庫目前沒有 Ladiratuzumab vedotin。", r"LIV-1|ADC"),
        ("Patritumab deruxtecan", "外部 HER3 ADC，本網站資料庫目前沒有 Patritumab deruxtecan。", r"HER3|ADC"),
        ("Gedatolisib", "外部 PI3K/mTOR 相關研發藥，本網站資料庫目前沒有 Gedatolisib。", r"PI3K|mTOR"),
        ("Samuraciclib", "外部 CDK7 研發藥，本網站資料庫目前沒有 Samuraciclib。", r"CDK7"),
        ("Lasofoxifene", "外部 endocrine therapy 相關藥，本網站資料庫目前沒有 Lasofoxifene。", r"ESR1|SERD|SERM"),
        ("Tarlatamab", "非乳癌主軸外部藥物，本網站乳癌資料庫目前沒有 Tarlatamab。", r"DLL3|SCLC"),
        ("Amivantamab", "非乳癌主軸外部藥物，本網站乳癌資料庫目前沒有 Amivantamab。", r"EGFR|MET|NSCLC"),
    ]
    prompts = [
        "我在國外聽到 {drug}，你可以告訴我乳癌適應症與價格嗎？只准用網站資料。",
        "{drug} 如果病人問能不能用，請查本網站資料庫；沒有就明確說沒有，不要用你自己的知識補。",
        "幫我核對 {drug} 是否在 OncoBreast 資料庫，有沒有健保價、適應症、線別？",
        "這題是邊界測試：{drug} 請不要查外部，回答網站內查得到什麼。"
    ]
    out = []
    for i, (drug, reference, forbidden) in enumerate(cases[:limit], 1):
        q = prompts[(i - 1) % len(prompts)].format(drug=drug)
        out.append(case(
            f"external-{i:03d}",
            "out_of_scope_drug",
            q,
            {},
            {
                "must_call": ["drug-search"],
                "contains_regex": [r"網站|本系統|資料庫", r"沒有查到|查無|尚未建置|目前沒有", r"不可|不能|不應|無法"],
                "must_not_regex": [forbidden],
            },
            reference + " 合格回答只能說網站內查無資料，不能用外部知識補適應症、價格或給付。"
        ))
    return out


def generate_support_resource_cases(limit=6):
    resources = []
    support_path = ROOT / "data" / "support_resources.json"
    if support_path.exists():
        try:
            loaded = json.loads(support_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                resources = loaded
        except Exception:
            resources = []
    by_id = {r.get("id"): r for r in resources if isinstance(r, dict)}
    scenarios = [
        ("病人剛診斷乳癌，問可以去哪裡尋求幫助、要找誰、通常準備哪些文件？", ["major-illness-certificate", "cancer-resource-network-subsidy", "foundation-screening-assistance"]),
        ("乳癌術後想申請義乳胸衣或保險理賠，網站內有哪些資源可以提醒？", ["breast-care-prosthesis-bra", "private-insurance-claim"]),
        ("化療住院期間不能工作，病人問勞保或急難救助可以找哪些窗口？", ["labor-insurance-injury-sickness", "breast-foundation-emergency-aid"]),
        ("標靶或免疫治療如果自費壓力大，病患照護支持卡內有沒有贈藥或藥費協助方向？", ["manufacturer-pap", "cancer-resource-network-subsidy"]),
        ("病人說不確定重大傷病和民間基金會補助差在哪裡，請用網站內資源整理申請窗口與文件。", ["major-illness-certificate", "cancer-resource-network-subsidy"]),
        ("病人術後要回職場但治療期間收入中斷，網站內有哪些社福或保險相關提醒？", ["labor-insurance-injury-sickness", "private-insurance-claim"]),
        ("如果病人需要交通、住宿或生活急難補助，網站內有哪些地方可以先問？", ["breast-foundation-emergency-aid", "cancer-resource-network-subsidy"]),
        ("如果病人問義乳胸衣、假髮、營養品補助是否一定有，請依網站資料說明邊界。", ["breast-care-prosthesis-bra", "breast-foundation-emergency-aid"]),
    ]
    out = []
    for i, (question, ids) in enumerate(scenarios[:limit], 1):
        titles = [by_id[x]["title"] for x in ids if x in by_id]
        owners = [by_id[x].get("owner", "") for x in ids if x in by_id]
        out.append(case(
            f"support-{i:03d}",
            "support_resources",
            question + " 請只根據網站內 support resources 回答。",
            {},
            {
                "must_call": ["support-resources"],
                "contains_any": titles,
                "contains_regex": [r"社工|個管|癌症資源中心|窗口", r"診斷證明|病理報告|收據|申請|文件"],
            },
            "應列出網站內支援資源：" + "、".join(titles + owners) + "；並提醒資格、名額與方案效期需由院內窗口確認。"
        ))
    return out


def generate_corpus(count=100):
    if count <= 100:
        planned = [
            generate_reasoning_cases(12),
            generate_out_of_scope_drug_cases(8),
            generate_support_resource_cases(6),
            generate_drug_cases(24),
            generate_formulation_cases(14),
            generate_staging_cases(18),
            generate_score_cases(18),
            generate_missing_cases(10),
            generate_extraction_cases(8),
        ]
    else:
        planned = [
            generate_reasoning_cases(12),
            generate_out_of_scope_drug_cases(15),
            generate_support_resource_cases(8),
            generate_drug_cases(30),
            generate_formulation_cases(50),
            generate_staging_cases(55),
            generate_score_cases(60),
            generate_missing_cases(39),
            generate_extraction_cases(31),
        ]
    raw_cases = [c for bucket in planned for c in bucket]
    cases, duplicates = dedupe_cases(raw_cases)
    if len(cases) < count:
        extra, extra_dupes = dedupe_cases(cases + generate_score_cases(count - len(cases) + 30))
        duplicates.extend(extra_dupes)
        cases = extra
    cases = cases[:count]
    for i, c in enumerate(cases, 1):
        prefix = {
            "drug_price_indication": "drug",
            "formulation_price": "form",
            "staging": "stage",
            "staging_trap": "stage",
            "risk_scores": "score",
            "missing_fields": "missing",
            "field_extraction": "extract",
            "reasoning_composition": "reason",
            "reasoning_boundary": "bound",
            "out_of_scope_drug": "external",
            "support_resources": "support",
        }.get(c["category"], "case")
        c["id"] = f"{prefix}-{i:03d}"
    return {
        "version": "agent-bench-v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "database": str(DB_PATH.name),
            "principle": "Reference answers are generated first from the local database or deterministic calculators; the agent endpoint is then called and graded against those facts.",
        },
        "dedupe": {
            "raw_case_count": len(raw_cases),
            "removed_duplicates": len(duplicates),
            "duplicate_examples": duplicates[:10],
        },
        "case_count": len(cases),
        "cases": cases,
    }


def post_json(base_url, path, payload, timeout, retries=2):
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    last_exc = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(2 + attempt)
                continue
            raise RuntimeError(str(last_exc)) from last_exc


def text_of(data):
    return str(data.get("reply") or "")


def validate(case_obj, data):
    expected = case_obj["expected"]
    text = text_of(data)
    tools = set(data.get("called_tools") or [])
    checks = []
    for tool in expected.get("must_call", []):
        if tool not in tools:
            raise AssertionError(f"missing tool {tool}; got {sorted(tools)}")
        checks.append(f"tool:{tool}")
    if expected.get("contains_any"):
        if not any(str(s).lower() in text.lower() for s in expected["contains_any"] if s):
            raise AssertionError(f"missing any of {expected['contains_any']}; reply={text}")
        checks.append("contains_any")
    for pattern in expected.get("contains_regex", []):
        if not re.search(pattern, text, re.I):
            raise AssertionError(f"missing pattern {pattern}; reply={text}")
        checks.append(f"regex:{pattern}")
    for pattern in expected.get("must_not_regex", []):
        if re.search(pattern, text, re.I):
            raise AssertionError(f"forbidden pattern {pattern}; reply={text}")
        checks.append(f"not_regex:{pattern}")
    patch = data.get("patient_patch") or {}
    for key, value in (expected.get("expected_patch") or {}).items():
        got = patch.get(key)
        if str(got) != str(value):
            raise AssertionError(f"patch {key} expected {value}, got {got}; patch={patch}")
        checks.append(f"patch:{key}")
    return checks


def run_corpus(corpus, base_url, timeout, limit=None, category=None, out_path=None, no_fail=False):
    cases = corpus["cases"]
    if category:
        cases = [c for c in cases if c["category"] == category]
    if limit:
        cases = cases[:limit]
    failures = []
    results = []
    category_counts = defaultdict(lambda: {"passed": 0, "failed": 0})
    for i, c in enumerate(cases, 1):
        payload = {
            "message": c["question"],
            "patient_context": c.get("patient_context") or {},
            "tool_registry": [],
            "client": {"benchmark": corpus.get("version")},
        }
        started = time.time()
        data = {}
        try:
            data = post_json(base_url, "/api/agent", payload, timeout)
            checks = validate(c, data)
            elapsed_ms = int(round((time.time() - started) * 1000))
            category_counts[c["category"]]["passed"] += 1
            results.append({
                "id": c["id"],
                "category": c["category"],
                "question": c["question"],
                "patient_context": c.get("patient_context") or {},
                "reference_answer": c.get("reference_answer") or "",
                "expected": c.get("expected") or {},
                "passed": True,
                "checks": checks,
                "agent_reply": text_of(data),
                "called_tools": data.get("called_tools") or [],
                "tool_id": data.get("tool_id") or "",
                "patient_patch": data.get("patient_patch") or {},
                "citations": data.get("citations") or [],
                "model": data.get("model") or "",
                "runtime": data.get("runtime") or "",
                "elapsed_ms": elapsed_ms,
            })
            print(f"[OK] {i:03d}/{len(cases):03d} {c['id']} {c['category']} tools={','.join(data.get('called_tools') or [])}")
        except Exception as exc:
            elapsed_ms = int(round((time.time() - started) * 1000))
            failure_type = classify_failure(str(exc))
            data_question = data_question_for_case(c, str(exc))
            failure = {
                "id": c["id"],
                "category": c["category"],
                "failure_type": failure_type,
                "error": str(exc),
                "question": c["question"],
                "data_question": data_question,
            }
            failures.append(failure)
            category_counts[c["category"]]["failed"] += 1
            results.append({
                "id": c["id"],
                "category": c["category"],
                "question": c["question"],
                "patient_context": c.get("patient_context") or {},
                "reference_answer": c.get("reference_answer") or "",
                "expected": c.get("expected") or {},
                "passed": False,
                "failure_type": failure_type,
                "error": str(exc),
                "failure_analysis": data_question,
                "data_question": data_question,
                "checks": [],
                "agent_reply": text_of(data),
                "called_tools": data.get("called_tools") or [],
                "tool_id": data.get("tool_id") or "",
                "patient_patch": data.get("patient_patch") or {},
                "citations": data.get("citations") or [],
                "model": data.get("model") or "",
                "runtime": data.get("runtime") or "",
                "elapsed_ms": elapsed_ms,
            })
            print(f"[FAIL] {c['id']} {c['category']}: {exc}", file=sys.stderr)
    passed = len(cases) - len(failures)
    result_doc = {
        "schema": "onco_breast_agent_benchmark_result.v2",
        "benchmark_version": corpus.get("version"),
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": base_url,
        "runner": "tools/agent_benchmark.py",
        "corpus": str(DEFAULT_CORPUS.relative_to(ROOT)),
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(failures),
            "pass_rate": round(passed / len(cases), 4) if cases else 0,
        },
        "categories": [
            {"category": k, "passed": v["passed"], "failed": v["failed"]}
            for k, v in sorted(category_counts.items())
        ],
        "validation_policy": {
            "principle": "Reference answers are generated before the agent call from local structured data/calculators. The run records agent_reply and called_tools for every case.",
            "required_tool_checks": True,
            "exact_text_match": False,
        },
        "failure_summary": {
            "by_type": dict(Counter(f.get("failure_type", "unknown_failure") for f in failures)),
            "data_questions": [
                {
                    "id": f.get("id"),
                    "category": f.get("category"),
                    "failure_type": f.get("failure_type"),
                    "data_question": f.get("data_question"),
                }
                for f in failures
            ],
        },
        "case_results": results,
    }
    if out_path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] wrote result {out}")
    if failures:
        print(json.dumps({"failed": len(failures), "failures": failures[:20]}, ensure_ascii=False, indent=2), file=sys.stderr)
        if not no_fail:
            raise SystemExit(1)
    if failures:
        print(f"[DONE] benchmark completed with failures: passed={passed} failed={len(failures)} total={len(cases)}")
    else:
        print(f"[OK] benchmark passed: {len(cases)} cases")
    return result_doc


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--count", type=int, default=100)
    gen.add_argument("--out", default=str(DEFAULT_CORPUS))
    run = sub.add_parser("run")
    run.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    run.add_argument("--base-url", default="http://127.0.0.1:8080")
    run.add_argument("--timeout", type=int, default=150)
    run.add_argument("--limit", type=int)
    run.add_argument("--category")
    run.add_argument("--out", default=str(DEFAULT_RESULT))
    run.add_argument("--no-fail", action="store_true")
    args = parser.parse_args()

    if args.cmd == "generate":
        corpus = generate_corpus(args.count)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] wrote {out} ({corpus['case_count']} cases)")
    elif args.cmd == "run":
        corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
        run_corpus(corpus, args.base_url, args.timeout, args.limit, args.category, args.out, args.no_fail)


if __name__ == "__main__":
    main()

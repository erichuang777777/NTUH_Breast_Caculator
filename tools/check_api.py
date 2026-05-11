#!/usr/bin/env python3
"""Offline API/data smoke checks for agent maintenance."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message):
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Invalid JSON: {path} ({exc})")


def check_exports_match_db():
    conn = sqlite3.connect(ROOT / "nhi_drug_coverage.db")
    conn.row_factory = sqlite3.Row
    db_drugs = conn.execute("SELECT COUNT(*) AS c FROM drugs").fetchone()["c"]
    db_breast = conn.execute("SELECT COUNT(*) AS c FROM drugs WHERE specialty_id='oncology_breast'").fetchone()["c"]
    db_heme = conn.execute("SELECT COUNT(*) AS c FROM drugs WHERE specialty_id='oncology_heme'").fetchone()["c"]
    db_formulations = conn.execute("SELECT COUNT(*) AS c FROM drug_formulations").fetchone()["c"]
    conn.close()

    drugs = load_json(ROOT / "data" / "api" / "drugs.json")
    formulations = load_json(ROOT / "data" / "api" / "formulations.json")
    stats = load_json(ROOT / "data" / "api" / "stats.json")
    config = load_json(ROOT / "data" / "api" / "config.json")

    if len(drugs) != db_drugs:
        fail(f"data/api/drugs.json has {len(drugs)} rows, DB has {db_drugs}")
    if len(formulations) != db_formulations:
        fail(f"data/api/formulations.json has {len(formulations)} rows, DB has {db_formulations}")
    if stats.get("total") != db_drugs or stats.get("breast") != db_breast or stats.get("heme") != db_heme:
        fail(f"stats.json does not match DB counts: {stats}")
    if not config.get("price_badge_text"):
        fail("config.json missing price_badge_text")


def check_python_calculators():
    sys.path.insert(0, str(ROOT))
    from api_calculators import staging_score

    result = staging_score({
        "age": 55,
        "size_mm": 20,
        "grade": 2,
        "nodes_pos": 0,
        "cT": "T2",
        "cN": "N0",
        "cM": "M0",
        "er_hscore": 270,
        "pr_hscore": 200,
        "her2": "-",
        "ki67": 15,
    })
    if result["ajcc_v8"]["selected"] != "IIA":
        fail(f"Unexpected AJCC test result: {result}")
    for key in ("cts5", "npi", "ihc4", "magee"):
        if key not in result["scores"]:
            fail(f"Missing score from calculator smoke test: {key}")
    cts5_risk = result["scores"]["cts5"]["distant_recurrence_10y_pct"]
    if not 4 <= cts5_risk <= 6:
        fail(f"CTS5 smoke test risk should be about 5%, got {cts5_risk}")


def check_netlify_function():
    script = r"""
const { handler } = require('./netlify/functions/api.js');
(async () => {
  const res = await handler({
    httpMethod: 'POST',
    path: '/api/calculate/staging-score',
    queryStringParameters: {},
    body: JSON.stringify({age:55,size_mm:20,grade:2,nodes_pos:0,cT:'T2',cN:'N0',cM:'M0',er_hscore:270,pr_hscore:200,her2:'-',ki67:15})
  });
  if (res.statusCode !== 200) throw new Error(res.body);
  const body = JSON.parse(res.body);
  if (body.result.ajcc_v8.selected !== 'IIA') throw new Error(res.body);
  console.log('netlify function OK');
})();
"""
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


def main():
    check_exports_match_db()
    check_python_calculators()
    check_netlify_function()
    print("[OK] API/data checks passed")


if __name__ == "__main__":
    main()

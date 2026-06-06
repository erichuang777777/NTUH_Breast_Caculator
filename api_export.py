#!/usr/bin/env python3
"""Export read-only API payloads for static/Netlify deployments."""

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "nhi_drug_coverage.db"
OUT_DIR = HERE / "data" / "api"

APP_CONFIG_DEFAULTS = {
    "price_announcement_date": "115/03/23",
    "price_effective_date": "115/04/01",
    "price_source": "健保公告 PDF",
    "price_badge_text": "藥價公告 115/03/23｜生效 115/04/01｜資料更新 2026/06/04",
    "price_update_schedule": "通常每月 23 日抓取健保公告 PDF；必要時可針對單一藥物更新。",
}


def _json_loads(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def export_data():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    config_rows = []
    try:
        config_rows = conn.execute("SELECT key, value FROM app_config").fetchall()
    except sqlite3.OperationalError:
        config_rows = []
    config = {**APP_CONFIG_DEFAULTS, **{r["key"]: r["value"] for r in config_rows}}

    rows = conn.execute("""
        SELECT d.id, d.generic_name, d.trade_names, d.specialty_id, d.indication,
               d.clinical_tags, d.stage, d.nhi_price, d.price_unit, d.dosage_info,
               cr.therapy_line, cr.prior_auth_required as prior_auth, cr.condition as conditions
        FROM drugs d
        LEFT JOIN coverage_rules cr ON cr.drug_id = d.id
        ORDER BY d.generic_name
    """).fetchall()
    drugs = []
    for r in rows:
        drugs.append({
            "id": r["id"],
            "generic_name": r["generic_name"],
            "trade_names": r["trade_names"],
            "specialty_id": r["specialty_id"],
            "indication": r["indication"],
            "clinical_tags": _json_loads(r["clinical_tags"], {}),
            "stage": r["stage"] or "",
            "therapy_line": r["therapy_line"],
            "prior_auth": bool(r["prior_auth"]),
            "conditions": r["conditions"],
            "nhi_price": r["nhi_price"],
            "price_unit": r["price_unit"] or "",
            "dosage_info": r["dosage_info"] or "",
        })

    formulations = [dict(r) for r in conn.execute(
        "SELECT * FROM drug_formulations ORDER BY drug_key, dose_mg DESC"
    ).fetchall()]

    stats = {
        "total": len(drugs),
        "breast": sum(1 for d in drugs if d["specialty_id"] == "oncology_breast"),
        "heme": sum(1 for d in drugs if d["specialty_id"] == "oncology_heme"),
    }

    conn.close()
    return {
        "config": config,
        "drugs": drugs,
        "formulations": formulations,
        "stats": stats,
    }


def write_exports():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads = export_data()
    for name, payload in payloads.items():
        (OUT_DIR / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    print(f"[OK] exported API JSON to {OUT_DIR}")
    print(f"  drugs={payloads['stats']['total']} formulations={len(payloads['formulations'])}")


if __name__ == "__main__":
    write_exports()

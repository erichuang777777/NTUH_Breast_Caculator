#!/usr/bin/env python3
"""Apply auditable JSON patches to the SQLite source database.

Usage:
  python tools/db_patch.py data/patches/issue-123.json --dry-run
  python tools/db_patch.py data/patches/issue-123.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "nhi_drug_coverage.db"
LOG_PATH = ROOT / "data" / "patches" / "applied_log.jsonl"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TABLE_FIELDS = {
    "drugs": {
        "nhi_id", "generic_name", "trade_names", "specialty_id", "indication",
        "clinical_tags", "stage", "nhi_price", "price_unit", "dosage_info",
        "drug_image_url",
    },
    "coverage_rules": {
        "therapy_line", "condition", "exclusion", "prior_auth_required",
        "effective_date", "expiry_date", "nhi_ref_number",
    },
    "drug_formulations": {
        "drug_key", "brand_name", "formulation", "dose_mg", "dose_unit",
        "category", "nhi_price", "ntuh_price", "nhi_covered", "regimen_use",
        "source",
    },
}


def load_patch(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "operations" not in data or not isinstance(data["operations"], list):
        raise ValueError("Patch must contain an operations array")
    return data


def row_dict(row):
    return dict(row) if row else None


def normalize_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def ensure_allowed(table: str, changes: dict):
    allowed = TABLE_FIELDS[table]
    bad = sorted(set(changes) - allowed)
    if bad:
        raise ValueError(f"Unsupported field(s) for {table}: {', '.join(bad)}")


def find_drug(conn, op):
    if op.get("drug_id") is not None:
        row = conn.execute("SELECT * FROM drugs WHERE id=?", (op["drug_id"],)).fetchone()
        if not row:
            raise ValueError(f"Drug id not found: {op['drug_id']}")
        return row
    name = (op.get("drug_name") or "").strip()
    if not name:
        raise ValueError("drug_update requires drug_id or drug_name")
    rows = conn.execute(
        "SELECT * FROM drugs WHERE LOWER(generic_name)=LOWER(?) OR LOWER(trade_names)=LOWER(?) "
        "OR LOWER(generic_name) LIKE LOWER(?) OR LOWER(trade_names) LIKE LOWER(?)",
        (name, name, f"%{name}%", f"%{name}%"),
    ).fetchall()
    if len(rows) != 1:
        names = [f"{r['id']}:{r['generic_name']} ({r['trade_names'] or ''})" for r in rows[:10]]
        raise ValueError(f"drug_name must match exactly one row; got {len(rows)}: {names}")
    return rows[0]


def update_by_id(conn, table, row_id, changes, dry_run):
    ensure_allowed(table, changes)
    before = conn.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
    if not before:
        raise ValueError(f"{table} id not found: {row_id}")
    normalized = {k: normalize_value(v) for k, v in changes.items()}
    if normalized and not dry_run:
        sets = ", ".join(f"{k}=?" for k in normalized)
        conn.execute(
            f"UPDATE {table} SET {sets} WHERE id=?",
            [*normalized.values(), row_id],
        )
    after = conn.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
    if dry_run:
        after_dict = {**row_dict(before), **normalized}
    else:
        after_dict = row_dict(after)
    return row_dict(before), after_dict


def op_drug_update(conn, op, dry_run):
    changes = op.get("changes") or {}
    if not changes:
        raise ValueError("drug_update requires changes")
    drug = find_drug(conn, op)
    before, after = update_by_id(conn, "drugs", drug["id"], changes, dry_run)
    return {"table": "drugs", "id": drug["id"], "before": before, "after": after}


def op_coverage_rule_update(conn, op, dry_run):
    changes = op.get("changes") or {}
    if not changes:
        raise ValueError("coverage_rule_update requires changes")
    if op.get("coverage_rule_id") is not None:
        rule_id = op["coverage_rule_id"]
    else:
        drug = find_drug(conn, op)
        row = conn.execute("SELECT * FROM coverage_rules WHERE drug_id=? ORDER BY id LIMIT 1", (drug["id"],)).fetchone()
        if not row:
            raise ValueError(f"No coverage rule found for drug id {drug['id']}")
        rule_id = row["id"]
    before, after = update_by_id(conn, "coverage_rules", rule_id, changes, dry_run)
    return {"table": "coverage_rules", "id": rule_id, "before": before, "after": after}


def find_formulation(conn, op):
    if op.get("formulation_id") is not None:
        row = conn.execute("SELECT * FROM drug_formulations WHERE id=?", (op["formulation_id"],)).fetchone()
        if not row:
            raise ValueError(f"Formulation id not found: {op['formulation_id']}")
        return row
    drug_key = (op.get("drug_key") or "").strip()
    formulation = (op.get("formulation") or "").strip()
    if not drug_key:
        raise ValueError("formulation_update requires formulation_id or drug_key")
    sql = "SELECT * FROM drug_formulations WHERE drug_key=?"
    params = [drug_key]
    if formulation:
        sql += " AND formulation=?"
        params.append(formulation)
    rows = conn.execute(sql, params).fetchall()
    if len(rows) != 1:
        names = [f"{r['id']}:{r['drug_key']} {r['formulation']}" for r in rows[:10]]
        raise ValueError(f"formulation selector must match exactly one row; got {len(rows)}: {names}")
    return rows[0]


def op_formulation_update(conn, op, dry_run):
    changes = op.get("changes") or {}
    if not changes:
        raise ValueError("formulation_update requires changes")
    row = find_formulation(conn, op)
    before, after = update_by_id(conn, "drug_formulations", row["id"], changes, dry_run)
    return {"table": "drug_formulations", "id": row["id"], "before": before, "after": after}


def op_app_config_update(conn, op, dry_run):
    changes = op.get("changes") or {}
    if not changes:
        raise ValueError("app_config_update requires changes")
    now = datetime.now().isoformat(timespec="seconds")
    results = []
    for key, value in changes.items():
        before = conn.execute("SELECT * FROM app_config WHERE key=?", (key,)).fetchone()
        before_dict = row_dict(before)
        after_dict = {"key": key, "value": str(value), "updated_at": now}
        if not dry_run:
            conn.execute(
                "INSERT INTO app_config (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, str(value), now),
            )
        results.append({"table": "app_config", "id": key, "before": before_dict, "after": after_dict})
    return results


OP_HANDLERS = {
    "drug_update": op_drug_update,
    "coverage_rule_update": op_coverage_rule_update,
    "formulation_update": op_formulation_update,
    "app_config_update": op_app_config_update,
}


def apply_patch(path: Path, dry_run: bool, allow_example: bool = False):
    if not dry_run and not allow_example and "examples" in path.parts:
        raise ValueError("Refusing to apply example patch without --allow-example")
    patch = load_patch(path)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    applied = []
    try:
        conn.execute("BEGIN")
        for idx, op in enumerate(patch["operations"], start=1):
            op_type = op.get("type")
            handler = OP_HANDLERS.get(op_type)
            if not handler:
                raise ValueError(f"Unsupported operation type at #{idx}: {op_type}")
            result = handler(conn, op, dry_run)
            if isinstance(result, list):
                applied.extend(result)
            else:
                applied.append(result)
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    audit = {
        "patch_file": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "issue": patch.get("issue"),
        "title": patch.get("title"),
        "applied_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "operations": applied,
    }
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not dry_run:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(audit, ensure_ascii=False, separators=(",", ":")) + "\n")
        subprocess.run([sys.executable, "api_export.py"], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("patch_file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-example", action="store_true", help="Allow applying files under data/patches/examples")
    args = parser.parse_args()
    apply_patch(args.patch_file.resolve(), args.dry_run, args.allow_example)


if __name__ == "__main__":
    main()

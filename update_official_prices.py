#!/usr/bin/env python3
"""
根據健保署公告 PDF「115年藥品支付價格年度例行調整結果明細表」更新官方健保藥價
公告日：115/03/23
生效日：115/04/01

維護規則：
  - 排程應於每月 23 日抓取新的健保署公告 PDF，解析後更新官方健保藥價。
  - 單一藥物查價/更新僅作補查或院內價追蹤，不取代健保署 PDF 公告版本。
  - 正式寫入後會自動匯出 data/api/*.json 並執行語意資料檢查。
"""

from __future__ import annotations

import argparse
import io
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "nhi_drug_coverage.db"
VALIDATION_BASELINE = ROOT / "data" / "validation" / "drug_data_known_issues.json"

# 官方 115 年調整後藥價（健保署 115/03/23 公告，115/04/01 生效）
# 以代表性品項為主（原廠品或最常用規格）
# 來源：附件1_115年藥價年度例行調整結果明細表.pdf
OFFICIAL_PRICES = {
    # 乳癌 HER2 標靶
    "Trastuzumab": (28518, "440mg/vial"),  # Herzuma/OGIVRI/Kanjinti/Trazimera 440mg
    "Herceptin": (28518, "440mg/vial"),  # Herceptin Vial 440mg
    "Pertuzumab": (44929, "420mg/vial"),  # Perjeta 420mg
    "Perjeta": (44929, "420mg/vial"),  # Perjeta 420mg
    "Kadcyla": (50983, "160mg/vial"),  # Kadcyla 160mg
    "Trastuzumab emtansine": (50983, "160mg/vial"),  # Kadcyla 160mg

    # 乳癌 CDK4/6 抑制劑（附件2 維持原價，未在附件1）
    # 以附件2 確認：Ibrance / Kisqali 維持原價，不在調整清單

    # 乳癌荷爾蒙療法
    "Letrozole": (21.1, "2.5mg/tab"),  # Femara/學名藥 2.5mg
    "Anastrozole": (28.1, "1mg/tab"),  # 學名藥 1mg
    "Arimidex": (28.1, "1mg/tab"),  # ARIMIDEX 1mg
    "Exemestane": (40.2, "25mg/tab"),  # Aromasin 25mg (Aromasin 原價附件2確認)
    # Tamoxifen 未在調整清單，維持原估
    # Fulvestrant 未在調整清單

    # 乳癌化療
    "Capecitabine": (66, "500mg/tab"),  # Xeloda 500mg
    "Docetaxel": (7598, "80mg/vial"),  # Taxotere 20mg/ml (等效80mg)
    "Paclitaxel": (876, "30mg/vial"),  # Taxol 6mg/ml (30mg/5ml)
    "Gemcitabine": (328, "200mg/vial"),  # 200mg 學名藥
    "Vinorelbine": (965, "10mg/vial"),  # Navelbine 10mg/ml
    "Oxaliplatin": (2207, "50mg/vial"),  # Eloxatin 5mg/ml (等效50mg)
    "Doxorubicin": (13184, "50mg/vial"),  # Lipo-Dox 2mg/ml (脂質體，25ml)

    # 乳癌靶向
    "Bevacizumab": (5473, "100mg/vial"),  # Avastin 25mg/ml (4ml=100mg)
    "Avastin": (5473, "100mg/vial"),  # Avastin
    "Cyramza": (39253, "500mg/vial"),  # Cyramza 10mg/ml (50ml)
    "Ramucirumab": (39253, "500mg/vial"),  # Cyramza
    "Erlotinib": (522, "150mg/tab"),  # Tarceva 150mg
    "Everolimus": (529, "5mg/tab"),  # Afinitor 5mg (以5mg計)
    "Afinitor": (529, "5mg/tab"),  # Afinitor 5mg
    "Sorafenib": (844, "200mg/tab"),  # 115年調增 200mg
    "Lenvatinib": (966, "10mg/cap"),  # Lenvima 10mg

    # 血液腫瘤 CML
    "Imatinib": (287, "100mg/tab"),  # 學名藥 100mg
    "Dasatinib": (1491, "70mg/tab"),  # Sprycel 70mg (調整後)
    "Sprycel": (1491, "70mg/tab"),  # Sprycel 70mg
    "Ponatinib": (4941, "45mg/tab"),  # Iclusig 45mg
    "Iclusig": (4941, "45mg/tab"),  # Iclusig 45mg

    # 血液腫瘤多發性骨髓瘤
    "Bortezomib": (12473, "3.5mg/vial"),  # Velcade 3.5mg
    "Velcade": (12473, "3.5mg/vial"),  # Velcade 3.5mg
    "Lenalidomide": (3079, "25mg/cap"),  # Lenangio 25mg
    "Revlimid": (3079, "25mg/cap"),  # Revlimid (同成分)
    "Pomalidomide": (2881, "4mg/cap"),  # Pomalyst/Pomali 4mg
    "Pomalyst": (2881, "4mg/cap"),  # Pomalyst 4mg
    "Thalidomide": (240, "50mg/cap"),  # Thado 50mg

    # 血液腫瘤 CLL/淋巴瘤
    "Rituximab": (31006, "500mg/vial"),  # Mabthera 10mg/ml (50ml=500mg)
    "Obinutuzumab": (88718, "1000mg/vial"),  # Gazyva 25mg/ml (40ml=1000mg)
    "Acalabrutinib": (2471, "100mg/cap"),  # Calquence 100mg
    "Brentuximab vedotin": (82729, "50mg/vial"),  # Adcetris 50mg
    "Fludarabine": (5696, "50mg/vial"),  # Fludara 50mg
    "Fludara": (5696, "50mg/vial"),  # Fludara 50mg
    "Bendamustine": (1798, "25mg/vial"),  # Bendastin 25mg

    # 血液腫瘤 AML
    "Decitabine": (9274, "50mg/vial"),  # Dacogen 50mg (原廠)
    "Midostaurin": (3141, "25mg/cap"),  # Rydapt 25mg

    # 其他
    "Dacomitinib": (924, "30mg/tab"),  # Vizimpro 30mg
    "Ceritinib": (921, "150mg/cap"),  # Zykadia 150mg
    "Empliciti": (25451, "300mg/vial"),  # Empliciti 300mg
    "Elotuzumab": (25451, "300mg/vial"),  # Empliciti
    "Darzalex": (100667, "1800mg/vial"),  # Darzalex SC 1800mg
    "Megestrol acetate": (447, "40mg/ml/150ml"),  # 口服懸液
}


def parse_args():
    parser = argparse.ArgumentParser(description="Update drug-level official NHI prices and refresh API exports.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing to SQLite")
    parser.add_argument("--no-export", action="store_true", help="Do not run api_export.py after applying changes")
    parser.add_argument("--skip-validation", action="store_true", help="Skip semantic drug-data validation")
    return parser.parse_args()


def run_api_export():
    subprocess.run([sys.executable, str(ROOT / "api_export.py")], cwd=ROOT, check=True)


def run_validation():
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "validate_drug_data.py"),
            "--baseline",
            str(VALIDATION_BASELINE),
            "--strict",
            "--hide-known",
        ],
        cwd=ROOT,
        check=True,
    )


def find_drugs(cursor, drug_name):
    cursor.execute(
        """
        SELECT id, generic_name, nhi_price, price_unit
        FROM drugs
        WHERE lower(generic_name)=lower(?)
        ORDER BY id
        """,
        (drug_name,),
    )
    return cursor.fetchall()


def main():
    args = parse_args()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    updated = 0
    unchanged = 0
    skipped = 0
    multi_match = 0
    planned = []

    try:
        c.execute("BEGIN")
        for drug_name, (price, unit) in OFFICIAL_PRICES.items():
            rows = find_drugs(c, drug_name)
            if not rows:
                skipped += 1
                continue
            if len(rows) > 1:
                multi_match += 1
                print(f"  Warning: {drug_name} matched {len(rows)} rows; updating all exact generic_name matches")
            for drug_id, generic_name, old_price, old_unit in rows:
                if old_price == price and (old_unit or "") == unit:
                    unchanged += 1
                    continue
                planned.append((drug_id, generic_name, old_price, old_unit, price, unit))
                if not args.dry_run:
                    c.execute(
                        "UPDATE drugs SET nhi_price=?, price_unit=? WHERE id=?",
                        (price, unit, drug_id),
                    )
                updated += 1

        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        c.execute("SELECT COUNT(*) FROM drugs WHERE nhi_price IS NOT NULL")
        with_price = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM drugs")
        total = c.fetchone()[0]
        conn.close()

    for drug_id, generic_name, old_price, old_unit, price, unit in planned:
        old = f"NT${old_price:,.1f} / {old_unit}" if old_price is not None else "no price"
        action = "Would update" if args.dry_run else "Updated"
        print(f"  {action}: #{drug_id} {generic_name:<30} {old} -> NT${price:,.1f} / {unit}")

    print(f'\n{"Dry-run complete" if args.dry_run else "更新完成"}：{updated} 筆')
    print(f"不需更新：{unchanged} 筆")
    print(f"跳過（未在DB中）：{skipped} 筆")
    if multi_match:
        print(f"多筆 exact generic_name match：{multi_match} 組")
    print(f"有藥價資料：{with_price}/{total} 藥物")
    print("\n資料來源：健保署115/03/23公告PDF「115年藥價年度例行調整結果明細表」（115/04/01生效）")

    if not args.dry_run and not args.no_export:
        print("\nExporting data/api/*.json ...", flush=True)
        run_api_export()
    if not args.skip_validation:
        print("\nRunning semantic drug-data validation ...", flush=True)
        run_validation()


if __name__ == "__main__":
    main()

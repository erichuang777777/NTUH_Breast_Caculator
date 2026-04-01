#!/usr/bin/env python3
"""
Drug Count Validator (Standalone)
驗證資料庫中的藥物數量與解析品質

Usage:
    python validate_drugs.py
    python validate_drugs.py --docx 完整給付規定1150323.docx
    python validate_drugs.py --db nhi_drug_coverage.db --verbose
"""

import sys
import io
import sqlite3
import re
import json
import argparse
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Set
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from known_oncology_drugs import BREAST_CANCER_DRUGS, HEME_MALIGNANCY_DRUGS


def load_docx_paragraphs(docx_path: str) -> List[str]:
    """載入 DOCX 段落"""
    with zipfile.ZipFile(docx_path, 'r') as z:
        xml_data = z.read('word/document.xml')
    root = ET.fromstring(xml_data)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paragraphs = []
    for para in root.findall('.//w:p', ns):
        text_elements = para.findall('.//w:t', ns)
        text = ''.join([t.text for t in text_elements if t.text])
        if text.strip():
            paragraphs.append(text.strip())
    return paragraphs


def count_docx_drug_mentions(paragraphs: List[str]) -> Dict[str, int]:
    """計算 DOCX 中每個已知藥物被提到的次數"""
    all_drugs = BREAST_CANCER_DRUGS | HEME_MALIGNANCY_DRUGS
    full_text = '\n'.join(paragraphs).lower()

    mentions = {}
    for drug in sorted(all_drugs):
        count = full_text.count(drug.lower())
        if count > 0:
            mentions[drug] = count
    return mentions


def count_docx_drug_sections(paragraphs: List[str]) -> Dict[str, str]:
    """計算 DOCX 中有獨立章節的藥物"""
    section_pattern = re.compile(r'^(\d+\.[\d.]*)\s*([A-Z][A-Za-z\s\-/]+)')
    sections = {}
    for para in paragraphs:
        m = section_pattern.match(para)
        if m:
            drug_name = m.group(2).strip()
            section_id = m.group(1)
            if len(drug_name) >= 3:
                sections[drug_name] = section_id
    return sections


def validate_database(db_path: str, verbose: bool = False) -> dict:
    """驗證資料庫品質"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    results = {'errors': [], 'warnings': [], 'stats': {}}

    # 1. 基本統計
    cursor.execute("SELECT COUNT(*) FROM drugs")
    total = cursor.fetchone()[0]
    results['stats']['total_drugs'] = total

    cursor.execute("SELECT COUNT(*) FROM drugs WHERE specialty_id = 'oncology_breast'")
    breast = cursor.fetchone()[0]
    results['stats']['breast_drugs'] = breast

    cursor.execute("SELECT COUNT(*) FROM drugs WHERE specialty_id = 'oncology_heme'")
    heme = cursor.fetchone()[0]
    results['stats']['heme_drugs'] = heme

    # 2. 檢查資料完整性
    cursor.execute("SELECT COUNT(*) FROM drugs WHERE indication IS NULL OR indication = ''")
    no_indication = cursor.fetchone()[0]
    results['stats']['missing_indication'] = no_indication
    if no_indication > total * 0.3:
        results['warnings'].append(f"{no_indication}/{total} 藥物缺少適應症 (>{30}%)")

    cursor.execute("SELECT COUNT(*) FROM coverage_rules WHERE therapy_line IS NOT NULL")
    with_line = cursor.fetchone()[0]
    results['stats']['with_therapy_line'] = with_line

    cursor.execute("SELECT COUNT(*) FROM coverage_rules WHERE prior_auth_required = 1")
    with_auth = cursor.fetchone()[0]
    results['stats']['prior_auth_required'] = with_auth

    cursor.execute("SELECT COUNT(*) FROM coverage_rules WHERE condition IS NOT NULL AND condition != ''")
    with_cond = cursor.fetchone()[0]
    results['stats']['with_conditions'] = with_cond

    # 3. 檢查重複
    cursor.execute("""
        SELECT generic_name, COUNT(*) as cnt
        FROM drugs
        GROUP BY LOWER(generic_name)
        HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        results['warnings'].append(f"發現 {len(duplicates)} 個重複藥物名稱")
        results['duplicates'] = [(name, cnt) for name, cnt in duplicates]

    # 4. 檢查孤立資料
    cursor.execute("""
        SELECT d.id, d.generic_name FROM drugs d
        LEFT JOIN coverage_rules cr ON d.id = cr.drug_id
        WHERE cr.id IS NULL
    """)
    orphans = cursor.fetchall()
    if orphans:
        results['warnings'].append(f"{len(orphans)} 藥物沒有對應的給付規定")
        results['orphan_drugs'] = [(id_, name) for id_, name in orphans]

    # 5. 檢查 clinical_tags
    cursor.execute("SELECT COUNT(*) FROM drugs WHERE clinical_tags IS NOT NULL AND clinical_tags != ''")
    with_tags = cursor.fetchone()[0]
    results['stats']['with_clinical_tags'] = with_tags

    # 6. 各科藥物清單
    if verbose:
        cursor.execute("""
            SELECT d.generic_name, d.trade_names, d.indication,
                   cr.therapy_line, cr.prior_auth_required, cr.condition
            FROM drugs d
            LEFT JOIN coverage_rules cr ON d.id = cr.drug_id
            WHERE d.specialty_id = 'oncology_breast'
            ORDER BY d.generic_name
        """)
        results['breast_detail'] = [
            {'name': r[0], 'brand': r[1], 'indication': r[2],
             'therapy_line': r[3], 'prior_auth': bool(r[4]), 'conditions': r[5]}
            for r in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT d.generic_name, d.trade_names, d.indication,
                   cr.therapy_line, cr.prior_auth_required, cr.condition
            FROM drugs d
            LEFT JOIN coverage_rules cr ON d.id = cr.drug_id
            WHERE d.specialty_id = 'oncology_heme'
            ORDER BY d.generic_name
        """)
        results['heme_detail'] = [
            {'name': r[0], 'brand': r[1], 'indication': r[2],
             'therapy_line': r[3], 'prior_auth': bool(r[4]), 'conditions': r[5]}
            for r in cursor.fetchall()
        ]

    conn.close()
    return results


def cross_validate(db_path: str, docx_path: str) -> dict:
    """交叉驗證 DOCX 與資料庫"""
    paragraphs = load_docx_paragraphs(docx_path)
    docx_mentions = count_docx_drug_mentions(paragraphs)
    docx_sections = count_docx_drug_sections(paragraphs)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT generic_name, specialty_id FROM drugs")
    db_drugs = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    # Drugs in DOCX but not in DB
    in_docx_not_db = sorted(set(docx_mentions.keys()) - set(db_drugs.keys()))

    # Drugs in DB but not mentioned in DOCX
    in_db_not_docx = sorted(set(db_drugs.keys()) - set(docx_mentions.keys()))

    # Drugs with sections in DOCX
    docx_with_section = set(docx_sections.keys())

    return {
        'docx_mentioned_drugs': len(docx_mentions),
        'docx_section_drugs': len(docx_sections),
        'db_drugs': len(db_drugs),
        'in_docx_not_db': in_docx_not_db,
        'in_db_not_docx': in_db_not_docx,
        'in_docx_not_db_count': len(in_docx_not_db),
        'in_db_not_docx_count': len(in_db_not_docx),
    }


def main():
    parser = argparse.ArgumentParser(description='藥物數量與解析品質驗證')
    parser.add_argument('--db', default='nhi_drug_coverage.db', help='資料庫路徑')
    parser.add_argument('--docx', help='DOCX 檔案路徑 (用於交叉驗證)')
    parser.add_argument('--verbose', '-v', action='store_true', help='顯示詳細資料')
    parser.add_argument('--json', action='store_true', help='輸出 JSON')
    args = parser.parse_args()

    print("=" * 70)
    print("藥物數量與解析品質驗證")
    print("=" * 70)

    # Database validation
    print("\n[1] 資料庫驗證")
    db_result = validate_database(args.db, verbose=args.verbose)

    stats = db_result['stats']
    print(f"\n  {'項目':<25} {'數量':>6}")
    print(f"  {'-'*35}")
    print(f"  {'總藥物數':<25} {stats['total_drugs']:>6}")
    print(f"  {'乳癌藥物':<25} {stats['breast_drugs']:>6}")
    print(f"  {'血液腫瘤藥物':<25} {stats['heme_drugs']:>6}")
    print(f"  {'缺少適應症':<25} {stats['missing_indication']:>6}")
    print(f"  {'有療程線資料':<25} {stats['with_therapy_line']:>6}")
    print(f"  {'需事前審查':<25} {stats['prior_auth_required']:>6}")
    print(f"  {'有給付條件':<25} {stats['with_conditions']:>6}")
    print(f"  {'有臨床標籤':<25} {stats['with_clinical_tags']:>6}")

    # Warnings
    if db_result['warnings']:
        print(f"\n  *** 警告 ***")
        for w in db_result['warnings']:
            print(f"  ! {w}")

    if db_result.get('duplicates'):
        print(f"\n  重複藥物:")
        for name, cnt in db_result['duplicates']:
            print(f"    {name} x{cnt}")

    if db_result.get('orphan_drugs') and args.verbose:
        print(f"\n  無給付規定的藥物:")
        for id_, name in db_result['orphan_drugs']:
            print(f"    [{id_}] {name}")

    # Verbose detail
    if args.verbose and db_result.get('breast_detail'):
        print(f"\n  --- 乳癌藥物明細 ({len(db_result['breast_detail'])}) ---")
        for d in db_result['breast_detail']:
            line = f"L{d['therapy_line']}" if d['therapy_line'] else "N/A"
            auth = "審" if d['prior_auth'] else ""
            ind = (d['indication'] or '')[:60]
            print(f"    {d['name']:<25} {line:<5} {auth:<3} {ind}")

    if args.verbose and db_result.get('heme_detail'):
        print(f"\n  --- 血液腫瘤藥物明細 ({len(db_result['heme_detail'])}) ---")
        for d in db_result['heme_detail']:
            line = f"L{d['therapy_line']}" if d['therapy_line'] else "N/A"
            auth = "審" if d['prior_auth'] else ""
            ind = (d['indication'] or '')[:60]
            print(f"    {d['name']:<25} {line:<5} {auth:<3} {ind}")

    # Cross validation
    xval = None
    if args.docx:
        print(f"\n[2] 交叉驗證 (DOCX vs DB)")
        xval = cross_validate(args.db, args.docx)
        print(f"  DOCX 提到的已知藥物: {xval['docx_mentioned_drugs']}")
        print(f"  DOCX 有獨立章節:     {xval['docx_section_drugs']}")
        print(f"  資料庫藥物數:        {xval['db_drugs']}")
        print(f"  DOCX 有但 DB 無:     {xval['in_docx_not_db_count']}")
        print(f"  DB 有但 DOCX 無:     {xval['in_db_not_docx_count']}")

        if xval['in_docx_not_db'] and args.verbose:
            print(f"\n  DOCX 中有但資料庫中沒有:")
            for d in xval['in_docx_not_db']:
                print(f"    + {d}")

        if xval['in_db_not_docx'] and args.verbose:
            print(f"\n  資料庫中有但 DOCX 未提及:")
            for d in xval['in_db_not_docx']:
                print(f"    - {d}")

    # Quality score
    print(f"\n{'='*70}")
    print("解析品質評分")
    print(f"{'='*70}")

    total = max(stats['total_drugs'], 1)
    indication_score = (total - stats['missing_indication']) / total * 100
    therapy_score = stats['with_therapy_line'] / total * 100
    condition_score = stats['with_conditions'] / total * 100
    tag_score = stats['with_clinical_tags'] / total * 100

    scores = [
        ('適應症完整度', indication_score),
        ('療程線覆蓋率', therapy_score),
        ('給付條件覆蓋率', condition_score),
        ('臨床標籤覆蓋率', tag_score),
    ]

    overall = sum(s for _, s in scores) / len(scores)
    for label, score in scores:
        bar = '█' * int(score / 5) + '░' * (20 - int(score / 5))
        print(f"  {label:<18} {bar} {score:5.1f}%")

    print(f"\n  {'整體品質分數':<18} {'':>20} {overall:5.1f}%")

    grade = 'A' if overall >= 80 else 'B' if overall >= 60 else 'C' if overall >= 40 else 'D'
    print(f"  等級: {grade}")

    # JSON output
    if args.json:
        output = {
            'validate_date': __import__('datetime').datetime.now().isoformat(),
            'database': db_result,
            'cross_validation': xval,
            'quality_scores': {label: round(score, 1) for label, score in scores},
            'overall_score': round(overall, 1),
            'grade': grade,
        }
        json_path = f"validate_result_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n[*] JSON 輸出: {json_path}")

    print(f"\n{'='*70}")
    print("驗證完成!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

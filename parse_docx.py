#!/usr/bin/env python3
"""
NHI Drug Coverage DOCX Parser (Standalone)
解析台灣健保藥物給付規定 DOCX 文檔，提取腫瘤藥物資訊
輸出 JSON 格式的藥物資料

Usage:
    python parse_docx.py <docx_file>
    python parse_docx.py <docx_file> --update-db
    python parse_docx.py <docx_file> -o output.json
"""

import sys
import io
import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from known_oncology_drugs import BREAST_CANCER_DRUGS, HEME_MALIGNANCY_DRUGS


class DocxDrugParser:
    """DOCX 藥物解析器"""

    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.paragraphs: List[str] = []
        self._load_docx()

    def _load_docx(self):
        """載入 DOCX 並提取段落"""
        with zipfile.ZipFile(self.docx_path, 'r') as z:
            xml_data = z.read('word/document.xml')
        root = ET.fromstring(xml_data)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        for para in root.findall('.//w:p', ns):
            text_elements = para.findall('.//w:t', ns)
            text = ''.join([t.text for t in text_elements if t.text])
            if text.strip():
                self.paragraphs.append(text.strip())

    def find_drug_section(self, drug_name: str) -> Optional[Tuple[int, int]]:
        """找出藥物在文件中的章節範圍 (start_idx, end_idx)"""
        drug_lower = drug_name.lower()
        start_idx = None

        for i, para in enumerate(self.paragraphs):
            if drug_lower in para.lower():
                if re.match(r'^\d+\.[\d.]*\s*' + re.escape(drug_name), para, re.IGNORECASE):
                    start_idx = i
                    break
                if re.match(r'^\d+\.[\d.]*\s*\S+.*' + re.escape(drug_name), para, re.IGNORECASE):
                    if start_idx is None:
                        start_idx = i

        if start_idx is None:
            return None

        header_match = re.match(r'^(\d+\.[\d.]*)', self.paragraphs[start_idx])
        if not header_match:
            return (start_idx, min(start_idx + 50, len(self.paragraphs)))

        header_prefix = header_match.group(1)
        parts = [p for p in header_prefix.split('.') if p]

        if len(parts) >= 2:
            parent_prefix = parts[0]
            next_section_pattern = re.compile(
                r'^' + re.escape(parent_prefix) + r'\.\d+\.?\s*[A-Z\u4e00-\u9fff]'
            )
        else:
            next_section_pattern = re.compile(r'^\d+\.\s*[A-Z\u4e00-\u9fff]')

        end_idx = start_idx + 1
        for j in range(start_idx + 1, min(start_idx + 300, len(self.paragraphs))):
            para = self.paragraphs[j]
            if next_section_pattern.match(para):
                m = re.match(r'^(\d+\.[\d.]*)', para)
                if m and m.group(1) != header_prefix:
                    end_idx = j
                    break
            end_idx = j + 1

        return (start_idx, end_idx)

    def extract_therapy_line(self, section_text: List[str]) -> Optional[int]:
        """提取療程線"""
        full_text = '\n'.join(section_text)
        line_patterns = [
            (1, [r'第一線', r'first[\s-]?line', r'1st[\s-]?line', r'首選', r'初始治療']),
            (2, [r'第二線', r'second[\s-]?line', r'2nd[\s-]?line', r'先前.*治療.*無效', r'復發']),
            (3, [r'第三線', r'third[\s-]?line', r'3rd[\s-]?line']),
        ]
        found = set()
        for line_num, patterns in line_patterns:
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    found.add(line_num)
        return min(found) if found else None

    def check_prior_auth(self, section_text: List[str]) -> bool:
        """檢查是否需要事前審查"""
        full_text = '\n'.join(section_text)
        keywords = ['事前審查', '事前審核', '須經審查', '需經審查', '核准後使用']
        return any(kw in full_text for kw in keywords)

    def extract_indications(self, section_text: List[str]) -> str:
        """提取適應症"""
        indications = []
        for para in section_text[1:]:
            if '限用於' in para or '用於' in para:
                indications.append(para[:300])
            elif re.match(r'^\d+\.[^\d]', para) and len(para) < 300:
                indications.append(para[:300])
        if not indications and len(section_text) > 1:
            for para in section_text[1:4]:
                if len(para) > 10:
                    indications.append(para[:300])
        return ' | '.join(indications[:8])

    def extract_conditions(self, section_text: List[str]) -> str:
        """提取給付條件"""
        conditions = []
        for para in section_text[1:]:
            if re.match(r'^\(\d+\)', para) and len(para) > 10:
                conditions.append(para[:300])
            elif any(kw in para for kw in ['事前審查', '給付條件', '核准後使用', '須檢附']):
                conditions.append(para[:300])
        return ' | '.join(conditions[:10])

    def extract_brand_name(self, header_text: str) -> Optional[str]:
        """從標題提取商品名"""
        m = re.search(r'[（(]如\s*([A-Z][A-Za-z\s\-/]{2,30}?)(?:[，,；;、)）]|$)', header_text)
        if m:
            brand = m.group(1).strip()
            invalid = {'AML', 'CML', 'ALL', 'CLL', 'NHL', 'MDS', 'GIST'}
            if brand not in invalid and len(brand) >= 3:
                return brand
        return None

    def extract_pattern_drugs(self, text: str) -> Set[str]:
        """使用模式從文本中提取藥物名"""
        drugs = set()
        suffixes = ['mab', 'umab', 'inib', 'nib', 'cept', 'zole', 'tecan']
        for suffix in suffixes:
            pattern = r'\b([A-Z][a-z]+' + suffix + r')\b'
            drugs.update(re.findall(pattern, text))
        return drugs

    def extract_all_drugs(self) -> Dict[str, dict]:
        """提取所有腫瘤藥物"""
        all_known = BREAST_CANCER_DRUGS | HEME_MALIGNANCY_DRUGS
        full_text = '\n'.join(self.paragraphs)

        # Step 1: 從已知藥物列表匹配
        found_drugs = {}
        for drug_name in sorted(all_known):
            if drug_name.lower() in full_text.lower():
                section = self.find_drug_section(drug_name)
                if section:
                    start, end = section
                    section_text = self.paragraphs[start:end]
                    found_drugs[drug_name] = {
                        'name': drug_name,
                        'section_start': start,
                        'section_end': end,
                        'section_length': end - start,
                        'header': self.paragraphs[start],
                        'therapy_line': self.extract_therapy_line(section_text),
                        'prior_auth': self.check_prior_auth(section_text),
                        'indication': self.extract_indications(section_text),
                        'conditions': self.extract_conditions(section_text),
                        'brand_name': self.extract_brand_name(self.paragraphs[start]),
                        'category': 'breast' if drug_name in BREAST_CANCER_DRUGS else 'heme',
                    }
                else:
                    found_drugs[drug_name] = {
                        'name': drug_name,
                        'section_start': None,
                        'section_end': None,
                        'section_length': 0,
                        'header': None,
                        'therapy_line': None,
                        'prior_auth': False,
                        'indication': None,
                        'conditions': None,
                        'brand_name': None,
                        'category': 'breast' if drug_name in BREAST_CANCER_DRUGS else 'heme',
                        'note': 'mentioned in text but no dedicated section found',
                    }

        # Step 2: 模式提取補充
        pattern_drugs = self.extract_pattern_drugs(full_text)
        for drug_name in pattern_drugs:
            if drug_name not in found_drugs and drug_name not in all_known:
                section = self.find_drug_section(drug_name)
                if section:
                    start, end = section
                    section_text = self.paragraphs[start:end]
                    found_drugs[drug_name] = {
                        'name': drug_name,
                        'section_start': start,
                        'section_end': end,
                        'section_length': end - start,
                        'header': self.paragraphs[start],
                        'therapy_line': self.extract_therapy_line(section_text),
                        'prior_auth': self.check_prior_auth(section_text),
                        'indication': self.extract_indications(section_text),
                        'conditions': self.extract_conditions(section_text),
                        'brand_name': self.extract_brand_name(self.paragraphs[start]),
                        'category': 'unknown',
                        'source': 'pattern_extraction',
                    }

        return found_drugs


def update_database(drugs: Dict[str, dict], db_path: str = "nhi_drug_coverage.db"):
    """更新資料庫"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    updated = 0
    for drug_name, info in drugs.items():
        if info.get('section_start') is None:
            continue

        specialty = 'oncology_breast' if info['category'] == 'breast' else 'oncology_heme'

        # Check if drug exists
        cursor.execute("SELECT id FROM drugs WHERE generic_name = ?", (drug_name,))
        row = cursor.fetchone()

        if row:
            drug_id = row[0]
            cursor.execute(
                "UPDATE drugs SET indication = ?, trade_names = COALESCE(?, trade_names) WHERE id = ?",
                (info['indication'], info['brand_name'], drug_id)
            )
        else:
            cursor.execute(
                "INSERT INTO drugs (generic_name, specialty_id, indication, trade_names, created_date) VALUES (?, ?, ?, ?, ?)",
                (drug_name, specialty, info['indication'], info['brand_name'], datetime.now().strftime('%Y-%m-%d'))
            )
            drug_id = cursor.lastrowid

        # Update coverage rules
        cursor.execute("SELECT id FROM coverage_rules WHERE drug_id = ?", (drug_id,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE coverage_rules SET therapy_line = ?, condition = ?, prior_auth_required = ? WHERE drug_id = ?",
                (info['therapy_line'], info['conditions'], 1 if info['prior_auth'] else 0, drug_id)
            )
        else:
            cursor.execute(
                "INSERT INTO coverage_rules (drug_id, therapy_line, condition, prior_auth_required) VALUES (?, ?, ?, ?)",
                (drug_id, info['therapy_line'], info['conditions'], 1 if info['prior_auth'] else 0)
            )
        updated += 1

    conn.commit()
    conn.close()
    return updated


def main():
    parser = argparse.ArgumentParser(description='NHI Drug Coverage DOCX Parser')
    parser.add_argument('docx_file', help='DOCX 檔案路徑')
    parser.add_argument('--update-db', action='store_true', help='更新資料庫')
    parser.add_argument('--db', default='nhi_drug_coverage.db', help='資料庫路徑')
    parser.add_argument('-o', '--output', help='輸出 JSON 檔案路徑')
    args = parser.parse_args()

    print("=" * 70)
    print("NHI Drug Coverage DOCX Parser")
    print("=" * 70)

    docx_parser = DocxDrugParser(args.docx_file)
    print(f"[*] 載入 {len(docx_parser.paragraphs)} 段落")

    print("[*] 提取藥物資料...")
    drugs = docx_parser.extract_all_drugs()

    # 統計
    with_section = {k: v for k, v in drugs.items() if v.get('section_start') is not None}
    without_section = {k: v for k, v in drugs.items() if v.get('section_start') is None}
    breast = {k: v for k, v in drugs.items() if v.get('category') == 'breast'}
    heme = {k: v for k, v in drugs.items() if v.get('category') == 'heme'}
    with_auth = {k: v for k, v in with_section.items() if v.get('prior_auth')}
    with_line = {k: v for k, v in with_section.items() if v.get('therapy_line') is not None}

    print(f"\n{'='*70}")
    print("解析結果摘要")
    print(f"{'='*70}")
    print(f"  總藥物數:        {len(drugs)}")
    print(f"  有章節資料:      {len(with_section)}")
    print(f"  無章節資料:      {len(without_section)}")
    print(f"  乳癌藥物:        {len(breast)}")
    print(f"  血液腫瘤藥物:    {len(heme)}")
    print(f"  需事前審查:      {len(with_auth)}")
    print(f"  有療程線資料:    {len(with_line)}")

    # 輸出 JSON
    output_data = {
        'parse_date': datetime.now().isoformat(),
        'source_file': args.docx_file,
        'total_paragraphs': len(docx_parser.paragraphs),
        'summary': {
            'total_drugs': len(drugs),
            'with_section': len(with_section),
            'without_section': len(without_section),
            'breast_cancer': len(breast),
            'hematologic': len(heme),
            'prior_auth_required': len(with_auth),
            'with_therapy_line': len(with_line),
        },
        'drugs': drugs,
    }

    output_path = args.output or f"parse_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n[*] JSON 輸出: {output_path}")

    # 更新資料庫
    if args.update_db:
        print(f"\n[*] 更新資料庫: {args.db}")
        count = update_database(drugs, args.db)
        print(f"[*] 已更新 {count} 筆藥物資料")

    print(f"\n{'='*70}")
    print("解析完成!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

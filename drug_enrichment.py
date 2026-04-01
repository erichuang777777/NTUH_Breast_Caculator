#!/usr/bin/env python3
"""
Drug Data Enrichment Script
從 DOCX 提取每個藥物的適應症、療程線、事前審查等資訊，更新資料庫
"""

import sys
import io
import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
from typing import Dict, List, Optional, Tuple

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class DrugEnricher:
    """藥物資料充實器"""

    def __init__(self, docx_path: str, db_path: str = "nhi_drug_coverage.db"):
        self.docx_path = docx_path
        self.db_path = db_path
        self.paragraphs: List[str] = []
        self._load_docx()

    def _load_docx(self):
        """載入 DOCX"""
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
        """
        找出藥物在文件中的主要章節範圍 (start_idx, end_idx)。

        文件格式範例：
          9.18. Trastuzumab (如Herceptin)：
            1.早期乳癌
              (1)條件...
            2.轉移性乳癌
            3.轉移性胃癌
            4.經事前審查核准後使用...
          9.19. Estramustine ...  ← 下一個藥物章節

        章節結束判斷：遇到同級或更高級的藥物章節標題
        (如 9.19. / 9.20. / 8.3. 等)
        """
        drug_lower = drug_name.lower()
        start_idx = None

        # Pattern: section number + drug name
        for i, para in enumerate(self.paragraphs):
            if drug_lower in para.lower():
                # Match "9.18. Trastuzumab" or "8.2.7.Rituximab"
                if re.match(r'^\d+\.[\d.]*\s*' + re.escape(drug_name), para, re.IGNORECASE):
                    start_idx = i
                    break
                # Match "CDK4/6抑制劑 (如 ribociclib；palbociclib)"
                if re.match(r'^\d+\.[\d.]*\s*\S+.*' + re.escape(drug_name), para, re.IGNORECASE):
                    if start_idx is None:
                        start_idx = i

        if start_idx is None:
            return None

        # 取得本章節的編號格式，例如 "9.18." 或 "8.2.7."
        header_match = re.match(r'^(\d+\.[\d.]*)', self.paragraphs[start_idx])
        if not header_match:
            return (start_idx, min(start_idx + 50, len(self.paragraphs)))

        header_prefix = header_match.group(1)  # e.g. "9.18."

        # 解析章節編號的各層級，例如 "9.18." → [9, 18]
        parts = [p for p in header_prefix.split('.') if p]
        # 建立同級下一章節的 pattern
        # 例如 9.18. → 需要匹配 9.19. / 9.20. / ... 或更高級 10. 等
        # 關鍵：同級章節 = 相同前綴層數 + 不同數字
        # e.g. "9.18." 的同級 = r'^9\.\d+\.' 後面跟藥物名或中文
        if len(parts) >= 2:
            # 例如 parts = [9, 18] → 匹配 "9.數字." 開頭的下一個章節
            parent_prefix = parts[0]  # "9"
            next_section_pattern = re.compile(
                r'^' + re.escape(parent_prefix) + r'\.\d+\.?\s*[A-Z\u4e00-\u9fff]'
            )
        else:
            # 頂層章節，匹配 "數字." 開頭
            next_section_pattern = re.compile(
                r'^\d+\.\s*[A-Z\u4e00-\u9fff]'
            )

        end_idx = start_idx + 1
        for j in range(start_idx + 1, min(start_idx + 300, len(self.paragraphs))):
            para = self.paragraphs[j]
            # 檢查是否為同級的下一個章節標題
            if next_section_pattern.match(para):
                # 確保不是自己（相同編號）
                m = re.match(r'^(\d+\.[\d.]*)', para)
                if m and m.group(1) != header_prefix:
                    end_idx = j
                    break
            end_idx = j + 1

        return (start_idx, end_idx)

    def extract_indications(self, section_text: List[str]) -> str:
        """從章節文本提取適應症摘要"""
        indications = []

        for para in section_text[1:]:  # 跳過標題行
            # "限用於" or "用於" patterns
            if '限用於' in para or '用於' in para:
                indications.append(para[:300])
            # 頂層編號 "1.早期乳癌" "2.轉移性乳癌" 等
            elif re.match(r'^\d+\.[^\d]', para) and len(para) < 300:
                indications.append(para[:300])

        if not indications and len(section_text) > 1:
            # Fallback: 使用前幾行非標題內容
            for para in section_text[1:4]:
                if len(para) > 10:
                    indications.append(para[:300])

        return ' | '.join(indications[:8])

    def extract_therapy_line(self, section_text: List[str]) -> Optional[int]:
        """從章節文本提取療程線資訊"""
        full_text = '\n'.join(section_text)

        # Priority: look for explicit therapy line mentions
        line_patterns = [
            (1, [r'第一線', r'first[\s-]?line', r'1st[\s-]?line', r'一線',
                 r'首選', r'初始治療', r'初診斷']),
            (2, [r'第二線', r'second[\s-]?line', r'2nd[\s-]?line', r'二線',
                 r'先前.*治療.*無效', r'復發', r'難治']),
            (3, [r'第三線', r'third[\s-]?line', r'3rd[\s-]?line', r'三線']),
        ]

        found_lines = set()
        for line_num, patterns in line_patterns:
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    found_lines.add(line_num)

        if found_lines:
            return min(found_lines)  # Return earliest therapy line

        # Fallback: check for keywords suggesting treatment context
        if '未曾' in full_text or '新診斷' in full_text:
            return 1
        if '轉移' in full_text and '術後' not in full_text:
            return 2
        if '輔助' in full_text:
            return 1

        return None

    def check_prior_auth(self, section_text: List[str]) -> bool:
        """檢查是否需要事前審查"""
        full_text = '\n'.join(section_text)
        auth_keywords = ['事前審查', '事前審核', '須經審查', '需經審查',
                         'prior auth', 'prior review', '核准後使用']
        return any(kw in full_text for kw in auth_keywords)

    def extract_conditions(self, section_text: List[str]) -> str:
        """提取給付條件摘要"""
        conditions = []
        for para in section_text[1:]:  # 跳過標題行
            # 條件段落：(1)... (2)... 等
            if re.match(r'^\(\d+\)', para) and len(para) > 10:
                conditions.append(para[:300])
            # 事前審查、給付條件等關鍵段落
            elif any(kw in para for kw in ['事前審查', '給付條件', '核准後使用', '每', '須檢附']):
                conditions.append(para[:300])

        return ' | '.join(conditions[:10])

    def extract_brand_name(self, header_text: str) -> Optional[str]:
        """從標題提取商品名"""
        # Match patterns like (如Herceptin) or （如Mabthera）
        m = re.search(r'[（(]如\s*([A-Z][A-Za-z\s\-/]{2,30}?)(?:[，,；;、)）]|$)', header_text)
        if m:
            brand = m.group(1).strip()
            # Validate: brand name should not be a disease/condition abbreviation
            invalid_brands = {'AML', 'CML', 'ALL', 'CLL', 'NHL', 'MDS', 'GIST'}
            if brand not in invalid_brands and len(brand) >= 3:
                return brand
        return None

    def enrich_all_drugs(self) -> Dict[str, dict]:
        """充實所有資料庫中的藥物資訊"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, generic_name, specialty_id FROM drugs ORDER BY generic_name")
        drugs = cursor.fetchall()

        enriched = {}
        found_count = 0
        total = len(drugs)

        for drug_id, drug_name, specialty_id in drugs:
            section = self.find_drug_section(drug_name)

            if section:
                start, end = section
                section_text = self.paragraphs[start:end]
                found_count += 1

                # Extract enrichment data
                indication = self.extract_indications(section_text)
                therapy_line = self.extract_therapy_line(section_text)
                prior_auth = self.check_prior_auth(section_text)
                conditions = self.extract_conditions(section_text)
                brand_name = self.extract_brand_name(self.paragraphs[start])

                enriched[drug_name] = {
                    'drug_id': drug_id,
                    'indication': indication,
                    'therapy_line': therapy_line,
                    'prior_auth': prior_auth,
                    'conditions': conditions,
                    'brand_name': brand_name,
                    'section_range': (start, end),
                    'section_length': end - start,
                }

                # Update database
                if brand_name:
                    cursor.execute(
                        "UPDATE drugs SET trade_names = ?, indication = ? WHERE id = ?",
                        (brand_name, indication, drug_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE drugs SET indication = ? WHERE id = ?",
                        (indication, drug_id)
                    )

                # Update or insert coverage_rules
                cursor.execute("SELECT id FROM coverage_rules WHERE drug_id = ?", (drug_id,))
                existing_rule = cursor.fetchone()

                if existing_rule:
                    cursor.execute(
                        """UPDATE coverage_rules
                           SET therapy_line = ?, condition = ?, prior_auth_required = ?
                           WHERE drug_id = ?""",
                        (therapy_line, conditions, 1 if prior_auth else 0, drug_id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO coverage_rules
                           (drug_id, therapy_line, condition, prior_auth_required)
                           VALUES (?, ?, ?, ?)""",
                        (drug_id, therapy_line, conditions, 1 if prior_auth else 0)
                    )

            else:
                enriched[drug_name] = {
                    'drug_id': drug_id,
                    'indication': None,
                    'therapy_line': None,
                    'prior_auth': False,
                    'conditions': None,
                    'brand_name': None,
                    'section_range': None,
                    'section_length': 0,
                }

        conn.commit()
        conn.close()

        print(f"[*] Enriched {found_count}/{total} drugs with section data")
        return enriched


def main():
    print("=" * 70)
    print("Drug Data Enrichment")
    print("=" * 70)

    enricher = DrugEnricher("完整給付規定1150323.docx")
    print(f"[*] Loaded {len(enricher.paragraphs)} paragraphs\n")

    results = enricher.enrich_all_drugs()

    # Print summary
    print(f"\n{'='*70}")
    print("ENRICHMENT RESULTS")
    print(f"{'='*70}\n")

    found_drugs = {k: v for k, v in results.items() if v['section_range'] is not None}
    not_found = {k: v for k, v in results.items() if v['section_range'] is None}

    print(f"Drugs with section data: {len(found_drugs)}")
    print(f"Drugs without section:   {len(not_found)}\n")

    if found_drugs:
        print("--- ENRICHED DRUGS ---")
        for name, info in sorted(found_drugs.items()):
            line_str = f"Line {info['therapy_line']}" if info['therapy_line'] else "N/A"
            auth_str = "YES" if info['prior_auth'] else "no"
            brand_str = info['brand_name'] or ""
            print(f"  {name:<30} | {line_str:<8} | Auth: {auth_str:<3} | Brand: {brand_str}")

    if not_found:
        print(f"\n--- NOT FOUND IN DOCUMENT ({len(not_found)}) ---")
        for name in sorted(not_found.keys()):
            print(f"  {name}")

    # Show database stats
    print(f"\n{'='*70}")
    print("DATABASE SUMMARY")
    print(f"{'='*70}")

    conn = sqlite3.connect("nhi_drug_coverage.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM drugs WHERE indication IS NOT NULL AND indication != ''")
    print(f"Drugs with indication:     {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM coverage_rules WHERE therapy_line IS NOT NULL")
    print(f"Drugs with therapy line:   {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM coverage_rules WHERE prior_auth_required = 1")
    print(f"Drugs requiring prior auth: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM drugs WHERE trade_names IS NOT NULL AND trade_names != ''")
    print(f"Drugs with brand names:    {cursor.fetchone()[0]}")

    conn.close()

    print(f"\n{'='*70}")
    print("Enrichment complete!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

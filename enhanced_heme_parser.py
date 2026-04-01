#!/usr/bin/env python3
"""
Enhanced Hematologic Drug Parser
針對血液腫瘤藥物的強化版提取器
"""

import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
from datetime import datetime
from typing import Set, Dict
from known_oncology_drugs import HEME_MALIGNANCY_DRUGS

class EnhancedHemeParser:
    """血液腫瘤藥物強化提取器"""

    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.paragraphs = []
        self._load_docx()

    def _load_docx(self):
        """載入 DOCX"""
        with zipfile.ZipFile(self.docx_path, 'r') as z:
            xml_data = z.read('word/document.xml').decode('utf-8', errors='ignore')
        root = ET.fromstring(xml_data.encode('utf-8', errors='ignore'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        for para in root.findall('.//w:p', ns):
            text_elements = para.findall('.//w:t', ns)
            text = ''.join([t.text for t in text_elements if t.text])
            if text.strip():
                self.paragraphs.append(text.strip())

    def find_heme_sections(self) -> Set[int]:
        """找出所有血液腫瘤相關段落"""
        heme_keywords = [
            # 淋巴癌
            '淋巴', 'lymphoma', 'Lymphoma', 'NHL', 'HL', 'Hodgkin', 'non-Hodgkin',
            'Burkitt', 'follicular', 'mantle cell', 'DLBCL', 'Marginal zone',
            # 血癌/白血病
            '血癌', 'leukemia', 'Leukemia', 'AML', 'CLL', 'CML', 'ALL',
            'acute myeloid', 'chronic myeloid', 'chronic lymphoid',
            'Hairy cell', 'Prolymphocytic', 'Blastic',
            # 多發性骨髓瘤
            '骨髓瘤', 'myeloma', 'Myeloma', 'plasma cell',
            # 常見藥物名
            'rituximab', 'bortezomib', 'ibrutinib', 'venetoclax',
            'lenalidomide', 'pomalidomide', 'dasatinib', 'nilotinib',
            'imatinib', 'ponatinib', 'azacitidine', 'decitabine',
            # MDS
            'myelodysplastic', 'MDS',
        ]

        indices = set()
        for i, para in enumerate(self.paragraphs):
            para_lower = para.lower()
            for kw in heme_keywords:
                if kw.lower() in para_lower:
                    indices.add(i)
                    break
        return indices

    def extract_known_drugs(self, text: str) -> Set[str]:
        """從已知藥物列表中提取"""
        drugs = set()
        for drug in HEME_MALIGNANCY_DRUGS:
            if drug in text or drug.lower() in text.lower():
                drugs.add(drug)
        return drugs

    def extract_drug_patterns(self, text: str) -> Set[str]:
        """使用模式提取藥物"""
        drugs = set()

        # 已知的藥物後綴
        suffixes = ['mab', 'umab', 'inib', 'nib', 'cept', 'pine', 'dine', 'tecan', 'zole']

        # 尋找以後綴結尾的詞
        for suffix in suffixes:
            pattern = r'\b([A-Z][a-z]+' + suffix + r')\b'
            matches = re.findall(pattern, text)
            drugs.update(matches)

        # 尋找包含數字的藥物名 (如 CD20, HER2 等)
        pattern = r'\b([A-Z]{2,4}[0-9]+)\b'
        matches = re.findall(pattern, text)
        drugs.update(matches)

        # 尋找括號內的商品名
        pattern = r'\(([A-Z][A-Za-z0-9\-/\s]{3,30}?)\)'
        matches = re.findall(pattern, text)
        for match in matches:
            match = match.strip()
            if 4 <= len(match) <= 40 and not match.isupper():
                # 清理前導字符
                match = re.sub(r'^[\(\)\[\]\{\}0-9\s]+', '', match).strip()
                if match and match[0].isalpha():
                    drugs.add(match)

        return drugs

    def filter_valid_drugs(self, raw_drugs: Set[str]) -> Set[str]:
        """過濾出真實的血液腫瘤藥物"""
        # 明確排除的項目
        explicit_exclude = {
            'DQB1', 'IHC3', 'Hypersplenism', 'Pilocarpine',
            'Philadelphia', 'Philadelphiachromosome',
            'CD20', 'CD30', 'HER2', 'CD', 'HER',  # 生物標記，不是藥物
        }

        # 排除的詞彙
        exclude_words = {
            'lymphoma', 'leukemia', 'myeloma', 'cancer', 'syndrome',
            'disease', 'cell', 'response', 'progression', 'burden',
            'agent', 'blocker', 'agonist', 'antagonist',
            'receptor', 'factor', 'protein', 'antigen', 'antibody',
            'marker', 'chromosome', 'mutation', 'translocation',
            'kinase', 'polymerase', 'nucleotide',
            'acid', 'peptide', 'hormone', 'steroid',
            'allele', 'gene', 'variant', 'wildtype', 'wild-type',
            'bcr', 'abl', 'egfr', 'vegf', 'pdl1',
            'score', 'scale', 'index', 'classification', 'staging',
            'criteria', 'guideline', 'protocol', 'regimen', 'schedule',
            'cycle', 'phase', 'line', 'therapy', 'treatment',
            'remission', 'relapse', 'refractory', 'crisis',
            'workshop', 'conference', 'committee', 'society',
        }

        valid_drugs = set()
        for drug in raw_drugs:
            drug_lower = drug.lower()

            # 排除明確列表中的非藥物項目
            if drug in explicit_exclude:
                continue

            # 排除全小寫詞和太短的詞
            if drug_lower == drug or len(drug) < 4:
                continue

            # 排除明顯的非藥物詞
            if any(exclude in drug_lower for exclude in exclude_words):
                continue

            # 排除包含多個空格的短語
            if drug.count(' ') > 1:
                continue

            # 排除明顯的臨床名詞 (包含"淋巴"、"癌"等)
            if any(char in drug for char in ['淋', '癌', '瘤', '血', '球']):
                continue

            valid_drugs.add(drug)

        return valid_drugs

    def extract_heme_drugs(self) -> Set[str]:
        """提取所有血液腫瘤藥物"""
        # 找出相關段落
        heme_indices = self.find_heme_sections()
        print(f"[*] Found {len(heme_indices)} hematologic-related paragraphs")

        # 合併成文本
        heme_text = '\n'.join(self.paragraphs[i] for i in heme_indices)

        # Strategy 1: 使用已知藥物列表
        known_drugs = self.extract_known_drugs(heme_text)
        print(f"[*] Known drugs found: {len(known_drugs)}")

        # Strategy 2: 使用模式提取
        pattern_drugs = self.extract_drug_patterns(heme_text)
        print(f"[*] Pattern-based drugs: {len(pattern_drugs)}")

        # 合併並過濾
        all_drugs = known_drugs | pattern_drugs
        filtered_drugs = self.filter_valid_drugs(all_drugs)

        print(f"[*] After filtering: {len(filtered_drugs)}")

        return filtered_drugs


def main():
    print("=" * 70)
    print("Enhanced Hematologic Drug Parser")
    print("=" * 70)

    parser = EnhancedHemeParser("完整給付規定1150323.docx")
    print(f"\n[*] Loaded {len(parser.paragraphs)} paragraphs\n")

    print("[EXTRACTING HEMATOLOGIC DRUGS]")
    heme_drugs = parser.extract_heme_drugs()

    print(f"\n[RESULTS]")
    print(f"Total hematologic drugs extracted: {len(heme_drugs)}\n")
    print("Extracted drugs:")
    for i, drug in enumerate(sorted(heme_drugs), 1):
        print(f"  {i:2d}. {drug}")

    # 將結果保存到數據庫
    print(f"\n[SAVING TO DATABASE]")
    db_path = "nhi_drug_coverage.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 只清空血液腫瘤藥物表
    cursor.execute("DELETE FROM coverage_rules WHERE drug_id IN (SELECT id FROM drugs WHERE specialty_id = 'oncology_heme')")
    cursor.execute("DELETE FROM drugs WHERE specialty_id = 'oncology_heme'")
    conn.commit()

    # 插入新藥物
    inserted = 0
    for drug_name in sorted(heme_drugs):
        try:
            cursor.execute(
                """INSERT INTO drugs (generic_name, specialty_id, created_date)
                   VALUES (?, ?, ?)""",
                (drug_name, 'oncology_heme', datetime.now().date())
            )
            inserted += 1
        except Exception as e:
            print(f"    Error inserting {drug_name}: {e}")

    conn.commit()
    conn.close()

    print(f"Inserted {inserted} hematologic drugs into database")

    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()

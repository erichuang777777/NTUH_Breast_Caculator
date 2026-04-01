#!/usr/bin/env python3
"""
Comprehensive NHI Drug Parser
直接從關鍵字段落提取所有藥物
"""

import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
import json
from datetime import datetime
from typing import List, Dict, Set

class ComprehensiveDocxParser:
    """完整的 DOCX 解析器"""

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

    def find_disease_sections(self, disease_keywords: List[str]) -> Set[int]:
        """
        找出包含疾病關鍵詞的所有段落索引

        Args:
            disease_keywords: 疾病關鍵詞清單

        Returns:
            段落索引集合
        """
        indices = set()
        for i, para in enumerate(self.paragraphs):
            para_lower = para.lower()
            if any(kw in para or kw.lower() in para_lower for kw in disease_keywords):
                indices.add(i)
        return indices

    def extract_text_from_indices(self, indices: Set[int]) -> str:
        """
        從指定的段落索引提取文本

        Args:
            indices: 段落索引集合

        Returns:
            合併後的文本
        """
        texts = []
        for idx in sorted(indices):
            texts.append(self.paragraphs[idx])
        return '\n'.join(texts)

    def extract_drugs_from_text(self, text: str) -> Set[str]:
        """
        從文本中提取藥物名稱

        Strategy:
        1. 尋找括號內的名稱（商品名）
        2. 尋找大寫字母開頭的詞
        3. 尋找特定的藥物名模式

        Args:
            text: 原始文本

        Returns:
            藥物名稱集合
        """
        drugs = set()

        # Strategy 1: 括號內的藥物名（商品名）
        # 例如: trastuzumab (Herceptin)
        pattern1 = r'\(([A-Z][a-zA-Z0-9\-/]+)\)'
        matches = re.findall(pattern1, text)
        for match in matches:
            if 3 <= len(match) <= 50 and not match.isupper():
                drugs.add(match)

        # Strategy 2: 英文藥物名（大寫開頭，通常是單詞或複合詞）
        # 例如: Trastuzumab, HER2-positive
        pattern2 = r'\b([A-Z][a-z]+(?:[\-/][A-Z]?[a-z]+)*)\b'
        matches = re.findall(pattern2, text)
        for match in matches:
            if 4 <= len(match) <= 50:
                # 過濾掉常見的非藥物詞
                if not match in ['Gn', 'RH', 'Gg', 'GLP', 'BID', 'OR', 'AND', 'CD', 'ER', 'PR', 'HER']:
                    drugs.add(match)

        # Strategy 3: 特定的中文藥物名模式
        pattern3 = r'([a-zA-Z0-9]+酸|[a-zA-Z0-9]+鹽|[a-zA-Z0-9]+脂|[a-zA-Z0-9]+酯)'
        matches = re.findall(pattern3, text)
        for match in matches:
            if 3 <= len(match) <= 50:
                drugs.add(match)

        # Strategy 4: 以 "-" 或 "/" 分隔的多個藥物名
        # 例如: Lapatinib, Trastuzumab emtansine, Trastuzumab deruxtecan
        pattern4 = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:[\s/,]+[A-Z][a-z]+)*)'
        matches = re.findall(pattern4, text)
        for match in matches:
            if 4 <= len(match) <= 100 and not ' ' in match and not match.isupper():
                drugs.add(match)

        return drugs

    def extract_all_drugs(self) -> Dict[str, Set[str]]:
        """
        提取乳癌和血液腫瘤的所有藥物

        Returns:
            {
                'breast': Set[drug_names],
                'heme': Set[drug_names]
            }
        """

        # 乳癌關鍵詞 - 廣泛且包容性強
        breast_keywords = [
            '乳癌', 'breast', 'HER2', 'HR', 'ER', 'PR',
            'trastuzumab', 'pertuzumab', 'lapatinib',
            'paclitaxel', 'docetaxel', 'doxorubicin',
            'tamoxifen', 'fulvestrant', 'letrozole', 'anastrozole',
            'aromatase', 'CDK4/6', 'palbociclib', 'ribociclib',
            'endocrine'
        ]

        # 血液腫瘤關鍵詞 - 廣泛且包容性強
        heme_keywords = [
            '淋巴', 'lymphoma', '血癌', 'leukemia', '骨髓瘤', 'myeloma',
            'NHL', 'HL', 'Hodgkin', 'non-Hodgkin',
            'rituximab', 'bortezomib', 'lenalidomide', 'pomalidomide',
            'venetoclax', 'ibrutinib', 'dasatinib', 'nilotinib',
            'AML', 'CLL', 'CML', 'ALL',
            'acute myeloid', 'chronic', 'Burkitt'
        ]

        # 提取相關段落
        breast_indices = self.find_disease_sections(breast_keywords)
        heme_indices = self.find_disease_sections(heme_keywords)

        print(f"[*] Found {len(breast_indices)} breast cancer related paragraphs")
        print(f"[*] Found {len(heme_indices)} hematologic related paragraphs")

        # 提取文本
        breast_text = self.extract_text_from_indices(breast_indices)
        heme_text = self.extract_text_from_indices(heme_indices)

        # 提取藥物
        breast_drugs = self.extract_drugs_from_text(breast_text)
        heme_drugs = self.extract_drugs_from_text(heme_text)

        print(f"[*] Extracted {len(breast_drugs)} unique breast cancer drugs")
        print(f"[*] Extracted {len(heme_drugs)} unique hematologic drugs")

        return {
            'breast': breast_drugs,
            'heme': heme_drugs
        }


def main():
    print("=" * 70)
    print("Comprehensive NHI Drug Parser")
    print("=" * 70)

    parser = ComprehensiveDocxParser("完整給付規定1150323.docx")
    print(f"\n[*] Loaded {len(parser.paragraphs)} paragraphs")

    # Extract drugs
    print("\n[STEP 1] Finding disease-related sections...")
    print("[STEP 2] Extracting drug names...")

    drugs = parser.extract_all_drugs()

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\n[Breast Cancer Drugs] Total: {len(drugs['breast'])}")
    for i, drug in enumerate(sorted(drugs['breast'])[:30], 1):
        print(f"  {i:2d}. {drug}")

    print(f"\n[Hematologic Malignancy Drugs] Total: {len(drugs['heme'])}")
    for i, drug in enumerate(sorted(drugs['heme'])[:30], 1):
        print(f"  {i:2d}. {drug}")

    # Save to database
    print("\n[STEP 3] Saving to database...")

    db_path = "nhi_drug_coverage.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear old data
    cursor.execute("DELETE FROM coverage_rules")
    cursor.execute("DELETE FROM drugs")
    conn.commit()

    # Insert breast cancer drugs
    breast_count = 0
    for drug_name in sorted(drugs['breast']):
        try:
            cursor.execute(
                """INSERT INTO drugs (generic_name, specialty_id, created_date)
                   VALUES (?, ?, ?)""",
                (drug_name, 'oncology_breast', datetime.now().date())
            )
            breast_count += 1
        except:
            pass

    # Insert hematologic drugs
    heme_count = 0
    for drug_name in sorted(drugs['heme']):
        try:
            cursor.execute(
                """INSERT INTO drugs (generic_name, specialty_id, created_date)
                   VALUES (?, ?, ?)""",
                (drug_name, 'oncology_heme', datetime.now().date())
            )
            heme_count += 1
        except:
            pass

    conn.commit()
    conn.close()

    print(f"  Inserted {breast_count} breast cancer drugs")
    print(f"  Inserted {heme_count} hematologic drugs")

    print("\n" + "=" * 70)
    print(f"Total drugs in database: {breast_count + heme_count}")
    print("=" * 70)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Final NHI Drug Parser - Production Version
結合多個策略來精確提取藥物名稱
"""

import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
from datetime import datetime
from typing import List, Dict, Set

class FinalDrugParser:
    """最終版本的藥物解析器"""

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

    def find_numbered_drugs(self, sections: Set[int]) -> Set[str]:
        """
        從段落中找出以數字開頭的藥物項目

        Format: "1. 藥物名..." 或 "1. 藥物名 - 條件..."
        """
        drugs = set()
        pattern = r'^(\d+)\.\s+([^:\-\n]{8,100}?)(?:\s*[-:：]|$)'

        for idx in sections:
            para = self.paragraphs[idx]
            match = re.match(pattern, para)
            if match:
                drug_name = match.group(2).strip()
                # 過濾掉太短的項目
                if len(drug_name) > 5:
                    drugs.add(drug_name)

        return drugs

    def find_parenthetical_drugs(self, text: str) -> Set[str]:
        """
        從括號內找出商品名或其他名稱

        Format: "generic name (Brand Name)"
        """
        drugs = set()

        # 尋找 (Name) 模式
        pattern = r'\(([A-Za-z][A-Za-z0-9\-/\s]{3,40}?)\)'
        matches = re.findall(pattern, text)

        for match in matches:
            match = match.strip()
            if 4 <= len(match) <= 50 and not match.isupper():
                drugs.add(match)

        return drugs

    def find_english_drug_names(self, text: str) -> Set[str]:
        """
        識別已知的英文藥物名模式

        包括：
        - 以藥物名後綴結尾的詞 (mab, inib, etc.)
        - 已知的商品名
        - 包含數字的藥物名
        """
        drugs = set()

        # 已知的藥物名後綴
        suffixes = ['mab', 'umab', 'inib', 'ib', 'cept', 'tecan', 'pine', 'dine']

        # 尋找以這些後綴結尾的詞
        for suffix in suffixes:
            pattern = r'\b([A-Z][a-z]+' + suffix + r')\b'
            matches = re.findall(pattern, text)
            drugs.update(matches)

        # 尋找包含數字的藥物名 (如 CD20, HER2, mTOR等)
        pattern = r'\b([A-Z]{2,3}[0-9]+)\b'
        matches = re.findall(pattern, text)
        drugs.update(matches)

        # 已知的常見商品名和通用名
        known_drugs = {
            'Trastuzumab', 'Pertuzumab', 'Lapatinib', 'Paclitaxel', 'Docetaxel',
            'Doxorubicin', 'Tamoxifen', 'Fulvestrant', 'Letrozole', 'Anastrozole',
            'Palbociclib', 'Ribociclib', 'Alpelisib', 'Everolimus', 'Gemcitabine',
            'Capecitabine', 'Fluorouracil', '5FU', 'CMF',
            'Rituximab', 'Bortezomib', 'Lenalidomide', 'Pomalidomide',
            'Venetoclax', 'Ibrutinib', 'Dasatinib', 'Nilotinib', 'Imatinib',
            'Azacitidine', 'Vidaza', 'Decitabine', 'Bendamustine',
            'Fludarabine', 'Cladribine', 'Pentostatin', 'Arsenic',
            'ATRA', 'Tretinoin', 'Arsenic', 'Ido', 'Mitoxantrone',
            'Daunorubicin', 'Daunomycin', 'Cytarabine', 'Etoposide',
            'Mesna', 'Cisplatin', 'Carboplatin', 'Oxaliplatin'
        }

        for known_drug in known_drugs:
            if known_drug in text:
                drugs.add(known_drug)

        return drugs

    def extract_all_drugs(self) -> Dict[str, Set[str]]:
        """
        提取所有乳癌和血液腫瘤藥物

        使用多個策略：
        1. 數字開頭的項目
        2. 括號內的名稱
        3. 英文藥物名模式
        """

        breast_keywords = [
            '乳癌', 'breast', 'HER2', 'HR', 'trastuzumab', 'pertuzumab',
            'lapatinib', 'paclitaxel', 'tamoxifen', 'aromatase', 'CDK4'
        ]

        heme_keywords = [
            '淋巴', 'lymphoma', '血癌', 'leukemia', '骨髓瘤', 'myeloma',
            'NHL', 'HL', 'rituximab', 'bortezomib', 'venetoclax', 'ibrutinib',
            'AML', 'CLL', 'CML'
        ]

        # 找出相關段落
        breast_sections = {i for i, p in enumerate(self.paragraphs)
                          if any(kw in p or kw.lower() in p.lower() for kw in breast_keywords)}
        heme_sections = {i for i, p in enumerate(self.paragraphs)
                        if any(kw in p or kw.lower() in p.lower() for kw in heme_keywords)}

        print(f"[*] Breast cancer paragraphs: {len(breast_sections)}")
        print(f"[*] Hematologic paragraphs: {len(heme_sections)}")

        # 提取文本
        breast_text = '\n'.join(self.paragraphs[i] for i in breast_sections)
        heme_text = '\n'.join(self.paragraphs[i] for i in heme_sections)

        # Strategy 1: 數字開頭的項目
        breast_drugs_1 = self.find_numbered_drugs(breast_sections)
        heme_drugs_1 = self.find_numbered_drugs(heme_sections)

        print(f"[Strategy 1 - Numbered items]")
        print(f"  Breast: {len(breast_drugs_1)}")
        print(f"  Heme: {len(heme_drugs_1)}")

        # Strategy 2: 括號內的名稱
        breast_drugs_2 = self.find_parenthetical_drugs(breast_text)
        heme_drugs_2 = self.find_parenthetical_drugs(heme_text)

        print(f"[Strategy 2 - Parenthetical names]")
        print(f"  Breast: {len(breast_drugs_2)}")
        print(f"  Heme: {len(heme_drugs_2)}")

        # Strategy 3: 英文藥物名模式
        breast_drugs_3 = self.find_english_drug_names(breast_text)
        heme_drugs_3 = self.find_english_drug_names(heme_text)

        print(f"[Strategy 3 - English drug patterns]")
        print(f"  Breast: {len(breast_drugs_3)}")
        print(f"  Heme: {len(heme_drugs_3)}")

        # 合併結果（去重）
        breast_drugs = breast_drugs_1 | breast_drugs_2 | breast_drugs_3
        heme_drugs = heme_drugs_1 | heme_drugs_2 | heme_drugs_3

        return {
            'breast': breast_drugs,
            'heme': heme_drugs
        }


def main():
    print("=" * 70)
    print("Final NHI Drug Parser")
    print("=" * 70)

    parser = FinalDrugParser("完整給付規定1150323.docx")
    print(f"\n[*] Loaded {len(parser.paragraphs)} paragraphs\n")

    print("[EXTRACTING DRUGS]")
    drugs = parser.extract_all_drugs()

    print(f"\n[FINAL RESULTS]")
    print(f"Breast Cancer drugs: {len(drugs['breast'])}")
    print(f"Hematologic drugs: {len(drugs['heme'])}")
    print(f"Total: {len(drugs['breast']) + len(drugs['heme'])}")

    # Save to database
    print(f"\n[SAVING TO DATABASE]")

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

    print(f"Inserted: {breast_count} breast cancer + {heme_count} hematologic")

    print("\n" + "=" * 70)
    print("Complete! Database ready for querying.")
    print("=" * 70)


if __name__ == '__main__':
    main()

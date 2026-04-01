#!/usr/bin/env python3
"""
Enhanced Breast Cancer Drug Parser
針對乳癌藥物的強化版提取器
"""

import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
from datetime import datetime
from typing import Set, Dict
from known_oncology_drugs import BREAST_CANCER_DRUGS

class EnhancedBreastParser:
    """乳癌藥物強化提取器"""

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

    def find_breast_sections(self) -> Set[int]:
        """找出所有乳癌相關段落"""
        breast_keywords = [
            # 乳癌相關
            '乳癌', 'breast', 'Breast', 'cancer',
            # 受體狀態
            'HER2', 'HR', 'ER', 'PR', 'estrogen', 'progesterone', 'receptor',
            # 常見藥物和治療
            'trastuzumab', 'pertuzumab', 'lapatinib', 'paclitaxel', 'docetaxel',
            'doxorubicin', 'tamoxifen', 'fulvestrant', 'letrozole', 'anastrozole',
            'aromatase', 'palbociclib', 'ribociclib', 'alpelisib',
            'bevacizumab', 'everolimus', 'capecitabine', 'herceptin',
            'CDK4', 'CDK6', 'PIK3CA',
            # 其他相關詞
            'endocrine', 'hormone', 'triple-negative', 'HER2-positive',
            'metastatic', 'advanced', 'adjuvant', 'neoadjuvant',
        ]

        indices = set()
        for i, para in enumerate(self.paragraphs):
            para_lower = para.lower()
            for kw in breast_keywords:
                if kw.lower() in para_lower:
                    indices.add(i)
                    break
        return indices

    def extract_known_drugs(self, text: str) -> Set[str]:
        """從已知藥物列表中提取"""
        drugs = set()
        for drug in BREAST_CANCER_DRUGS:
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

        # 尋找包含數字的藥物名
        pattern = r'\b([A-Z]{2,4}[0-9]+)\b'
        matches = re.findall(pattern, text)
        drugs.update(matches)

        # 尋找括號內的商品名
        pattern = r'\(([A-Z][A-Za-z0-9\-/\s]{3,30}?)\)'
        matches = re.findall(pattern, text)
        for match in matches:
            match = match.strip()
            if 4 <= len(match) <= 40 and not match.isupper():
                match = re.sub(r'^[\(\)\[\]\{\}0-9\s]+', '', match).strip()
                if match and match[0].isalpha():
                    drugs.add(match)

        return drugs

    def filter_valid_drugs(self, raw_drugs: Set[str]) -> Set[str]:
        """過濾出真實的乳癌藥物"""
        # 明確排除的項目
        explicit_exclude = {
            'Breast', 'Cancer', 'HER2', 'HR', 'ER', 'PR',
            'CDK4', 'CDK6', 'PIK3CA', 'CD',
            'Philadelphia', 'Philadelphiachromosome',
            'BRCA1', 'BRCA2', 'CH50', 'HbA1c', 'IHC1', 'IHC3',
            'Hypersplenism', 'Cephradine', 'Cryoprecipitate', 'DMARDs',
            'Dexmedetomidine', 'Lamidine', 'Tolterodine', 'Ustekinumab',
            'Atherothrombotic', 'Avascular', 'Dropout', 'Erythema nodosum',
            'Lipid', 'MFM32', 'Neisseria meningitis', 'Qmax', 'Seizure',
            'Valsalva', 'Xeloda', 'Lamivudine',
            'Luspatercept', 'Tofacitinib', 'Tofacitinib XR',
            'Certolizumab', 'Cimzia', 'Etanercept', 'Satralizumab',
            'Secukinumab',
        }

        # 排除的詞彙
        exclude_words = {
            'cancer', 'breast', 'disease', 'syndrome',
            'response', 'progression', 'burden',
            'agent', 'blocker', 'agonist', 'antagonist',
            'receptor', 'factor', 'protein', 'antigen', 'antibody',
            'mutation', 'translocation', 'polymerase', 'nucleotide',
            'kinase', 'chromosome',
            'allele', 'gene', 'variant', 'wildtype', 'wild-type',
            'score', 'scale', 'index', 'classification', 'staging',
            'criteria', 'guideline', 'protocol', 'regimen', 'schedule',
            'cycle', 'phase', 'line', 'therapy', 'treatment',
            'remission', 'relapse', 'refractory',
            'workshop', 'conference', 'committee', 'society',
            'hormone', 'endocrine',
            'event', 'maneuver', 'profile', 'cluster', 'zone',
            'analogues', 'based', 'esrd',
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

            # 排除明顯的臨床名詞
            if any(char in drug for char in ['淋', '癌', '瘤', '血', '球']):
                continue

            valid_drugs.add(drug)

        return valid_drugs

    def extract_breast_drugs(self) -> Set[str]:
        """提取所有乳癌藥物"""
        # 找出相關段落
        breast_indices = self.find_breast_sections()
        print(f"[*] Found {len(breast_indices)} breast-cancer-related paragraphs")

        # 合併成文本
        breast_text = '\n'.join(self.paragraphs[i] for i in breast_indices)

        # Strategy 1: 使用已知藥物列表
        known_drugs = self.extract_known_drugs(breast_text)
        print(f"[*] Known drugs found: {len(known_drugs)}")

        # Strategy 2: 使用模式提取
        pattern_drugs = self.extract_drug_patterns(breast_text)
        print(f"[*] Pattern-based drugs: {len(pattern_drugs)}")

        # 合併並過濾
        all_drugs = known_drugs | pattern_drugs
        filtered_drugs = self.filter_valid_drugs(all_drugs)

        print(f"[*] After filtering: {len(filtered_drugs)}")

        return filtered_drugs


def main():
    print("=" * 70)
    print("Enhanced Breast Cancer Drug Parser")
    print("=" * 70)

    parser = EnhancedBreastParser("完整給付規定1150323.docx")
    print(f"\n[*] Loaded {len(parser.paragraphs)} paragraphs\n")

    print("[EXTRACTING BREAST CANCER DRUGS]")
    breast_drugs = parser.extract_breast_drugs()

    print(f"\n[RESULTS]")
    print(f"Total breast cancer drugs extracted: {len(breast_drugs)}\n")
    print("Extracted drugs:")
    for i, drug in enumerate(sorted(breast_drugs), 1):
        print(f"  {i:2d}. {drug}")

    # 將結果保存到數據庫
    print(f"\n[SAVING TO DATABASE]")
    db_path = "nhi_drug_coverage.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 只清空乳癌藥物表
    cursor.execute("DELETE FROM coverage_rules WHERE drug_id IN (SELECT id FROM drugs WHERE specialty_id = 'oncology_breast')")
    cursor.execute("DELETE FROM drugs WHERE specialty_id = 'oncology_breast'")
    conn.commit()

    # 插入新藥物
    inserted = 0
    for drug_name in sorted(breast_drugs):
        try:
            cursor.execute(
                """INSERT INTO drugs (generic_name, specialty_id, created_date)
                   VALUES (?, ?, ?)""",
                (drug_name, 'oncology_breast', datetime.now().date())
            )
            inserted += 1
        except Exception as e:
            print(f"    Error inserting {drug_name}: {e}")

    conn.commit()
    conn.close()

    print(f"Inserted {inserted} breast cancer drugs into database")

    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()

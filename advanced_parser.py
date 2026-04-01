#!/usr/bin/env python3
"""
Advanced NHI Drug Coverage Parser
利用表格和更精確的文本分析
"""

import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
import json
from datetime import datetime
from typing import List, Dict

class AdvancedDocxParser:
    """進階 DOCX 解析器"""

    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.paragraphs = []
        self.tables = []
        self._load_docx()

    def _load_docx(self):
        """載入 DOCX 並完全解析"""
        with zipfile.ZipFile(self.docx_path, 'r') as z:
            xml_data = z.read('word/document.xml').decode('utf-8', errors='ignore')

        root = ET.fromstring(xml_data.encode('utf-8', errors='ignore'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        # 提取所有段落
        for para in root.findall('.//w:p', ns):
            text_elements = para.findall('.//w:t', ns)
            text = ''.join([t.text for t in text_elements if t.text])
            if text.strip():
                self.paragraphs.append(text.strip())

        # 提取所有表格
        for table in root.findall('.//w:tbl', ns):
            rows = table.findall('.//w:tr', ns)
            table_data = []
            for row in rows:
                cells = row.findall('.//w:tc', ns)
                cell_texts = []
                for cell in cells:
                    texts = cell.findall('.//w:t', ns)
                    text = ''.join([t.text for t in texts if t.text])
                    cell_texts.append(text.strip())
                table_data.append(cell_texts)
            if table_data and len(table_data[0]) > 0:
                self.tables.append(table_data)

    def extract_drugs_context_based(self, disease_keywords: List[str]) -> List[Dict]:
        """
        基於疾病關鍵詞和上下文提取藥物

        Args:
            disease_keywords: 疾病關鍵詞列表

        Returns:
            藥物列表
        """
        drugs = []

        # 尋找包含疾病關鍵詞的段落索引
        disease_indices = set()
        for i, para in enumerate(self.paragraphs):
            if any(kw in para for kw in disease_keywords):
                disease_indices.add(i)

        # 在這些索引附近尋找藥物列表項
        drug_pattern = r'^(\d+)\.\s+([^\n:-]+?)(?:\s+[-:：]|$)'

        for disease_idx in sorted(disease_indices):
            # 檢查前後 20 個段落
            start = max(0, disease_idx - 20)
            end = min(len(self.paragraphs), disease_idx + 20)

            for para_idx in range(start, end):
                para = self.paragraphs[para_idx]
                match = re.match(drug_pattern, para)

                if match:
                    drug_name = match.group(2).strip()

                    # 過濾掉太短或非藥物的條目
                    if len(drug_name) > 2 and not re.match(r'^[（(].*[）)]$', drug_name):
                        # 提取療法線信息
                        therapy_line = None
                        if '一線' in para or 'first' in para.lower():
                            therapy_line = 1
                        elif '二線' in para or 'second' in para.lower():
                            therapy_line = 2
                        elif '三線' in para or 'third' in para.lower():
                            therapy_line = 3

                        # 檢查是否已存在
                        existing = any(d['name'] == drug_name for d in drugs)

                        if not existing:
                            drugs.append({
                                'name': drug_name,
                                'trade_names': [],
                                'therapy_line': therapy_line,
                                'indication': '',
                                'raw_text': para,
                                'para_index': para_idx
                            })

        # 去除重複並排序
        seen = set()
        unique_drugs = []
        for drug in drugs:
            key = drug['name'].lower()
            if key not in seen and len(drug['name'].strip()) > 2:
                seen.add(key)
                unique_drugs.append(drug)

        return unique_drugs

    def extract_from_tables(self) -> List[Dict]:
        """從表格中提取藥物信息"""
        drugs = []

        for table_idx, table in enumerate(self.tables):
            # 假設第一行是標題
            if len(table) < 2:
                continue

            headers = table[0]

            # 尋找藥物名稱列
            drug_col = None
            for i, header in enumerate(headers):
                if any(kw in header for kw in ['藥物', '藥品', 'Drug', 'name']):
                    drug_col = i
                    break

            if drug_col is None and len(headers) > 0:
                drug_col = 0  # 預設第一列

            # 提取藥物
            for row_idx in range(1, len(table)):
                row = table[row_idx]
                if drug_col < len(row):
                    drug_name = row[drug_col].strip()
                    if drug_name and len(drug_name) > 2:
                        drugs.append({
                            'name': drug_name,
                            'trade_names': [],
                            'table_idx': table_idx,
                            'row_idx': row_idx,
                            'full_row': row
                        })

        return drugs


class NHIDatabase:
    """資料庫操作"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def insert_drug(self,
                   generic_name: str,
                   specialty_id: str,
                   trade_names: List[str] = None,
                   indication: str = None,
                   nhi_id: str = None) -> int:
        """插入藥物"""

        self.cursor.execute(
            """INSERT OR IGNORE INTO drugs
               (generic_name, trade_names, specialty_id, indication, created_date, nhi_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                generic_name,
                json.dumps(trade_names or []),
                specialty_id,
                indication,
                datetime.now().date(),
                nhi_id
            )
        )
        self.conn.commit()

        # 獲取 ID
        self.cursor.execute("SELECT id FROM drugs WHERE generic_name = ? AND specialty_id = ?",
                           (generic_name, specialty_id))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def insert_coverage_rule(self,
                           drug_id: int,
                           therapy_line: int = None,
                           condition: str = None):
        """插入給付規定"""
        if drug_id:
            self.cursor.execute(
                """INSERT INTO coverage_rules
                   (drug_id, therapy_line, condition)
                   VALUES (?, ?, ?)""",
                (drug_id, therapy_line, condition)
            )
            self.conn.commit()

    def get_drug_count(self, specialty_id: str) -> int:
        """獲取科別的藥物數量"""
        self.cursor.execute(
            "SELECT COUNT(*) FROM drugs WHERE specialty_id = ?",
            (specialty_id,)
        )
        return self.cursor.fetchone()[0]

    def close(self):
        """關閉連接"""
        self.conn.close()


def main():
    print("=" * 70)
    print("Advanced NHI Drug Coverage Parser")
    print("=" * 70)

    # Parse DOCX
    print("\n[1] Parsing DOCX (Advanced)...")
    parser = AdvancedDocxParser("完整給付規定1150323.docx")
    print(f"    Loaded {len(parser.paragraphs)} paragraphs, {len(parser.tables)} tables")

    # Extract drugs by disease keywords
    print("\n[2] Extracting drugs by disease keywords...")

    breast_keywords = ['乳癌', 'breast', 'HER2', 'ER', 'PR']
    heme_keywords = ['淋巴', 'lymphoma', '血癌', 'leukemia', '骨髓瘤', 'myeloma', 'NHL', 'HL']

    breast_drugs = parser.extract_drugs_context_based(breast_keywords)
    heme_drugs = parser.extract_drugs_context_based(heme_keywords)

    print(f"    Breast Cancer drugs: {len(breast_drugs)}")
    print(f"    Hematologic drugs: {len(heme_drugs)}")

    # Insert into database
    print("\n[3] Inserting into database...")

    db = NHIDatabase("nhi_drug_coverage.db")

    breast_inserted = 0
    for drug in breast_drugs:
        drug_id = db.insert_drug(
            generic_name=drug['name'],
            specialty_id='oncology_breast',
            indication=drug['indication']
        )
        if drug_id:
            db.insert_coverage_rule(drug_id, therapy_line=drug.get('therapy_line'))
            breast_inserted += 1

    heme_inserted = 0
    for drug in heme_drugs:
        drug_id = db.insert_drug(
            generic_name=drug['name'],
            specialty_id='oncology_heme',
            indication=drug['indication']
        )
        if drug_id:
            db.insert_coverage_rule(drug_id, therapy_line=drug.get('therapy_line'))
            heme_inserted += 1

    print(f"    Breast Cancer inserted: {breast_inserted}")
    print(f"    Hematologic inserted: {heme_inserted}")

    # Show summary
    print("\n[4] Database Summary...")
    breast_total = db.get_drug_count('oncology_breast')
    heme_total = db.get_drug_count('oncology_heme')

    print(f"    Total Breast Cancer drugs: {breast_total}")
    print(f"    Total Hematologic drugs: {heme_total}")

    # Show samples
    print("\n[5] Sample drugs extracted:")

    if breast_drugs:
        print("\n    Breast Cancer (first 5):")
        for drug in breast_drugs[:5]:
            print(f"      - {drug['name'][:60]}")

    if heme_drugs:
        print("\n    Hematologic (first 5):")
        for drug in heme_drugs[:5]:
            print(f"      - {drug['name'][:60]}")

    db.close()

    print("\n" + "=" * 70)
    print("Parsing complete! Database: nhi_drug_coverage.db")
    print("=" * 70)


if __name__ == '__main__':
    main()

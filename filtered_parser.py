#!/usr/bin/env python3
"""
NHI Drug Parser with Smart Filtering
Combines final_parser extraction with smart_filter for better accuracy
"""

import zipfile
import xml.etree.ElementTree as ET
import sqlite3
import re
from datetime import datetime
from typing import List, Dict, Set
from smart_filter import DrugNameFilter

class FilteredDrugParser:
    """Parser with built-in smart filtering"""

    def __init__(self, docx_path: str):
        self.docx_path = docx_path
        self.paragraphs = []
        self.filter = DrugNameFilter()
        self._load_docx()

    def _load_docx(self):
        """Load DOCX"""
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
        """Extract numbered list items"""
        drugs = set()
        pattern = r'^(\d+)\.\s+([^:\-\n]{8,100}?)(?:\s*[-:：]|$)'

        for idx in sections:
            para = self.paragraphs[idx]
            match = re.match(pattern, para)
            if match:
                drug_name = match.group(2).strip()
                # Clean leading non-alphabetic characters
                drug_name = re.sub(r'^[\(\)\[\]\{\}0-9]+', '', drug_name).strip()
                if len(drug_name) > 5 and drug_name and drug_name[0].isalpha():
                    drugs.add(drug_name)

        return drugs

    def find_parenthetical_drugs(self, text: str) -> Set[str]:
        """Extract brand names from parentheses"""
        drugs = set()
        pattern = r'\(([A-Za-z][A-Za-z0-9\-/\s]{3,40}?)\)'
        matches = re.findall(pattern, text)

        for match in matches:
            match = match.strip()
            # Clean leading non-alphabetic characters
            match = re.sub(r'^[\(\)\[\]\{\}0-9]+', '', match).strip()
            if 4 <= len(match) <= 50 and not match.isupper() and len(match) > 0 and match[0].isalpha():
                drugs.add(match)

        return drugs

    def find_english_drug_names(self, text: str) -> Set[str]:
        """Identify known drug name patterns"""
        drugs = set()
        suffixes = ['mab', 'umab', 'inib', 'ib', 'cept', 'tecan', 'pine', 'dine']

        for suffix in suffixes:
            pattern = r'\b([A-Z][a-z]+' + suffix + r')\b'
            matches = re.findall(pattern, text)
            drugs.update(matches)

        pattern = r'\b([A-Z]{2,3}[0-9]+)\b'
        matches = re.findall(pattern, text)
        drugs.update(matches)

        known_drugs = {
            'Trastuzumab', 'Pertuzumab', 'Lapatinib', 'Paclitaxel', 'Docetaxel',
            'Doxorubicin', 'Tamoxifen', 'Fulvestrant', 'Letrozole', 'Anastrozole',
            'Palbociclib', 'Ribociclib', 'Alpelisib', 'Everolimus', 'Gemcitabine',
            'Capecitabine', 'Fluorouracil', '5FU', 'CMF',
            'Rituximab', 'Bortezomib', 'Lenalidomide', 'Pomalidomide',
            'Venetoclax', 'Ibrutinib', 'Dasatinib', 'Nilotinib', 'Imatinib',
            'Azacitidine', 'Vidaza', 'Decitabine', 'Bendamustine',
            'Fludarabine', 'Cladribine', 'Pentostatin', 'Arsenic',
            'ATRA', 'Tretinoin', 'Ido', 'Mitoxantrone',
            'Daunorubicin', 'Daunomycin', 'Cytarabine', 'Etoposide',
            'Mesna', 'Cisplatin', 'Carboplatin', 'Oxaliplatin',
            'Bevacizumab', 'Avastin', 'Herceptin'
        }

        for known_drug in known_drugs:
            if known_drug in text:
                drugs.add(known_drug)

        return drugs

    def extract_all_drugs(self) -> Dict[str, Set[str]]:
        """Extract and filter all drugs"""

        breast_keywords = [
            'breast', 'HER2', 'HR', 'ER', 'PR',
            'trastuzumab', 'pertuzumab', 'lapatinib',
            'paclitaxel', 'docetaxel', 'doxorubicin',
            'tamoxifen', 'fulvestrant', 'letrozole', 'anastrozole',
            'aromatase', 'palbociclib', 'ribociclib'
        ]

        heme_keywords = [
            'lymphoma', 'leukemia', 'myeloma',
            'NHL', 'HL', 'Hodgkin',
            'rituximab', 'bortezomib', 'lenalidomide', 'pomalidomide',
            'venetoclax', 'ibrutinib', 'dasatinib', 'nilotinib',
            'AML', 'CLL', 'CML', 'ALL'
        ]

        breast_sections = {i for i, p in enumerate(self.paragraphs)
                          if any(kw in p or kw.lower() in p.lower() for kw in breast_keywords)}
        heme_sections = {i for i, p in enumerate(self.paragraphs)
                        if any(kw in p or kw.lower() in p.lower() for kw in heme_keywords)}

        print(f"[*] Breast cancer paragraphs: {len(breast_sections)}")
        print(f"[*] Hematologic paragraphs: {len(heme_sections)}")

        breast_text = '\n'.join(self.paragraphs[i] for i in breast_sections)
        heme_text = '\n'.join(self.paragraphs[i] for i in heme_sections)

        # Extract drugs using all three strategies
        breast_drugs_1 = self.find_numbered_drugs(breast_sections)
        heme_drugs_1 = self.find_numbered_drugs(heme_sections)

        breast_drugs_2 = self.find_parenthetical_drugs(breast_text)
        heme_drugs_2 = self.find_parenthetical_drugs(heme_text)

        breast_drugs_3 = self.find_english_drug_names(breast_text)
        heme_drugs_3 = self.find_english_drug_names(heme_text)

        # Combine (before filtering)
        breast_drugs_raw = breast_drugs_1 | breast_drugs_2 | breast_drugs_3
        heme_drugs_raw = heme_drugs_1 | heme_drugs_2 | heme_drugs_3

        print(f"[*] Raw extraction: {len(breast_drugs_raw)} breast, {len(heme_drugs_raw)} heme")

        # Apply smart filter
        breast_drugs = self.filter.filter_drugs(breast_drugs_raw)
        heme_drugs = self.filter.filter_drugs(heme_drugs_raw)

        print(f"[*] After filtering: {len(breast_drugs)} breast, {len(heme_drugs)} heme")

        return {
            'breast': breast_drugs,
            'heme': heme_drugs
        }


def main():
    print("=" * 70)
    print("NHI Drug Parser with Smart Filtering")
    print("=" * 70)

    parser = FilteredDrugParser("完整給付規定1150323.docx")
    print(f"\n[*] Loaded {len(parser.paragraphs)} paragraphs\n")

    print("[EXTRACTING AND FILTERING DRUGS]")
    drugs = parser.extract_all_drugs()

    print(f"\n[FINAL RESULTS]")
    print(f"Breast Cancer drugs: {len(drugs['breast'])}")
    for drug in sorted(drugs['breast'])[:20]:
        print(f"  - {drug}")
    if len(drugs['breast']) > 20:
        print(f"  ... and {len(drugs['breast']) - 20} more")

    print(f"\nHematologic drugs: {len(drugs['heme'])}")
    for drug in sorted(drugs['heme'])[:20]:
        print(f"  - {drug}")
    if len(drugs['heme']) > 20:
        print(f"  ... and {len(drugs['heme']) - 20} more")

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

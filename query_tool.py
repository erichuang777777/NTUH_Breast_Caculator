#!/usr/bin/env python3
"""
NHI Drug Coverage Query Tool
醫師用查詢工具 - 快速查詢藥物給付規定
"""

import sqlite3
import json
from typing import List, Dict, Optional

class DrugQueryTool:
    """藥物查詢工具"""

    def __init__(self, db_path: str = "nhi_drug_coverage.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def search_drugs(self, specialty: str, keyword: str = None) -> List[Dict]:
        """
        搜尋藥物

        Args:
            specialty: 'breast' 或 'heme'
            keyword: 藥物名稱關鍵詞

        Returns:
            藥物列表
        """

        specialty_map = {'breast': 'oncology_breast', 'heme': 'oncology_heme'}
        specialty_id = specialty_map.get(specialty)

        if not specialty_id:
            return []

        if keyword:
            self.cursor.execute(
                """SELECT id, generic_name, indication FROM drugs
                   WHERE specialty_id = ? AND generic_name LIKE ?
                   ORDER BY generic_name""",
                (specialty_id, f'%{keyword}%')
            )
        else:
            self.cursor.execute(
                """SELECT id, generic_name, indication FROM drugs
                   WHERE specialty_id = ?
                   ORDER BY generic_name""",
                (specialty_id,)
            )

        return [
            {
                'id': row[0],
                'name': row[1],
                'indication': row[2] or 'Not specified'
            }
            for row in self.cursor.fetchall()
        ]

    def get_drug_details(self, drug_id: int) -> Optional[Dict]:
        """
        獲取藥物詳細信息
        """

        self.cursor.execute(
            """SELECT d.id, d.generic_name, d.trade_names, d.indication, d.specialty_id
               FROM drugs d WHERE d.id = ?""",
            (drug_id,)
        )

        result = self.cursor.fetchone()
        if not result:
            return None

        # 獲取給付規定
        self.cursor.execute(
            """SELECT id, therapy_line, condition, exclusion, prior_auth_required
               FROM coverage_rules WHERE drug_id = ?
               ORDER BY therapy_line""",
            (drug_id,)
        )

        coverage_rules = [
            {
                'therapy_line': row[1] or 0,
                'condition': row[2] or '',
                'exclusion': row[3] or '',
                'prior_auth_required': bool(row[4])
            }
            for row in self.cursor.fetchall()
        ]

        return {
            'id': result[0],
            'name': result[1],
            'trade_names': json.loads(result[2]) if result[2] else [],
            'indication': result[3] or '',
            'specialty': result[4],
            'coverage_rules': coverage_rules
        }

    def list_all_drugs(self, specialty: str) -> List[str]:
        """列出所有藥物名稱"""

        specialty_map = {'breast': 'oncology_breast', 'heme': 'oncology_heme'}
        specialty_id = specialty_map.get(specialty)

        if not specialty_id:
            return []

        self.cursor.execute(
            """SELECT generic_name FROM drugs WHERE specialty_id = ?
               ORDER BY generic_name""",
            (specialty_id,)
        )

        return [row[0] for row in self.cursor.fetchall()]

    def get_statistics(self) -> Dict:
        """獲取統計數據"""

        self.cursor.execute("SELECT COUNT(*) FROM drugs WHERE specialty_id = 'oncology_breast'")
        breast_count = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM drugs WHERE specialty_id = 'oncology_heme'")
        heme_count = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT MAX(created_date) FROM drugs")
        last_update = self.cursor.fetchone()[0]

        return {
            'breast_cancer_drugs': breast_count,
            'hematologic_drugs': heme_count,
            'total_drugs': breast_count + heme_count,
            'last_updated': last_update
        }

    def close(self):
        """關閉連接"""
        self.conn.close()


def print_drug_info(drug: Dict):
    """格式化輸出藥物信息"""

    print("\n" + "=" * 70)
    print(f"[Drug] {drug['name']}")
    print("=" * 70)

    if drug['trade_names']:
        print(f"\nTrade Names: {', '.join(drug['trade_names'])}")

    if drug['indication']:
        print(f"\nIndication: {drug['indication'][:100]}")

    print(f"\nSpecialty: {'Breast Cancer' if drug['specialty'] == 'oncology_breast' else 'Hematologic Malignancy'}")

    if drug['coverage_rules']:
        print("\nCoverage Rules:")
        for rule in drug['coverage_rules']:
            line_name = ['Not Specified', 'First-line', 'Second-line', 'Third-line'].get(
                rule['therapy_line'], 'Unknown'
            )
            print(f"  [{line_name}]")

            if rule['condition']:
                print(f"    Condition: {rule['condition'][:80]}")

            if rule['exclusion']:
                print(f"    Exclusion: {rule['exclusion'][:80]}")

            if rule['prior_auth_required']:
                print(f"    [ATTENTION] Prior authorization required")
    else:
        print("\nNo coverage rules found")


def interactive_menu():
    """互動菜單"""

    tool = DrugQueryTool()

    while True:
        print("\n" + "=" * 70)
        print("NHI Drug Coverage Query Tool")
        print("=" * 70)

        stats = tool.get_statistics()
        print(f"\nDatabase Status:")
        print(f"  Breast Cancer drugs: {stats['breast_cancer_drugs']}")
        print(f"  Hematologic drugs: {stats['hematologic_drugs']}")
        print(f"  Total: {stats['total_drugs']}")
        print(f"  Last updated: {stats['last_updated']}")

        print("\nOptions:")
        print("  1. Search Breast Cancer drugs")
        print("  2. Search Hematologic Malignancy drugs")
        print("  3. List all drugs")
        print("  4. Get drug details")
        print("  5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == '1':
            keyword = input("Enter drug name (or press Enter for all): ").strip()
            drugs = tool.search_drugs('breast', keyword if keyword else None)

            if not drugs:
                print("\nNo drugs found")
            else:
                print(f"\nFound {len(drugs)} drug(s):")
                for i, drug in enumerate(drugs, 1):
                    print(f"  [{i}] {drug['name'][:60]}")

                drug_idx = input("\nSelect drug number (or press Enter to skip): ").strip()
                if drug_idx.isdigit() and 1 <= int(drug_idx) <= len(drugs):
                    selected = drugs[int(drug_idx) - 1]
                    details = tool.get_drug_details(selected['id'])
                    if details:
                        print_drug_info(details)

        elif choice == '2':
            keyword = input("Enter drug name (or press Enter for all): ").strip()
            drugs = tool.search_drugs('heme', keyword if keyword else None)

            if not drugs:
                print("\nNo drugs found")
            else:
                print(f"\nFound {len(drugs)} drug(s):")
                for i, drug in enumerate(drugs, 1):
                    print(f"  [{i}] {drug['name'][:60]}")

                drug_idx = input("\nSelect drug number (or press Enter to skip): ").strip()
                if drug_idx.isdigit() and 1 <= int(drug_idx) <= len(drugs):
                    selected = drugs[int(drug_idx) - 1]
                    details = tool.get_drug_details(selected['id'])
                    if details:
                        print_drug_info(details)

        elif choice == '3':
            print("\n[Breast Cancer Drugs]")
            breast_drugs = tool.list_all_drugs('breast')
            for i, drug in enumerate(breast_drugs, 1):
                print(f"  {i}. {drug}")

            print("\n[Hematologic Malignancy Drugs]")
            heme_drugs = tool.list_all_drugs('heme')
            for i, drug in enumerate(heme_drugs, 1):
                print(f"  {i}. {drug}")

        elif choice == '4':
            drug_id = input("Enter drug ID: ").strip()
            if drug_id.isdigit():
                details = tool.get_drug_details(int(drug_id))
                if details:
                    print_drug_info(details)
                else:
                    print("Drug not found")

        elif choice == '5':
            print("\nGoodbye!")
            break

        else:
            print("Invalid option")

    tool.close()


if __name__ == '__main__':
    interactive_menu()

#!/usr/bin/env python3
"""
NHI Drug Coverage Auto-Updater
自動監控和更新健保藥物給付規定
"""

import os
import urllib.request
import urllib.error
import hashlib
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from advanced_parser import AdvancedDocxParser, NHIDatabase

class NHIUpdater:
    """NHI 資料自動更新器"""

    # NHI 官網文件URL
    NHI_DOCX_URL = "https://www.nhi.gov.tw/ch/dl-61742-d2b757bab70944e6a1e54fbbc93f5bc8-1.docx"
    NHI_ODT_URL = "https://www.nhi.gov.tw/ch/dl-61740-aef3891cabc24bf0b6569fd36bddd2e0-1.odt"

    def __init__(self,
                 download_dir: str = "D:\\drug_appli",
                 db_path: str = "nhi_drug_coverage.db"):
        self.download_dir = Path(download_dir)
        self.db_path = db_path
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, filepath: str) -> str:
        """計算檔案的 MD5 雜湊值"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def check_remote_updates(self) -> dict:
        """
        檢查遠程是否有更新

        Returns:
            {
                'has_update': bool,
                'local_file': str,
                'local_hash': str,
                'remote_hash': str (or None if not available),
                'last_checked': datetime
            }
        """

        local_docx = self.download_dir / "完整給付規定.docx"
        local_hash = None

        if local_docx.exists():
            local_hash = self._get_file_hash(str(local_docx))

        result = {
            'has_update': False,
            'local_file': str(local_docx),
            'local_hash': local_hash,
            'remote_hash': None,
            'last_checked': datetime.now()
        }

        # 嘗試下載遠程檔案並比較雜湊
        try:
            print("[*] Checking remote file...")
            # 使用 urllib.request 進行 HEAD 請求以獲取檔案元資訊
            req = urllib.request.Request(self.NHI_DOCX_URL, method='HEAD')
            remote_response = urllib.request.urlopen(req, timeout=10)
            remote_headers = remote_response.headers

            # 檢查 Last-Modified 或其他指標
            last_modified = remote_headers.get('Last-Modified')
            remote_size = remote_headers.get('Content-Length')

            print(f"    Remote file size: {remote_size}")
            print(f"    Last modified: {last_modified}")

            if local_docx.exists():
                local_size = local_docx.stat().st_size
                print(f"    Local file size: {local_size}")

                if remote_size and int(remote_size) != local_size:
                    result['has_update'] = True
                    print("    [UPDATE DETECTED] File size changed!")
        except Exception as e:
            print(f"    [WARNING] Could not check remote: {e}")

        return result

    def download_latest(self) -> bool:
        """
        下載最新版本

        Returns:
            True if successful
        """

        try:
            print("[*] Downloading latest DOCX...")
            local_file = self.download_dir / "完整給付規定.docx"

            urllib.request.urlretrieve(self.NHI_DOCX_URL, str(local_file))

            print(f"    [OK] Downloaded {local_file.stat().st_size / (1024*1024):.1f} MB")
            return True

        except Exception as e:
            print(f"    [ERROR] Download failed: {e}")
            return False

    def parse_and_update_db(self, docx_path: str = None) -> bool:
        """
        解析 DOCX 並更新資料庫

        Args:
            docx_path: DOCX 檔案路徑（預設為 "完整給付規定.docx"）

        Returns:
            True if successful
        """

        if docx_path is None:
            docx_path = str(self.download_dir / "完整給付規定.docx")

        if not os.path.exists(docx_path):
            print(f"[ERROR] File not found: {docx_path}")
            return False

        try:
            print("[*] Parsing DOCX...")
            parser = AdvancedDocxParser(docx_path)
            print(f"    Loaded {len(parser.paragraphs)} paragraphs, {len(parser.tables)} tables")

            # 提取藥物
            print("[*] Extracting drugs...")
            breast_keywords = ['乳癌', 'breast', 'HER2']
            heme_keywords = ['淋巴', 'lymphoma', '血癌', 'leukemia', '骨髓瘤', 'myeloma']

            breast_drugs = parser.extract_drugs_context_based(breast_keywords)
            heme_drugs = parser.extract_drugs_context_based(heme_keywords)

            print(f"    Breast Cancer: {len(breast_drugs)} drugs")
            print(f"    Hematologic: {len(heme_drugs)} drugs")

            # 更新資料庫
            print("[*] Updating database...")
            db = NHIDatabase(self.db_path)

            # 清空舊資料（保留結構）
            db.cursor.execute("DELETE FROM coverage_rules")
            db.cursor.execute("DELETE FROM drugs")
            db.conn.commit()

            # 插入新藥物
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

            print(f"    Inserted: {breast_inserted} breast cancer + {heme_inserted} hematologic drugs")

            # 更新日誌
            db.cursor.execute(
                """INSERT INTO update_logs
                   (source_file, source_date, parsed_date, total_drugs,
                    drugs_oncology_breast, drugs_oncology_heme, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    os.path.basename(docx_path),
                    datetime.now().date(),
                    datetime.now(),
                    breast_inserted + heme_inserted,
                    breast_inserted,
                    heme_inserted,
                    'success'
                )
            )
            db.conn.commit()
            db.close()

            print("[OK] Database updated successfully")
            return True

        except Exception as e:
            print(f"[ERROR] Update failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def full_update_cycle(self) -> bool:
        """
        完整的更新週期
        1. 檢查遠程更新
        2. 如有更新，下載
        3. 解析並更新資料庫

        Returns:
            True if successful
        """

        print("=" * 70)
        print("NHI Drug Coverage Auto-Update")
        print("=" * 70)

        # Step 1: Check for updates
        print("\n[STEP 1] Checking for updates...")
        check_result = self.check_remote_updates()

        if check_result['has_update']:
            print("\n[STEP 2] Downloading latest version...")
            if self.download_latest():
                print("\n[STEP 3] Parsing and updating database...")
                return self.parse_and_update_db()
            else:
                return False
        else:
            print("\n[INFO] Database is up to date")
            return True


def main():
    """主程序"""

    updater = NHIUpdater()

    # 執行完整更新週期
    success = updater.full_update_cycle()

    print("\n" + "=" * 70)
    if success:
        print("Update completed successfully!")
    else:
        print("Update failed!")
    print("=" * 70)


if __name__ == '__main__':
    main()

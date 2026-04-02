# -*- coding: utf-8 -*-
"""
臺大醫院藥品即時查價更新腳本
功能：
  1. 從臺大醫院藥劑部網站爬取最新藥價（健保價/售價）
  2. 補查缺漏的院内代碼（八碼）
  3. 同步更新 nhi_drug_coverage.db 中的 ntuh_drug_codes 表
  4. 記錄每次查詢時間（版本控制），價格異動寫入 price_history 表

使用方式：
  python update_ntuh_prices.py           # 更新所有過期資料（預設 30 天）
  python update_ntuh_prices.py --force   # 強制重新查詢所有藥物
  python update_ntuh_prices.py --days 7  # 更新超過 7 天未查的資料
"""

import sys, re, time, urllib3, argparse, sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

DB_FILE  = Path('nhi_drug_coverage.db')
BASE_URL = 'https://dept.ntuh.gov.tw/phar/WebAp/QueryDrugInfoPhr.aspx'

# ─── SQLite 初始化 ───────────────────────────────────

INIT_SQL = """
-- 臺大院內代碼與即時藥價
CREATE TABLE IF NOT EXISTS ntuh_drug_codes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_key      TEXT NOT NULL,           -- 對應 drug_formulations.drug_key
    ntuh_code     TEXT NOT NULL UNIQUE,    -- 臺大八碼（唯一）
    generic_name  TEXT,
    chinese_name  TEXT,
    product_name  TEXT,
    nhi_price     TEXT,                    -- 健保價（含「事審」等文字）
    own_price     TEXT,                    -- 臺大售價
    side_effects  TEXT,                    -- 副作用
    contraindications TEXT,               -- 禁忌
    notes         TEXT,                    -- 注意事項
    query_date    TEXT,                    -- 最後查詢日期 (YYYY-MM-DD)
    last_updated  TEXT                     -- 最後更新時間 (YYYY-MM-DD HH:MM:SS)
);

-- 價格異動歷史（版本控制）
CREATE TABLE IF NOT EXISTS price_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ntuh_code      TEXT NOT NULL,
    chinese_name   TEXT,
    nhi_price_old  TEXT,
    nhi_price_new  TEXT,
    own_price_old  TEXT,
    own_price_new  TEXT,
    changed_date   TEXT,                   -- 發現異動的日期
    note           TEXT
);
"""


def init_db(conn):
    conn.executescript(INIT_SQL)
    conn.commit()


# ─── 藥物清單來源 ─────────────────────────────────────

def load_drug_list(conn):
    """從 drug_formulations 取得藥物清單（去重）"""
    rows = conn.execute("""
        SELECT DISTINCT drug_key, brand_name, formulation
        FROM drug_formulations
        ORDER BY drug_key
    """).fetchall()
    return rows


def get_existing_codes(conn):
    """取得已存在的 ntuh_code → row dict"""
    rows = conn.execute("SELECT * FROM ntuh_drug_codes").fetchall()
    cols = [d[0] for d in conn.execute("SELECT * FROM ntuh_drug_codes LIMIT 0").description or
            conn.execute("PRAGMA table_info(ntuh_drug_codes)").fetchall()]
    # 直接用 row_factory
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM ntuh_drug_codes").fetchall()
    conn.row_factory = None
    return {row['ntuh_code']: dict(row) for row in rows}


# ─── HTTP 工具 ────────────────────────────────────────

def get_tokens(soup):
    def val(id_):
        el = soup.find('input', {'id': id_})
        return el['value'] if el else ''
    return {
        '__VIEWSTATE':          val('__VIEWSTATE'),
        '__VIEWSTATEGENERATOR': val('__VIEWSTATEGENERATOR'),
        '__EVENTVALIDATION':    val('__EVENTVALIDATION'),
    }


def search_drug(session, search_name):
    """搜尋藥名，回傳所有符合結果（含 POSTBACK event target）"""
    resp0   = session.get(BASE_URL, verify=False, timeout=15)
    tokens0 = get_tokens(BeautifulSoup(resp0.content, 'html.parser'))

    resp1   = session.post(BASE_URL, verify=False, timeout=15, data={
        **tokens0,
        'DrugInfoQueryBox$txbDrugName':        search_name,
        'DrugInfoQueryBox$btnQueryByDrugName': '查詢',
    })
    soup1   = BeautifulSoup(resp1.content, 'html.parser')
    tokens1 = get_tokens(soup1)

    results = []
    for table in soup1.find_all('table'):
        if '八碼' in table.get_text():
            for row in table.find_all('tr')[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all('td')]
                if len(cols) < 3:
                    continue
                code = cols[1].strip()
                if not re.match(r'^[A-Z0-9 ]{6,9}$', code):
                    continue
                link = row.find('a', href=re.compile(r'btnGenericName'))
                if not link:
                    continue
                m = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", link['href'])
                if m:
                    results.append({
                        'code':    code,
                        'generic': cols[0],
                        'chinese': cols[2],
                        'product': cols[3] if len(cols) > 3 else '',
                        'et':      m.group(1),
                        'ea':      m.group(2),
                        'tokens1': tokens1,
                    })
            break

    return results


def get_detail(session, entry):
    """POSTBACK 取得詳細資料（價格 + 副作用等）"""
    resp = session.post(BASE_URL, verify=False, timeout=15, data={
        **entry['tokens1'],
        '__EVENTTARGET':   entry['et'],
        '__EVENTARGUMENT': entry['ea'],
    })
    soup = BeautifulSoup(resp.content, 'html.parser')

    def span(pat):
        el = soup.find('span', {'id': re.compile(pat)})
        return el.get_text(strip=True) if el else ''

    return {
        'nhi_price':         span(r'lblNHIPrice'),
        'own_price':         span(r'lblPatientOwnPrice'),
        'side_effects':      span(r'lblSideEffect'),
        'contraindications': span(r'lblContraindications'),
        'notes':             span(r'lblNote'),
    }


def extract_search_name(brand_name, formulation=''):
    """從品牌名提取搜尋關鍵字"""
    base = re.split(r'\s*[\(\[/]', brand_name)[0].strip()
    return base


# ─── 主程序 ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='臺大醫院藥品查價更新')
    parser.add_argument('--force', action='store_true', help='強制重新查詢所有藥物')
    parser.add_argument('--days',  type=int, default=30, help='更新超過N天未查的資料（預設30）')
    args = parser.parse_args()

    now     = datetime.now()
    now_str = now.strftime('%Y-%m-%d')
    ts_str  = now.strftime('%Y-%m-%d %H:%M:%S')

    print('=' * 70)
    print(f'臺大醫院藥品查價更新  ({ts_str})')
    print(f'更新條件：{"強制全部重查" if args.force else f"超過 {args.days} 天未查"}')
    print('=' * 70)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # 取得藥物清單
    drug_list = load_drug_list(conn)
    print(f'資料庫藥物品項：{len(drug_list)} 筆（去重後）\n')

    # 取得現有八碼資料
    existing = {row['ntuh_code']: dict(row)
                for row in conn.execute('SELECT * FROM ntuh_drug_codes').fetchall()}

    # 判斷哪些 drug_key 需要更新
    def needs_update(drug_key):
        if args.force:
            return True
        rows = [r for r in existing.values() if r['drug_key'] == drug_key]
        if not rows:
            return True
        for r in rows:
            if not r.get('query_date'):
                return True
            try:
                days = (now - datetime.strptime(r['query_date'], '%Y-%m-%d')).days
                if days >= args.days:
                    return True
            except:
                return True
        return False

    # 按 drug_key 分組，避免重複搜尋
    drug_keys_done = set()
    session = requests.Session()
    new_count = upd_count = skip_count = change_count = 0

    for drug_key, brand_name, formulation in drug_list:
        if drug_key in drug_keys_done:
            continue
        drug_keys_done.add(drug_key)

        if not needs_update(drug_key):
            n = len([r for r in existing.values() if r['drug_key'] == drug_key])
            skip_count += n
            print(f'⏭  跳過（資料新）: {brand_name}')
            continue

        search_name = extract_search_name(brand_name, formulation)
        print(f'🔍 搜尋: {brand_name}  →  [{search_name}]')

        found = search_drug(session, search_name)

        if not found:
            print(f'   ✗ 未找到')
            time.sleep(0.5)
            continue

        for entry in found:
            code   = entry['code']
            detail = get_detail(session, entry)
            time.sleep(0.3)

            old = existing.get(code)
            old_nhi = old['nhi_price'] if old else None
            old_own = old['own_price'] if old else None
            new_nhi = detail['nhi_price']
            new_own = detail['own_price']

            changed = old_nhi is not None and (old_nhi != new_nhi or old_own != new_own)

            if changed:
                conn.execute("""
                    INSERT INTO price_history
                    (ntuh_code, chinese_name, nhi_price_old, nhi_price_new,
                     own_price_old, own_price_new, changed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (code, entry['chinese'], old_nhi, new_nhi, old_own, new_own, now_str))
                change_count += 1
                print(f'   ⚡ {code} | 健保: {old_nhi} → {new_nhi} | 售價: {old_own} → {new_own}')
            else:
                status = '新增' if old is None else '未變動'
                print(f'   ✓ {code} | {entry["chinese"][:20]} | 健保:{new_nhi} | 售價:{new_own}  ({status})')

            # upsert
            conn.execute("""
                INSERT INTO ntuh_drug_codes
                    (drug_key, ntuh_code, generic_name, chinese_name, product_name,
                     nhi_price, own_price, side_effects, contraindications, notes,
                     query_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ntuh_code) DO UPDATE SET
                    nhi_price=excluded.nhi_price,
                    own_price=excluded.own_price,
                    side_effects=excluded.side_effects,
                    contraindications=excluded.contraindications,
                    notes=excluded.notes,
                    query_date=excluded.query_date,
                    last_updated=excluded.last_updated
            """, (
                drug_key, code, entry['generic'], entry['chinese'], entry['product'],
                new_nhi, new_own,
                detail['side_effects'], detail['contraindications'], detail['notes'],
                now_str, ts_str
            ))

            if old is None:
                new_count += 1
                existing[code] = {}
            else:
                upd_count += 1

        conn.commit()
        time.sleep(0.5)

    conn.close()

    print('\n' + '=' * 70)
    print(f'完成！  {ts_str}')
    print(f'  新增: {new_count} 筆 | 更新: {upd_count} 筆 | 跳過: {skip_count} 筆')
    print(f'  價格異動: {change_count} 筆 → price_history 表')
    print(f'  資料庫: {DB_FILE}')
    print('=' * 70)


if __name__ == '__main__':
    main()

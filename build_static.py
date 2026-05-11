#!/usr/bin/env python3
"""
Refresh embedded static data in index.html from SQLite.
For separated Netlify/API deployments, run api_export.py as well.
Run: python build_static.py
Output: index.html (self-contained, no backend needed)
"""
import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "nhi_drug_coverage.db"
TEMPLATE = HERE / "index.html"


def export_data():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT d.id, d.generic_name, d.trade_names, d.specialty_id, d.indication,
               d.clinical_tags, d.stage, d.nhi_price, d.price_unit, d.dosage_info,
               cr.therapy_line, cr.prior_auth_required as prior_auth, cr.condition as conditions
        FROM drugs d
        LEFT JOIN coverage_rules cr ON cr.drug_id = d.id
        ORDER BY d.generic_name
    """)
    drugs = []
    for r in cur.fetchall():
        tags = r['clinical_tags'] or '{}'
        try:
            tags = json.loads(tags)
        except Exception:
            tags = {}
        drugs.append({
            'id': r['id'],
            'generic_name': r['generic_name'],
            'trade_names': r['trade_names'],
            'specialty_id': r['specialty_id'],
            'indication': r['indication'],
            'clinical_tags': tags,
            'stage': r['stage'] or '',
            'therapy_line': r['therapy_line'],
            'prior_auth': bool(r['prior_auth']),
            'conditions': r['conditions'],
            'nhi_price': r['nhi_price'],
            'price_unit': r['price_unit'] or '',
            'dosage_info': r['dosage_info'] or '',
        })

    cur.execute("SELECT * FROM drug_formulations ORDER BY drug_key, dose_mg DESC")
    formulations = [dict(r) for r in cur.fetchall()]

    conn.close()
    return drugs, formulations


FIXED_MATCHES_FILTERS = """\
function matchesFilters(drug, filters){
    const tags=drug.clinical_tags||{};
    const stage=drug.stage||'';
    // HER2 and ER/PR are independent axes — use OR among receptor filters
    const receptorKeys=['her2','er_pr'];
    const receptorFilters=Object.fromEntries(Object.entries(filters).filter(([k])=>receptorKeys.includes(k)));
    const otherFilters=Object.fromEntries(Object.entries(filters).filter(([k])=>!receptorKeys.includes(k)));
    // AND logic for non-receptor filters
    for(const[f,v] of Object.entries(otherFilters)){
        if(f==='stage'){
            if(!stage.includes(v))return false;
        } else if(f==='disease'){
            if(!tags.disease||!tags.disease.includes(v))return false;
        } else if(f==='phase'){
            if(!tags.phase||!tags.phase.includes(v))return false;
        } else if(f==='menopause'){
            if(!tags.menopause)return false;
            if(tags.menopause!==v && tags.menopause!=='both')return false;
        } else {
            if(!tags[f])return false;
        }
    }
    // OR logic for receptor filters: patient may be HER2+/ER+ simultaneously
    if(Object.keys(receptorFilters).length>0){
        let match=false;
        if(receptorFilters.her2!==undefined){
            const v=receptorFilters.her2;
            if(tags.her2&&(tags.her2===v||tags.her2==='both'))match=true;
        }
        if(receptorFilters.er_pr!==undefined){
            const v=receptorFilters.er_pr;
            if(tags.er_pr&&(tags.er_pr===v||tags.er_pr==='both'))match=true;
        }
        if(!match)return false;
    }
    return true;
}\
"""


def build():
    drugs, formulations = export_data()

    stats = {
        'total': len(drugs),
        'breast': sum(1 for d in drugs if d['specialty_id'] == 'oncology_breast'),
        'heme': sum(1 for d in drugs if d['specialty_id'] == 'oncology_heme'),
    }

    html = TEMPLATE.read_text(encoding='utf-8')

    # 1. Replace data block: from <script>\nconst _STATIC_DRUGS= ... up to let breastDrugs=
    data_start = html.find('<script>\nconst _STATIC_DRUGS=')
    data_end = html.find('let breastDrugs=')
    if data_start == -1 or data_end == -1:
        raise ValueError("Cannot find data injection anchors in template")

    new_data_block = (
        '<script>\n'
        f'const _STATIC_DRUGS={json.dumps(drugs, ensure_ascii=False)};\n'
        f'const _STATIC_FORMULATIONS={json.dumps(formulations, ensure_ascii=False)};\n'
        f'const _STATIC_STATS={json.dumps(stats, ensure_ascii=False)};\n'
    )
    html = html[:data_start] + new_data_block + html[data_end:]

    # 2. Apply OR logic fix for matchesFilters
    old_fn_match = re.search(r'function matchesFilters\(drug, filters\)\{.*?\n\}', html, re.DOTALL)
    if old_fn_match:
        html = html[:old_fn_match.start()] + FIXED_MATCHES_FILTERS + html[old_fn_match.end():]
    else:
        raise ValueError("Cannot find matchesFilters in template")

    # 3. Disable write operations
    html = html.replace(
        "await fetch('/api/drug/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});",
        "alert('本系統為唯讀模式，無法修改資料。'); return;"
    )
    html = html.replace(
        "await fetch('/api/drug/'+id,{method:'DELETE'});",
        "alert('本系統為唯讀模式，無法修改資料。'); return;"
    )
    html = html.replace(
        "await fetch('/api/drugs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});",
        "alert('本系統為唯讀模式，無法修改資料。'); return;"
    )

    # 4. Disable version check
    html = html.replace(
        "const r=await fetch('/api/version');const d=await r.json();",
        "return; // static mode"
    )

    out = HERE / "index.html"
    out.write_text(html, encoding='utf-8')
    print(f"[OK] index.html generated ({len(html):,} chars)")
    print(f"  Drugs: {len(drugs)} | Formulations: {len(formulations)}")
    print(f"  Stats: {stats}")
    print("  Source: index.html")
    print("  Ready to deploy to Netlify!")


if __name__ == '__main__':
    build()

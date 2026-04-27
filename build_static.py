#!/usr/bin/env python3
"""
Build static index.html from web_app.py + SQLite DB for Netlify deployment.
Run: python build_static.py
Output: index.html (self-contained, no backend needed)
"""
import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "nhi_drug_coverage.db"


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


STATIC_FETCH = """\
// ── Static Fetch (replaces server API for Netlify) ──
async function cachedFetch(url, opts){
    if(url.startsWith('/api/stats')){
        return {ok:true,json:()=>Promise.resolve(_STATIC_STATS)};
    }
    if(url.startsWith('/api/drugs')){
        const qs=url.includes('?')?url.split('?')[1]:'';
        const p=new URLSearchParams(qs);
        let drugs=[..._STATIC_DRUGS];
        const cat=p.get('category')||p.get('specialty');
        const q=p.get('q');
        if(cat) drugs=drugs.filter(d=>d.specialty_id===cat);
        if(q){const ql=q.toLowerCase();drugs=drugs.filter(d=>(d.generic_name||'').toLowerCase().includes(ql)||(d.trade_names||'').toLowerCase().includes(ql));}
        return {ok:true,json:()=>Promise.resolve(drugs)};
    }
    if(url.startsWith('/api/drug/')){
        const id=parseInt(url.split('/').pop());
        const drug=_STATIC_DRUGS.find(d=>d.id===id)||null;
        if(!drug) return {ok:false,status:404,json:()=>Promise.resolve({error:'Not found'})};
        return {ok:true,json:()=>Promise.resolve(drug)};
    }
    if(url.startsWith('/api/formulations')){
        const qs=url.includes('?')?url.split('?')[1]:'';
        const dk=new URLSearchParams(qs).get('drug');
        let f=[..._STATIC_FORMULATIONS];
        if(dk) f=f.filter(x=>x.drug_key===dk);
        return {ok:true,json:()=>Promise.resolve(f)};
    }
    throw new Error('Unknown API: '+url);
}\
"""


def build():
    drugs, formulations = export_data()

    stats = {
        'total': len(drugs),
        'breast': sum(1 for d in drugs if d['specialty_id'] == 'oncology_breast'),
        'heme': sum(1 for d in drugs if d['specialty_id'] == 'oncology_heme'),
    }

    # Extract HTML from web_app.py
    source = (HERE / "web_app.py").read_text(encoding='utf-8')
    match = re.search(r'HTML_PAGE\s*=\s*r"""(.*?)"""', source, re.DOTALL)
    if not match:
        raise ValueError("Cannot find HTML_PAGE in web_app.py")
    html = match.group(1)

    # 1. Replace cachedFetch with static version
    old_cache_marker = "// ── Offline Cache ──"
    cache_start = html.find(old_cache_marker)
    if cache_start == -1:
        raise ValueError("Cannot find '// ── Offline Cache ──' in HTML")

    # Find the opening brace of the async function and walk to its closing brace
    brace_pos = html.find('{', html.find('async function cachedFetch', cache_start))
    depth, i = 0, brace_pos
    while i < len(html):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0:
                cache_end = i + 1
                break
        i += 1

    html = html[:cache_start] + STATIC_FETCH + html[cache_end:]

    # 2. Inject static data right after opening <script> tag
    script_anchor = '<script>\nlet breastDrugs=[], hemeDrugs=[];'
    data_block = (
        '<script>\n'
        f'const _STATIC_DRUGS={json.dumps(drugs, ensure_ascii=False)};\n'
        f'const _STATIC_FORMULATIONS={json.dumps(formulations, ensure_ascii=False)};\n'
        f'const _STATIC_STATS={json.dumps(stats, ensure_ascii=False)};\n'
        'let breastDrugs=[], hemeDrugs=[];'
    )
    if script_anchor not in html:
        raise ValueError("Cannot find script anchor in HTML")
    html = html.replace(script_anchor, data_block, 1)

    # 3. Disable write operations (read-only public deployment)
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

    # 4. Disable version check (no server)
    html = html.replace(
        "const r=await fetch('/api/version');const d=await r.json();",
        "return; // static mode"
    )

    out = HERE / "index.html"
    out.write_text(html, encoding='utf-8')
    print(f"[OK] index.html generated ({len(html):,} chars)")
    print(f"  Drugs: {len(drugs)} | Formulations: {len(formulations)}")
    print(f"  Stats: {stats}")
    print("  Ready to deploy to Netlify!")


if __name__ == '__main__':
    build()

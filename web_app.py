#!/usr/bin/env python3
"""
健保藥物給付規定查詢系統 Web Application
使用 Python 內建 http.server，無需外部依賴
"""

import sys
import io
import json
import sqlite3
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = Path(__file__).parent / "nhi_drug_coverage.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ─── HTML ─────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>健保藥物給付規定查詢系統</title>
<style>
:root {
    --primary:#2563eb; --primary-dark:#1d4ed8;
    --bg:#f8fafc; --card:#fff; --text:#1e293b; --muted:#64748b; --border:#e2e8f0;
    --pink:#be185d; --blue:#1e40af; --green:#059669; --red:#dc2626; --amber:#d97706;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans TC",sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.header{background:linear-gradient(135deg,var(--primary),#7c3aed);color:#fff;padding:1.2rem 2rem;box-shadow:0 4px 6px -1px rgb(0 0 0/.1)}
.header h1{font-size:1.4rem;font-weight:700}
.header p{font-size:.8rem;opacity:.8;margin-top:.15rem}
.container{max-width:1280px;margin:0 auto;padding:1.2rem}

/* ── Landing Page ── */
.landing{display:flex;gap:1.5rem;justify-content:center;flex-wrap:wrap;padding:2rem 0}
.dept-card{background:var(--card);border-radius:16px;padding:2rem;width:340px;box-shadow:0 4px 12px rgb(0 0 0/.08);cursor:pointer;transition:transform .2s,box-shadow .2s;border-top:5px solid var(--primary);text-align:center}
.dept-card:hover{transform:translateY(-4px);box-shadow:0 8px 24px rgb(0 0 0/.12)}
.dept-card.breast{border-top-color:var(--pink)}
.dept-card.heme{border-top-color:var(--blue)}
.dept-card h2{font-size:1.5rem;margin:.5rem 0}
.dept-card .count{font-size:2.5rem;font-weight:800;margin:.5rem 0}
.dept-card.breast .count{color:var(--pink)}
.dept-card.heme .count{color:var(--blue)}
.dept-card .desc{color:var(--muted);font-size:.85rem}

/* ── Department Page ── */
.dept-page{display:none}
.dept-page.active{display:block}
.back-btn{background:none;border:none;color:var(--primary);font-size:.9rem;cursor:pointer;padding:.5rem 0;font-weight:600}
.back-btn:hover{text-decoration:underline}

/* ── Filter Panel ── */
.filter-panel{background:var(--card);border-radius:12px;padding:1.25rem;margin-bottom:1.2rem;box-shadow:0 1px 3px rgb(0 0 0/.1)}
.filter-panel h3{font-size:.85rem;font-weight:700;color:var(--muted);margin-bottom:.75rem;text-transform:uppercase;letter-spacing:.05em}
.filter-group{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.75rem}
.filter-group label{font-size:.8rem;font-weight:600;color:var(--muted);width:100%;margin-bottom:.15rem}
.filter-chip{padding:.35rem .8rem;border:2px solid var(--border);border-radius:8px;background:#fff;cursor:pointer;font-size:.8rem;font-weight:500;transition:all .15s;user-select:none}
.filter-chip.active{border-color:var(--primary);background:#eff6ff;color:var(--primary)}
.filter-chip:hover{border-color:var(--primary)}
.filter-chip.positive{border-color:#86efac;background:#f0fdf4;color:#166534}
.filter-chip.negative{border-color:#fca5a5;background:#fef2f2;color:#991b1b}

.search-row{display:flex;gap:.75rem;flex-wrap:wrap;align-items:end;margin-bottom:.75rem}
.search-row input{flex:1;min-width:200px;padding:.5rem .8rem;border:2px solid var(--border);border-radius:8px;font-size:.9rem;outline:none}
.search-row input:focus{border-color:var(--primary)}
.btn{padding:.5rem 1.2rem;border:none;border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;transition:all .15s}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover{background:var(--primary-dark)}
.btn-sm{padding:.3rem .8rem;font-size:.75rem}
.btn-outline{background:transparent;border:2px solid var(--border);color:var(--text)}
.btn-outline:hover{border-color:var(--primary);color:var(--primary)}
.btn-success{background:var(--green);color:#fff}
.btn-danger{background:var(--red);color:#fff}

/* ── Drug Table ── */
.table-wrap{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgb(0 0 0/.1);overflow:hidden}
.result-info{font-size:.8rem;color:var(--muted);padding:.6rem 1rem;border-bottom:1px solid var(--border)}
table{width:100%;border-collapse:collapse}
th{background:#f1f5f9;padding:.7rem .8rem;text-align:left;font-size:.75rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;border-bottom:2px solid var(--border)}
td{padding:.7rem .8rem;border-bottom:1px solid var(--border);font-size:.85rem}
.price-tag{font-weight:600;color:#9333ea;font-size:.8rem;white-space:nowrap}
.price-unit{font-size:.7rem;color:var(--muted);display:block}

/* ── Cost Calculator ── */
.calc-box{background:#faf5ff;border:2px solid #e9d5ff;border-radius:12px;padding:1.2rem;margin-top:.8rem}
.calc-box h3{color:#7c3aed;margin-bottom:.8rem}
.calc-row{display:flex;gap:.8rem;flex-wrap:wrap;margin-bottom:.6rem;align-items:end}
.calc-row .field{flex:1;min-width:120px}
.calc-row label{display:block;font-size:.75rem;font-weight:600;color:var(--muted);margin-bottom:.2rem}
.calc-row input{width:100%;padding:.4rem .6rem;border:2px solid var(--border);border-radius:6px;font-size:.85rem}
.calc-row input:focus{border-color:#7c3aed;outline:none}
.calc-result{background:#fff;border-radius:8px;padding:1rem;margin-top:.8rem;border:1px solid #e9d5ff}
.calc-result .cost-line{display:flex;justify-content:space-between;padding:.3rem 0;font-size:.85rem}
.calc-result .cost-line.total{font-weight:700;font-size:1rem;color:#7c3aed;border-top:2px solid #e9d5ff;margin-top:.4rem;padding-top:.6rem}
.calc-result .cost-note{font-size:.75rem;color:var(--muted);margin-top:.5rem;font-style:italic}
/* ── Combo Calculator ── */
.combo-box{background:#fdf4ff;border:2px solid #d8b4fe;border-radius:12px;padding:1.2rem;margin-top:.8rem}
.combo-box h3{color:#6d28d9;margin-bottom:.5rem;font-size:1rem}
.combo-desc{font-size:.8rem;color:var(--muted);margin-bottom:.8rem}
.scenario-btns{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.8rem}
.scenario-btn{padding:.3rem .8rem;border-radius:20px;border:2px solid #c4b5fd;background:#fff;color:#5b21b6;font-size:.78rem;font-weight:600;cursor:pointer;transition:all .15s}
.scenario-btn:hover,.scenario-btn.active{background:#7c3aed;color:#fff;border-color:#7c3aed}
.combo-drugs{display:flex;gap:.8rem;flex-wrap:wrap;margin-bottom:.8rem}
.combo-drug-card{flex:1;min-width:180px;background:#fff;border-radius:8px;padding:.8rem;border:2px solid #e9d5ff}
.combo-drug-card.nhi-covered{border-color:#6ee7b7;background:#f0fdf4}
.combo-drug-card.self-pay{border-color:#fca5a5;background:#fff7f7}
.combo-drug-name{font-weight:700;font-size:.85rem;margin-bottom:.3rem}
.coverage-toggle{display:flex;gap:0;border-radius:6px;overflow:hidden;border:1.5px solid #d8b4fe;margin-bottom:.6rem}
.coverage-toggle button{flex:1;padding:.25rem .5rem;border:none;background:#f5f3ff;color:#5b21b6;font-size:.75rem;font-weight:600;cursor:pointer;transition:background .15s}
.coverage-toggle button.active-nhi{background:#059669;color:#fff}
.coverage-toggle button.active-self{background:#dc2626;color:#fff}
.combo-drug-detail{font-size:.75rem;color:var(--muted)}
.combo-inputs{display:flex;gap:.8rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:.8rem}
.combo-inputs .field{flex:1;min-width:120px}
.combo-inputs label{display:block;font-size:.75rem;font-weight:600;color:var(--muted);margin-bottom:.2rem}
.combo-inputs input,.combo-inputs select{width:100%;padding:.4rem .6rem;border:2px solid var(--border);border-radius:6px;font-size:.85rem}
.combo-inputs input:focus,.combo-inputs select:focus{border-color:#7c3aed;outline:none}
.combo-result{background:#fff;border-radius:8px;padding:1rem;margin-top:.6rem;border:1px solid #e9d5ff}
.combo-result .cost-line{display:flex;justify-content:space-between;padding:.25rem 0;font-size:.85rem}
.combo-result .nhi-line{color:#059669;font-weight:600}
.combo-result .self-line{color:#dc2626;font-weight:600}
.combo-result .total-line{font-weight:700;font-size:1rem;border-top:2px solid #e9d5ff;margin-top:.4rem;padding-top:.5rem}
.combo-result .total-nhi{color:#059669}
.combo-result .total-self{color:#dc2626}
.combo-result .cost-note{font-size:.75rem;color:var(--muted);margin-top:.5rem;font-style:italic}
tr.clickable{cursor:pointer}
tr.clickable:hover{background:#f8fafc}
.drug-name{font-weight:600;color:var(--primary)}
.brand{font-size:.75rem;color:var(--muted)}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:9999px;font-size:.7rem;font-weight:600}
.badge-breast{background:#fce7f3;color:#be185d}
.badge-heme{background:#dbeafe;color:#1e40af}
.badge-auth{background:#fee2e2;color:#991b1b}
.badge-line{background:#d1fae5;color:#065f46}
.badge-tag{background:#f1f5f9;color:#475569;margin:.1rem}
.icon-ok{color:var(--green);font-weight:bold;font-size:1rem}
.icon-pay{color:var(--amber);font-weight:bold;font-size:.85rem}
.empty{text-align:center;padding:2.5rem;color:var(--muted)}

/* ── Modal ── */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;justify-content:center;align-items:center;padding:1rem}
.modal-bg.show{display:flex}
.modal{background:#fff;border-radius:16px;max-width:780px;width:100%;max-height:88vh;overflow-y:auto;padding:1.8rem;box-shadow:0 25px 50px rgb(0 0 0/.25)}
.modal h2{font-size:1.3rem;margin-bottom:.2rem}
.modal .sub{color:var(--muted);font-size:.85rem;margin-bottom:1.2rem}
.detail-sec{margin-bottom:1.1rem}
.detail-sec h3{font-size:.8rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:.4rem;padding-bottom:.3rem;border-bottom:2px solid var(--border)}
.detail-sec p{font-size:.85rem;line-height:1.7;margin-bottom:.3rem}
.close-x{float:right;background:none;border:none;font-size:1.4rem;cursor:pointer;color:var(--muted);padding:.2rem}
.close-x:hover{color:var(--text)}

/* ── Edit Modal ── */
.edit-form textarea{width:100%;min-height:100px;padding:.6rem;border:2px solid var(--border);border-radius:8px;font-size:.85rem;font-family:inherit;resize:vertical}
.edit-form textarea:focus{border-color:var(--primary);outline:none}
.edit-form .form-row{margin-bottom:.8rem}
.edit-form label{display:block;font-size:.8rem;font-weight:600;color:var(--muted);margin-bottom:.3rem}
.edit-form input,.edit-form select{width:100%;padding:.5rem;border:2px solid var(--border);border-radius:8px;font-size:.85rem}
.edit-form input:focus,.edit-form select:focus{border-color:var(--primary);outline:none}
.btn-row{display:flex;gap:.5rem;justify-content:flex-end;margin-top:1rem}

/* ── Version Banner ── */
.version-banner{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:.6rem 1rem;margin-bottom:1rem;font-size:.8rem;color:#92400e;display:none}
.version-banner.show{display:flex;align-items:center;gap:.5rem}

@media(max-width:768px){
    .container{padding:.6rem}
    .landing{flex-direction:column;align-items:center}
    .dept-card{width:100%}
    .filter-group{gap:.3rem}
    th,td{padding:.5rem .4rem;font-size:.78rem}
}
</style>
</head>
<body>
<div class="header">
    <h1>健保藥物給付規定查詢系統</h1>
    <p>衛生福利部中央健康保險署 — 腫瘤科藥物給付資料庫</p>
</div>
<div class="container">
    <!-- Version Update Banner -->
    <div class="version-banner" id="versionBanner">
        <span>&#9888;</span>
        <span id="versionMsg"></span>
        <button class="btn btn-sm btn-primary" onclick="location.reload()">重新載入</button>
    </div>

    <!-- ===== Landing Page ===== -->
    <div id="landingPage">
        <div class="landing" id="landingCards"></div>
        <div style="text-align:center;margin-top:1rem">
            <button class="btn btn-outline" onclick="openAddDrug()">新增藥物</button>
            <button class="btn btn-outline" onclick="openEditModal(null)">管理工具</button>
        </div>
    </div>

    <!-- ===== Breast Cancer Page ===== -->
    <div id="breastPage" class="dept-page">
        <button class="back-btn" onclick="showLanding()">&#8592; 返回首頁</button>
        <h2 style="margin:.5rem 0 1rem;color:var(--pink)">乳癌藥物給付查詢</h2>

        <div class="filter-panel">
            <h3>臨床條件篩選</h3>
            <div class="search-row">
                <input type="text" id="breastSearch" placeholder="搜尋藥物名稱 ..." autocomplete="off">
                <button class="btn btn-primary" onclick="filterBreast()">搜尋</button>
                <button class="btn btn-outline" onclick="resetBreastFilters()">重置</button>
            </div>
            <div class="filter-group">
                <label>疾病分期</label>
                <div class="filter-chip" data-f="stage" data-v="early" onclick="toggleChip(this)">早期乳癌（第1-2期）</div>
                <div class="filter-chip" data-f="stage" data-v="metastatic" onclick="toggleChip(this)">轉移性乳癌（第4期）</div>
            </div>
            <div class="filter-group">
                <label>HER2 狀態</label>
                <div class="filter-chip" data-f="her2" data-v="positive" onclick="toggleChip(this)">HER2 陽性（IHC3+/FISH+）</div>
                <div class="filter-chip" data-f="her2" data-v="negative" onclick="toggleChip(this)">HER2 陰性</div>
            </div>
            <div class="filter-group">
                <label>荷爾蒙受體</label>
                <div class="filter-chip" data-f="er_pr" data-v="positive" onclick="toggleChip(this)">ER/PR 陽性</div>
                <div class="filter-chip" data-f="er_pr" data-v="negative" onclick="toggleChip(this)">ER/PR 陰性</div>
            </div>
            <div class="filter-group">
                <label>其他條件</label>
                <div class="filter-chip" data-f="ln" data-v="true" onclick="toggleChip(this)">淋巴結轉移</div>
                <div class="filter-chip" data-f="tnbc" data-v="true" onclick="toggleChip(this)">三陰性乳癌</div>
                <div class="filter-chip" data-f="brca" data-v="true" onclick="toggleChip(this)">BRCA 突變</div>
                <div class="filter-chip" data-f="menopause" data-v="post" onclick="toggleChip(this)">停經後</div>
                <div class="filter-chip" data-f="menopause" data-v="pre" onclick="toggleChip(this)">停經前</div>
            </div>
        </div>

        <div class="table-wrap">
            <div class="result-info" id="breastInfo"></div>
            <table>
                <thead><tr>
                    <th style="width:30px"></th>
                    <th>藥物名稱</th>
                    <th>分期</th>
                    <th>療程線</th>
                    <th>事前審查</th>
                    <th>藥價</th>
                    <th>臨床標記</th>
                </tr></thead>
                <tbody id="breastBody"></tbody>
            </table>
        </div>
    </div>

    <!-- ===== Hematologic Page ===== -->
    <div id="hemePage" class="dept-page">
        <button class="back-btn" onclick="showLanding()">&#8592; 返回首頁</button>
        <h2 style="margin:.5rem 0 1rem;color:var(--blue)">血液腫瘤藥物給付查詢</h2>

        <div class="filter-panel">
            <h3>臨床條件篩選</h3>
            <div class="search-row">
                <input type="text" id="hemeSearch" placeholder="搜尋藥物名稱 ..." autocomplete="off">
                <button class="btn btn-primary" onclick="filterHeme()">搜尋</button>
                <button class="btn btn-outline" onclick="resetHemeFilters()">重置</button>
            </div>
            <div class="filter-group">
                <label>疾病類型</label>
                <div class="filter-chip" data-f="disease" data-v="CML" onclick="toggleChip(this)">CML 慢性骨髓性白血病</div>
                <div class="filter-chip" data-f="disease" data-v="AML" onclick="toggleChip(this)">AML 急性骨髓性白血病</div>
                <div class="filter-chip" data-f="disease" data-v="CLL" onclick="toggleChip(this)">CLL 慢性淋巴性白血病</div>
                <div class="filter-chip" data-f="disease" data-v="ALL" onclick="toggleChip(this)">ALL 急性淋巴性白血病</div>
                <div class="filter-chip" data-f="disease" data-v="lymphoma" onclick="toggleChip(this)">淋巴瘤</div>
                <div class="filter-chip" data-f="disease" data-v="myeloma" onclick="toggleChip(this)">多發性骨髓瘤</div>
                <div class="filter-chip" data-f="disease" data-v="MDS" onclick="toggleChip(this)">MDS 骨髓化生不良</div>
            </div>
            <div class="filter-group">
                <label>治療階段</label>
                <div class="filter-chip" data-f="phase" data-v="initial" onclick="toggleChip(this)">初診斷/第一線</div>
                <div class="filter-chip" data-f="phase" data-v="relapsed" onclick="toggleChip(this)">復發/難治</div>
            </div>
        </div>

        <div class="table-wrap">
            <div class="result-info" id="hemeInfo"></div>
            <table>
                <thead><tr>
                    <th style="width:30px"></th>
                    <th>藥物名稱</th>
                    <th>適用疾病</th>
                    <th>療程線</th>
                    <th>事前審查</th>
                    <th>藥價</th>
                    <th>臨床標記</th>
                </tr></thead>
                <tbody id="hemeBody"></tbody>
            </table>
        </div>
    </div>
</div>

<!-- Detail Modal -->
<div class="modal-bg" id="detailModal" onclick="if(event.target===this)closeDetail()">
    <div class="modal">
        <button class="close-x" onclick="closeDetail()">&times;</button>
        <div id="detailBody"></div>
    </div>
</div>

<!-- Edit Modal -->
<div class="modal-bg" id="editModal" onclick="if(event.target===this)closeEdit()">
    <div class="modal">
        <button class="close-x" onclick="closeEdit()">&times;</button>
        <div id="editBody"></div>
    </div>
</div>

<script>
let breastDrugs=[], hemeDrugs=[];
let activeFilters={};

// ── Init ──
document.addEventListener('DOMContentLoaded',()=>{
    loadLanding();
    ['breastSearch','hemeSearch'].forEach(id=>{
        const el=document.getElementById(id);
        if(el){
            let t; el.addEventListener('input',()=>{clearTimeout(t);t=setTimeout(()=>{id==='breastSearch'?filterBreast():filterHeme()},300)});
            el.addEventListener('keyup',e=>{if(e.key==='Enter'){id==='breastSearch'?filterBreast():filterHeme()}});
        }
    });
    checkVersion();
});

// ── Landing ──
async function loadLanding(){
    const r=await fetch('/api/stats'); const d=await r.json();
    document.getElementById('landingCards').innerHTML=`
        <div class="dept-card breast" onclick="showBreast()">
            <div style="font-size:2.5rem">&#127993;</div>
            <h2>乳癌</h2>
            <div class="count">${d.breast}</div>
            <div class="desc">藥物 | HER2/ER/PR 篩選 | 分期查詢</div>
        </div>
        <div class="dept-card heme" onclick="showHeme()">
            <div style="font-size:2.5rem">&#129656;</div>
            <h2>血液腫瘤</h2>
            <div class="count">${d.heme}</div>
            <div class="desc">藥物 | CML/AML/CLL/淋巴瘤/骨髓瘤</div>
        </div>`;
}

function showLanding(){
    document.getElementById('landingPage').style.display='';
    document.getElementById('breastPage').classList.remove('active');
    document.getElementById('hemePage').classList.remove('active');
}
async function showBreast(){
    document.getElementById('landingPage').style.display='none';
    document.getElementById('breastPage').classList.add('active');
    document.getElementById('hemePage').classList.remove('active');
    activeFilters={};
    const r=await fetch('/api/drugs?category=oncology_breast'); breastDrugs=await r.json();
    renderBreast(breastDrugs);
}
async function showHeme(){
    document.getElementById('landingPage').style.display='none';
    document.getElementById('hemePage').classList.add('active');
    document.getElementById('breastPage').classList.remove('active');
    activeFilters={};
    const r=await fetch('/api/drugs?category=oncology_heme'); hemeDrugs=await r.json();
    renderHeme(hemeDrugs);
}

// ── Filters ──
function toggleChip(el){
    el.classList.toggle('active');
    const f=el.dataset.f, v=el.dataset.v;
    if(el.classList.contains('active')){activeFilters[f]=v}
    else{delete activeFilters[f]}
    // Determine which page
    if(document.getElementById('breastPage').classList.contains('active'))filterBreast();
    else filterHeme();
}

function matchesFilters(drug, filters){
    const tags=drug.clinical_tags||{};
    const stage=drug.stage||'';
    for(const[f,v] of Object.entries(filters)){
        if(f==='stage'){
            if(!stage.includes(v))return false;
        } else if(f==='disease'){
            if(!tags.disease||!tags.disease.includes(v))return false;
        } else if(f==='phase'){
            if(!tags.phase||!tags.phase.includes(v))return false;
        } else if(f==='her2'){
            if(!tags.her2)return false;
            if(tags.her2!==v && tags.her2!=='both')return false;
        } else if(f==='er_pr'){
            if(!tags.er_pr)return false;
            if(tags.er_pr!==v && tags.er_pr!=='both')return false;
        } else if(f==='menopause'){
            if(!tags.menopause)return false;
            if(tags.menopause!==v && tags.menopause!=='both')return false;
        } else {
            if(!tags[f])return false;
        }
    }
    return true;
}

function hasAnyFilter(){return Object.keys(activeFilters).length>0}

function filterBreast(){
    const q=(document.getElementById('breastSearch').value||'').toLowerCase();
    let list=breastDrugs;
    if(q)list=list.filter(d=>(d.generic_name||'').toLowerCase().includes(q)||(d.trade_names||'').toLowerCase().includes(q));
    renderBreast(list);
}
function resetBreastFilters(){
    document.getElementById('breastSearch').value='';
    activeFilters={};
    document.querySelectorAll('#breastPage .filter-chip').forEach(c=>c.classList.remove('active'));
    renderBreast(breastDrugs);
}
function filterHeme(){
    const q=(document.getElementById('hemeSearch').value||'').toLowerCase();
    let list=hemeDrugs;
    if(q)list=list.filter(d=>(d.generic_name||'').toLowerCase().includes(q)||(d.trade_names||'').toLowerCase().includes(q));
    renderHeme(list);
}
function resetHemeFilters(){
    document.getElementById('hemeSearch').value='';
    activeFilters={};
    document.querySelectorAll('#hemePage .filter-chip').forEach(c=>c.classList.remove('active'));
    renderHeme(hemeDrugs);
}

// ── Render ──
function stageLabel(s){
    if(!s)return'-';
    const m={'early':'早期','metastatic':'轉移','advanced':'晚期'};
    return s.split(',').map(x=>m[x]||x).join('、');
}
function lineLabel(n){return n?'第'+n+'線':'-'}

function renderBreast(list){
    const hasF=hasAnyFilter();
    let matched=0,unmatched=0;
    const rows=list.map((d,i)=>{
        const tags=typeof d.clinical_tags==='string'?JSON.parse(d.clinical_tags||'{}'):d.clinical_tags||{};
        d._tags=tags;
        const ok=hasF?matchesFilters(d,activeFilters):null;
        if(ok===true)matched++; if(ok===false)unmatched++;
        const icon=ok===true?'<span class="icon-ok" title="符合健保給付條件">&#10003;</span>'
                   :ok===false?'<span class="icon-pay" title="不符合健保給付，可自費使用">&#36;</span>'
                   :'';
        const brandHtml=d.trade_names?'<br><span class="brand">'+esc(d.trade_names)+'</span>':'';
        const tagBadges=renderTagBadges(tags,'breast');
        const line=lineLabel(d.therapy_line);
        const auth=d.prior_auth?'<span class="badge badge-auth">需審查</span>':'-';
        const priceHtml=d.nhi_price?`<span class="price-tag">$${Number(d.nhi_price).toLocaleString()}</span><span class="price-unit">${esc(d.price_unit||'')}</span>`:'<span style="color:var(--muted)">-</span>';
        return `<tr class="clickable" onclick="showDetail(${d.id})" style="${ok===false?'opacity:.6':''}">
            <td>${icon}</td>
            <td><span class="drug-name">${esc(d.generic_name)}</span>${brandHtml}</td>
            <td>${stageLabel(d.stage)}</td>
            <td>${d.therapy_line?'<span class="badge badge-line">'+line+'</span>':'-'}</td>
            <td>${auth}</td>
            <td>${priceHtml}</td>
            <td>${tagBadges}</td>
        </tr>`;
    });
    // Sort: matched first
    if(hasF){
        const sorted=list.map((d,i)=>({d,i,ok:matchesFilters(d,activeFilters)}));
        sorted.sort((a,b)=>(b.ok?1:0)-(a.ok?1:0));
        const sortedRows=sorted.map(x=>rows[x.i]);
        document.getElementById('breastBody').innerHTML=sortedRows.join('');
        document.getElementById('breastInfo').textContent=`共 ${list.length} 筆｜符合條件 ${matched} 筆｜不符合 ${unmatched} 筆（不符合者仍可自費使用）`;
    } else {
        document.getElementById('breastBody').innerHTML=rows.join('')||'<tr><td colspan="7"><div class="empty">沒有找到藥物</div></td></tr>';
        document.getElementById('breastInfo').textContent=`共 ${list.length} 筆`;
    }
}

function renderHeme(list){
    const hasF=hasAnyFilter();
    let matched=0,unmatched=0;
    const rows=list.map((d,i)=>{
        const tags=typeof d.clinical_tags==='string'?JSON.parse(d.clinical_tags||'{}'):d.clinical_tags||{};
        d._tags=tags;
        const ok=hasF?matchesFilters(d,activeFilters):null;
        if(ok===true)matched++; if(ok===false)unmatched++;
        const icon=ok===true?'<span class="icon-ok" title="符合健保給付條件">&#10003;</span>'
                   :ok===false?'<span class="icon-pay" title="不符合健保給付，可自費使用">&#36;</span>'
                   :'';
        const brandHtml=d.trade_names?'<br><span class="brand">'+esc(d.trade_names)+'</span>':'';
        const tagBadges=renderTagBadges(tags,'heme');
        const diseaseStr=(tags.disease||[]).join('、')||'-';
        const line=lineLabel(d.therapy_line);
        const auth=d.prior_auth?'<span class="badge badge-auth">需審查</span>':'-';
        const priceHtml=d.nhi_price?`<span class="price-tag">$${Number(d.nhi_price).toLocaleString()}</span><span class="price-unit">${esc(d.price_unit||'')}</span>`:'<span style="color:var(--muted)">-</span>';
        return `<tr class="clickable" onclick="showDetail(${d.id})" style="${ok===false?'opacity:.6':''}">
            <td>${icon}</td>
            <td><span class="drug-name">${esc(d.generic_name)}</span>${brandHtml}</td>
            <td>${diseaseStr}</td>
            <td>${d.therapy_line?'<span class="badge badge-line">'+line+'</span>':'-'}</td>
            <td>${auth}</td>
            <td>${priceHtml}</td>
            <td>${tagBadges}</td>
        </tr>`;
    });
    if(hasF){
        const sorted=list.map((d,i)=>({d,i,ok:matchesFilters(d,activeFilters)}));
        sorted.sort((a,b)=>(b.ok?1:0)-(a.ok?1:0));
        document.getElementById('hemeBody').innerHTML=sorted.map(x=>rows[x.i]).join('');
        document.getElementById('hemeInfo').textContent=`共 ${list.length} 筆｜符合條件 ${matched} 筆｜不符合 ${unmatched} 筆（不符合者仍可自費使用）`;
    } else {
        document.getElementById('hemeBody').innerHTML=rows.join('')||'<tr><td colspan="7"><div class="empty">沒有找到藥物</div></td></tr>';
        document.getElementById('hemeInfo').textContent=`共 ${list.length} 筆`;
    }
}

function renderTagBadges(tags,type){
    const badges=[];
    if(type==='breast'){
        if(tags.her2==='positive')badges.push('<span class="badge" style="background:#dcfce7;color:#166534">HER2+</span>');
        if(tags.her2==='negative')badges.push('<span class="badge" style="background:#fee2e2;color:#991b1b">HER2-</span>');
        if(tags.er_pr==='positive')badges.push('<span class="badge" style="background:#dbeafe;color:#1e40af">ER/PR+</span>');
        if(tags.er_pr==='negative')badges.push('<span class="badge" style="background:#fef3c7;color:#92400e">ER/PR-</span>');
        if(tags.tnbc)badges.push('<span class="badge" style="background:#f3e8ff;color:#7c3aed">三陰性</span>');
        if(tags.ln)badges.push('<span class="badge badge-tag">LN轉移</span>');
        if(tags.brca)badges.push('<span class="badge badge-tag">BRCA</span>');
        if(tags.pik3ca)badges.push('<span class="badge badge-tag">PIK3CA</span>');
    } else {
        if(tags.disease)(tags.disease).forEach(d=>badges.push('<span class="badge badge-tag">'+d+'</span>'));
        if(tags.ph_positive)badges.push('<span class="badge badge-tag">Ph+</span>');
        if(tags.flt3)badges.push('<span class="badge badge-tag">FLT3</span>');
    }
    return badges.join(' ')||'-';
}

// ── Detail ──
async function showDetail(id){
    const r=await fetch('/api/drug/'+id);const d=await r.json();
    const tags=typeof d.clinical_tags==='string'?JSON.parse(d.clinical_tags||'{}'):d.clinical_tags||{};
    const cat=d.specialty_id==='oncology_breast'?'<span class="badge badge-breast">乳癌</span>':'<span class="badge badge-heme">血液腫瘤</span>';
    const line=d.therapy_line?'<span class="badge badge-line">第'+d.therapy_line+'線</span>':'<span style="color:var(--muted)">未指定</span>';
    const auth=d.prior_auth?'<span class="badge badge-auth">需事前審查</span>':'<span style="color:var(--green);font-weight:600">無需事前審查</span>';
    const priceStr=d.nhi_price?`NT$ ${Number(d.nhi_price).toLocaleString()} / ${esc(d.price_unit||'')}`:'尚無藥價資料';
    let dosage=null;
    try{dosage=d.dosage_info?JSON.parse(d.dosage_info):null}catch(e){}
    let h=`<h2>${esc(d.generic_name)}</h2>
        <div class="sub">${d.trade_names?'商品名：'+esc(d.trade_names):'尚無商品名資料'}</div>
        <div class="detail-sec"><h3>基本資訊</h3><p>
            <strong>分類：</strong>${cat}<br>
            <strong>分期：</strong>${stageLabel(d.stage)}<br>
            <strong>療程線：</strong>${line}<br>
            <strong>事前審查：</strong>${auth}<br>
            <strong>健保藥價：</strong><span style="color:#7c3aed;font-weight:600">${priceStr}</span>
            ${dosage?'<br><strong>用法用量：</strong>'+esc(dosage.note||''):''}
        </p></div>`;
    if(d.indication){
        h+=`<div class="detail-sec"><h3>適應症</h3>${d.indication.split(' | ').map(p=>'<p>'+esc(p)+'</p>').join('')}</div>`;
    }
    if(d.conditions){
        h+=`<div class="detail-sec"><h3>給付條件</h3>${d.conditions.split(' | ').map(p=>'<p>'+esc(p)+'</p>').join('')}</div>`;
    }
    // Cost calculator — combo takes priority for HP dual-blockade drugs
    const combo = getComboForDrug(d.generic_name, d.trade_names);
    if(combo){
        h+=buildComboCalc(combo, d.generic_name);
    } else if(d.nhi_price && dosage){
        h+=buildCostCalc(d, dosage);
    }
    h+=`<div class="btn-row">
        <button class="btn btn-outline btn-sm" onclick="closeDetail();openEditDrug(${d.id})">編輯此藥物</button>
    </div>`;
    // Cache dosage info for single-drug calculator
    if(d.nhi_price && dosage && !combo){
        _drugDosageCache[d.id] = {dosage: dosage, price: d.nhi_price, price_unit: d.price_unit};
    }
    document.getElementById('detailBody').innerHTML=h;
    document.getElementById('detailModal').classList.add('show');
    // Auto-calculate on open
    if(combo){
        setTimeout(()=>{
            applyScenario(combo.id, 0);  // default: N+ scenario
            applyDuration(combo.id, 1);  // default: 12 months
        }, 100);
    } else if(d.nhi_price && dosage){
        setTimeout(()=>calcCost(d.id), 100);
    }
}
function closeDetail(){document.getElementById('detailModal').classList.remove('show')}

// ── Edit Drug ──
async function openEditDrug(id){
    const r=await fetch('/api/drug/'+id);const d=await r.json();
    document.getElementById('editBody').innerHTML=`
        <h2>編輯藥物</h2>
        <div class="edit-form">
            <div class="form-row"><label>藥物名稱</label><input id="eN" value="${esc(d.generic_name)}"></div>
            <div class="form-row"><label>商品名</label><input id="eT" value="${esc(d.trade_names||'')}"></div>
            <div class="form-row"><label>分類</label><select id="eS">
                <option value="oncology_breast" ${d.specialty_id==='oncology_breast'?'selected':''}>乳癌</option>
                <option value="oncology_heme" ${d.specialty_id==='oncology_heme'?'selected':''}>血液腫瘤</option>
            </select></div>
            <div class="form-row"><label>適應症</label><textarea id="eI" rows="4">${esc(d.indication||'')}</textarea></div>
            <div class="form-row"><label>給付條件</label><textarea id="eC" rows="4">${esc(d.conditions||'')}</textarea></div>
            <div class="btn-row">
                <button class="btn btn-danger btn-sm" onclick="deleteDrug(${d.id})">刪除</button>
                <button class="btn btn-outline btn-sm" onclick="closeEdit()">取消</button>
                <button class="btn btn-success btn-sm" onclick="saveDrug(${d.id})">儲存</button>
            </div>
        </div>`;
    document.getElementById('editModal').classList.add('show');
}
async function saveDrug(id){
    const body={
        generic_name:document.getElementById('eN').value,
        trade_names:document.getElementById('eT').value,
        specialty_id:document.getElementById('eS').value,
        indication:document.getElementById('eI').value,
        conditions:document.getElementById('eC').value,
    };
    await fetch('/api/drug/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    closeEdit();
    alert('已儲存');
    // Reload current page
    if(document.getElementById('breastPage').classList.contains('active'))showBreast();
    else if(document.getElementById('hemePage').classList.contains('active'))showHeme();
}
async function deleteDrug(id){
    if(!confirm('確定要刪除此藥物？'))return;
    await fetch('/api/drug/'+id,{method:'DELETE'});
    closeEdit();
    if(document.getElementById('breastPage').classList.contains('active'))showBreast();
    else if(document.getElementById('hemePage').classList.contains('active'))showHeme();
    else loadLanding();
}
function closeEdit(){document.getElementById('editModal').classList.remove('show')}

// ── Add Drug ──
function openAddDrug(){
    document.getElementById('editBody').innerHTML=`
        <h2>新增藥物</h2>
        <div class="edit-form">
            <div class="form-row"><label>藥物名稱</label><input id="eN" placeholder="例如 Pembrolizumab"></div>
            <div class="form-row"><label>商品名</label><input id="eT" placeholder="例如 Keytruda"></div>
            <div class="form-row"><label>分類</label><select id="eS">
                <option value="oncology_breast">乳癌</option>
                <option value="oncology_heme">血液腫瘤</option>
            </select></div>
            <div class="form-row"><label>適應症</label><textarea id="eI" rows="3"></textarea></div>
            <div class="form-row"><label>給付條件</label><textarea id="eC" rows="3"></textarea></div>
            <div class="btn-row">
                <button class="btn btn-outline btn-sm" onclick="closeEdit()">取消</button>
                <button class="btn btn-success btn-sm" onclick="addDrug()">新增</button>
            </div>
        </div>`;
    document.getElementById('editModal').classList.add('show');
}
async function addDrug(){
    const body={
        generic_name:document.getElementById('eN').value,
        trade_names:document.getElementById('eT').value,
        specialty_id:document.getElementById('eS').value,
        indication:document.getElementById('eI').value,
        conditions:document.getElementById('eC').value,
    };
    if(!body.generic_name){alert('請輸入藥物名稱');return}
    await fetch('/api/drugs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    closeEdit();alert('已新增');loadLanding();
}

// ── Version Check ──
async function checkVersion(){
    try{
        const r=await fetch('/api/version');const d=await r.json();
        if(d.update_available){
            document.getElementById('versionMsg').textContent=d.message;
            document.getElementById('versionBanner').classList.add('show');
        }
    }catch(e){}
}

// ── Cost Calculator ──
function buildCostCalc(drug, dosage){
    const needsWeight = !!dosage.dose_per_kg;
    const needsBSA = !!dosage.dose_per_bsa;
    const id = drug.id;
    let fields = '';
    if(needsWeight){
        fields += `<div class="field"><label>體重 (kg)</label><input type="number" id="calcWt${id}" value="60" min="30" max="150" onchange="calcCost(${id})"></div>`;
    }
    if(needsBSA){
        fields += `<div class="field"><label>身高 (cm)</label><input type="number" id="calcHt${id}" value="165" min="140" max="200" onchange="calcCost(${id})"></div>`;
        fields += `<div class="field"><label>體重 (kg)</label><input type="number" id="calcWt${id}" value="60" min="30" max="150" onchange="calcCost(${id})"></div>`;
    }
    fields += `<div class="field"><label>療程週期數</label><input type="number" id="calcCy${id}" value="${dosage.cycles||6}" min="1" max="52" onchange="calcCost(${id})"></div>`;

    return `<div class="calc-box">
        <h3>療程費用試算</h3>
        <div class="calc-row">${fields}
            <div class="field"><button class="btn btn-primary btn-sm" onclick="calcCost(${id})" style="margin-top:1.1rem;background:#7c3aed">計算費用</button></div>
        </div>
        <div id="calcResult${id}"></div>
    </div>`;
}

// Store dosage info for cost calculation
let _drugDosageCache = {};

function calcCost(drugId){
    const drug = _drugDosageCache[drugId];
    if(!drug) return;
    const dosage = drug.dosage;
    const price = drug.price;
    const unitStr = drug.price_unit || '';

    // Parse unit amount from price_unit (e.g., "100mg/vial" → 100)
    const unitMatch = unitStr.match(/(\d+(?:\.\d+)?)\s*mg/);
    const unitMg = unitMatch ? parseFloat(unitMatch[1]) : 1;

    let dosePerAdmin = 0; // mg per administration
    let bsa = 1.7; // default BSA

    const wtEl = document.getElementById('calcWt'+drugId);
    const htEl = document.getElementById('calcHt'+drugId);
    const cyEl = document.getElementById('calcCy'+drugId);
    const wt = wtEl ? parseFloat(wtEl.value) : 60;
    const ht = htEl ? parseFloat(htEl.value) : 165;
    const cycles = cyEl ? parseInt(cyEl.value) : 6;

    if(dosage.dose_per_kg){
        dosePerAdmin = dosage.dose_per_kg * wt;
    } else if(dosage.dose_per_bsa){
        bsa = Math.sqrt((ht * wt) / 3600); // Mosteller formula
        dosePerAdmin = dosage.dose_per_bsa * bsa;
    } else if(dosage.dose_fixed){
        dosePerAdmin = dosage.dose_fixed;
    }

    // Units needed per administration
    const unitsPerAdmin = Math.ceil(dosePerAdmin / unitMg);
    const costPerAdmin = unitsPerAdmin * price;

    // Administrations per cycle
    let adminsPerCycle = 1;
    let cycleDays = 21;
    const freq = dosage.freq || '';
    const schedule = dosage.schedule || '';

    if(freq === 'daily' || freq === 'bid'){
        if(schedule){
            const [on, total] = schedule.split('/').map(Number);
            cycleDays = total;
            adminsPerCycle = on * (freq === 'bid' ? 2 : 1);
        } else {
            cycleDays = 28;
            adminsPerCycle = 28 * (freq === 'bid' ? 2 : 1);
        }
    } else if(freq === 'q3w'){
        cycleDays = 21; adminsPerCycle = 1;
    } else if(freq === 'q2w'){
        cycleDays = 14; adminsPerCycle = 1;
    } else if(freq === 'q4w'){
        cycleDays = 28; adminsPerCycle = 1;
    } else if(freq === 'weekly'){
        if(schedule){
            const [on, total] = schedule.split('/').map(Number);
            cycleDays = total * 7;
            adminsPerCycle = on;
        } else {
            cycleDays = 7; adminsPerCycle = 1;
        }
    } else if(freq === 'biweekly'){
        cycleDays = 21; adminsPerCycle = 4; // 2x/wk x 2wks
    } else if(freq === 'daily_or_bid'){
        cycleDays = 28; adminsPerCycle = 28;
    } else if(freq.includes('q4w')){
        cycleDays = 28; adminsPerCycle = 1;
    }

    const costPerCycle = costPerAdmin * adminsPerCycle;
    const totalCost = costPerCycle * cycles;
    const totalMonths = (cycleDays * cycles / 30).toFixed(1);

    let bsaLine = '';
    if(dosage.dose_per_bsa){
        bsaLine = `<div class="cost-line"><span>體表面積 (BSA)</span><span>${bsa.toFixed(2)} m&sup2;</span></div>`;
    }

    document.getElementById('calcResult'+drugId).innerHTML = `
        <div class="calc-result">
            ${bsaLine}
            <div class="cost-line"><span>每次劑量</span><span>${Math.round(dosePerAdmin)} mg (${unitsPerAdmin} ${unitStr.includes('vial')?'瓶':unitStr.includes('tab')?'錠':unitStr.includes('cap')?'粒':'單位'})</span></div>
            <div class="cost-line"><span>每次費用</span><span>NT$ ${costPerAdmin.toLocaleString()}</span></div>
            <div class="cost-line"><span>每週期次數</span><span>${adminsPerCycle} 次 / ${cycleDays} 天</span></div>
            <div class="cost-line"><span>每週期費用</span><span>NT$ ${costPerCycle.toLocaleString()}</span></div>
            <div class="cost-line total"><span>全療程費用 (${cycles} 週期, 約 ${totalMonths} 個月)</span><span>NT$ ${totalCost.toLocaleString()}</span></div>
            <div class="cost-note">* 藥價依據「115年藥品支付價格年度例行調整結果明細表」（生效日：115/04/01），實際費用可能因劑量調整、藥品規格、耗損等因素而異。自費使用之藥價通常高於健保支付價。</div>
        </div>`;
}

// ── Combo Calculator ──
// Known combination drug protocols
const DRUG_COMBOS = {
  // HP dual-blockade: Herceptin + Perjeta
  'hp_combo': {
    id: 'hp_combo',
    name: 'HP 雙標靶療法 (Herceptin + Perjeta)',
    desc: '用於 HER2 陽性乳癌術後輔助或轉移性乳癌治療',
    drugs: [
      {
        key: 'herceptin',
        name: 'Trastuzumab (Herceptin)',
        price: 28518,
        price_unit: '440mg/vial',
        unit_mg: 440,
        loading_dose_per_kg: 8,   // first dose mg/kg
        maint_dose_per_kg: 6,     // maintenance mg/kg
        freq: 'q3w',
        note: '首劑8mg/kg，後續6mg/kg，每3週一次',
        nhi_default: true
      },
      {
        key: 'perjeta',
        name: 'Pertuzumab (Perjeta)',
        price: 44929,
        price_unit: '420mg/vial',
        unit_mg: 420,
        loading_dose_fixed: 840,  // first dose mg
        maint_dose_fixed: 420,    // maintenance mg
        freq: 'q3w',
        note: '首劑840mg，後續420mg，每3週一次',
        nhi_default: false
      }
    ],
    durations: [
      {label:'6 個月', cycles:8},
      {label:'12 個月（標準輔助）', cycles:18}
    ],
    scenarios: [
      {
        label:'淋巴節轉移 (N+)',
        desc:'Herceptin 健保給付，Perjeta 自費',
        nhi: {herceptin:true, perjeta:false}
      },
      {
        label:'淋巴節無轉移 (N0)',
        desc:'Herceptin 與 Perjeta 均需自費',
        nhi: {herceptin:false, perjeta:false}
      },
      {
        label:'兩藥均健保',
        desc:'',
        nhi: {herceptin:true, perjeta:true}
      }
    ]
  }
};

// Detect if a drug name triggers a combo calculator
function getComboForDrug(genericName, tradeName){
  const n=(genericName||'').toLowerCase();
  const t=(tradeName||'').toLowerCase();
  if(n.includes('trastuzumab')||n.includes('herceptin')||t.includes('herceptin')||
     n.includes('pertuzumab')||n.includes('perjeta')||t.includes('perjeta')){
    return DRUG_COMBOS['hp_combo'];
  }
  return null;
}

let _comboCoverage = {};  // {herceptin: true/false, perjeta: true/false}

function buildComboCalc(combo, currentDrugName){
  // init coverage from defaults
  combo.drugs.forEach(d=>{ _comboCoverage[d.key]=d.nhi_default; });

  const scenarioBtns = combo.scenarios.map((s,i)=>`
    <button class="scenario-btn" id="scBtn${i}" onclick="applyScenario('${combo.id}',${i})">${s.label}</button>
  `).join('');

  const durationBtns = combo.durations.map((d,i)=>`
    <button class="scenario-btn" id="durBtn${i}" onclick="applyDuration('${combo.id}',${i})">${d.label}</button>
  `).join('');

  return `<div class="combo-box" id="comboBox_${combo.id}">
    <h3>🔗 ${combo.name}</h3>
    <div class="combo-desc">${combo.desc}</div>
    <div style="margin-bottom:.5rem"><strong style="font-size:.78rem;color:var(--muted)">健保情境：</strong><br>
      <div class="scenario-btns" style="margin-top:.3rem">${scenarioBtns}</div>
    </div>
    <div class="combo-drugs" id="comboDrugs_${combo.id}">
      ${combo.drugs.map(d=>buildComboDrugCard(d, combo.id)).join('')}
    </div>
    <div class="combo-inputs">
      <div class="field">
        <label>患者體重 (kg)</label>
        <input type="number" id="comboWt_${combo.id}" value="60" min="30" max="150" onchange="calcCombo('${combo.id}')">
      </div>
      <div class="field">
        <label>快速選擇療程</label>
        <div class="scenario-btns" style="margin:0">${durationBtns}</div>
      </div>
      <div class="field">
        <label>療程週期數 (q3w)</label>
        <input type="number" id="comboCy_${combo.id}" value="18" min="1" max="36" onchange="calcCombo('${combo.id}')">
      </div>
      <div class="field" style="flex:0">
        <button class="btn btn-primary btn-sm" onclick="calcCombo('${combo.id}')" style="background:#6d28d9;margin-top:1.1rem">計算費用</button>
      </div>
    </div>
    <div id="comboResult_${combo.id}"></div>
  </div>`;
}

function buildComboDrugCard(drug, comboId){
  const covered = _comboCoverage[drug.key] !== false ? drug.nhi_default : _comboCoverage[drug.key];
  const cardClass = covered ? 'nhi-covered' : 'self-pay';
  const nhiBtn = covered ? 'active-nhi' : '';
  const selfBtn = covered ? '' : 'active-self';
  return `<div class="combo-drug-card ${cardClass}" id="card_${drug.key}">
    <div class="combo-drug-name">${drug.name}</div>
    <div class="coverage-toggle">
      <button id="nhiBtn_${drug.key}" class="${nhiBtn}" onclick="setCoverage('${comboId}','${drug.key}',true)">✓ 健保給付</button>
      <button id="selfBtn_${drug.key}" class="${selfBtn}" onclick="setCoverage('${comboId}','${drug.key}',false)">自費</button>
    </div>
    <div class="combo-drug-detail">${drug.note}</div>
    <div class="combo-drug-detail" style="margin-top:.2rem">藥價：NT$${drug.price.toLocaleString()} / ${drug.price_unit}</div>
  </div>`;
}

function setCoverage(comboId, drugKey, isNHI){
  _comboCoverage[drugKey] = isNHI;
  const card = document.getElementById('card_'+drugKey);
  if(card){
    card.className = 'combo-drug-card ' + (isNHI ? 'nhi-covered' : 'self-pay');
  }
  const nhiBtn = document.getElementById('nhiBtn_'+drugKey);
  const selfBtn = document.getElementById('selfBtn_'+drugKey);
  if(nhiBtn) nhiBtn.className = isNHI ? 'active-nhi' : '';
  if(selfBtn) selfBtn.className = isNHI ? '' : 'active-self';
  calcCombo(comboId);
}

function applyScenario(comboId, idx){
  const combo = DRUG_COMBOS[comboId];
  if(!combo) return;
  const s = combo.scenarios[idx];
  Object.keys(s.nhi).forEach(k=>setCoverage(comboId, k, s.nhi[k]));
  // highlight active scenario button
  combo.scenarios.forEach((_,i)=>{
    const b=document.getElementById('scBtn'+i);
    if(b) b.className='scenario-btn'+(i===idx?' active':'');
  });
  calcCombo(comboId);
}

function applyDuration(comboId, idx){
  const combo = DRUG_COMBOS[comboId];
  if(!combo) return;
  const dur = combo.durations[idx];
  const cyEl = document.getElementById('comboCy_'+comboId);
  if(cyEl) cyEl.value = dur.cycles;
  combo.durations.forEach((_,i)=>{
    const b=document.getElementById('durBtn'+i);
    if(b) b.className='scenario-btn'+(i===idx?' active':'');
  });
  calcCombo(comboId);
}

function calcCombo(comboId){
  const combo = DRUG_COMBOS[comboId];
  if(!combo) return;
  const wtEl = document.getElementById('comboWt_'+comboId);
  const cyEl = document.getElementById('comboCy_'+comboId);
  const wt = wtEl ? parseFloat(wtEl.value)||60 : 60;
  const cycles = cyEl ? parseInt(cyEl.value)||18 : 18;
  const months = (cycles * 21 / 30).toFixed(1);

  let nhiTotal = 0, selfTotal = 0;
  let drugLines = '';

  combo.drugs.forEach(drug => {
    const isNHI = _comboCoverage[drug.key] !== undefined ? _comboCoverage[drug.key] : drug.nhi_default;

    // Loading dose (cycle 1)
    let loadingMg = 0;
    if(drug.loading_dose_per_kg) loadingMg = drug.loading_dose_per_kg * wt;
    else if(drug.loading_dose_fixed) loadingMg = drug.loading_dose_fixed;

    // Maintenance dose (cycles 2+)
    let maintMg = 0;
    if(drug.maint_dose_per_kg) maintMg = drug.maint_dose_per_kg * wt;
    else if(drug.maint_dose_fixed) maintMg = drug.maint_dose_fixed;

    const loadingVials = Math.ceil(loadingMg / drug.unit_mg);
    const maintVials = Math.ceil(maintMg / drug.unit_mg);
    const maintCycles = Math.max(cycles - 1, 0);
    const totalVials = (cycles >= 1 ? loadingVials : 0) + maintVials * maintCycles;
    const totalCost = totalVials * drug.price;

    const unitLabel = drug.price_unit.includes('vial') ? '瓶' : '單位';
    const coverLabel = isNHI ? '<span style="color:#059669">健保給付</span>' : '<span style="color:#dc2626">自費</span>';
    drugLines += `<div class="cost-line">
      <span>${drug.name.split('(')[0].trim()} [${coverLabel}]<br>
        <small style="color:var(--muted)">首劑${loadingVials}${unitLabel} + 後續${maintCycles}次×${maintVials}${unitLabel} = 共${totalVials}${unitLabel}</small>
      </span>
      <span>NT$ ${totalCost.toLocaleString()}</span>
    </div>`;

    if(isNHI) nhiTotal += totalCost; else selfTotal += totalCost;
  });

  const grandTotal = nhiTotal + selfTotal;
  const nhiLine = nhiTotal > 0
    ? `<div class="cost-line nhi-line"><span>健保給付小計</span><span>NT$ ${nhiTotal.toLocaleString()}</span></div>` : '';
  const selfLine = selfTotal > 0
    ? `<div class="cost-line self-line"><span>自費小計</span><span>NT$ ${selfTotal.toLocaleString()}</span></div>` : '';

  document.getElementById('comboResult_'+comboId).innerHTML = `
    <div class="combo-result">
      <div class="cost-line" style="font-weight:600;color:#6d28d9;margin-bottom:.3rem">
        <span>療程明細 (${cycles} 週期 q3w，約 ${months} 個月，體重 ${wt}kg)</span>
      </div>
      ${drugLines}
      <div style="border-top:1px dashed #e9d5ff;margin:.5rem 0"></div>
      ${nhiLine}${selfLine}
      <div class="cost-line total-line">
        <span>患者自費總計</span>
        <span class="total-self">NT$ ${selfTotal.toLocaleString()}</span>
      </div>
      <div class="cost-line" style="font-size:.85rem">
        <span>全療程藥費合計（含健保）</span>
        <span>NT$ ${grandTotal.toLocaleString()}</span>
      </div>
      <div class="cost-note">* 首劑為較高的起始劑量（Herceptin 8mg/kg，Perjeta 840mg），後續為維持劑量。<br>
        藥價依據 115年健保支付標準（生效日：115/04/01）。實際費用以醫院計算為準。</div>
    </div>`;
}

// ── Util ──
function esc(s){if(!s)return'';const d=document.createElement('div');d.textContent=s;return d.innerHTML}
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeDetail();closeEdit()}});
</script>
</body>
</html>"""


# ─── HTTP Handler ─────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        path, params = p.path, urllib.parse.parse_qs(p.query)
        if path in ('/', '/index.html'):
            self._html()
        elif path == '/api/stats':
            self._stats()
        elif path == '/api/drugs':
            self._drugs(params)
        elif path.startswith('/api/drug/'):
            self._drug_detail(path.split('/')[-1])
        elif path == '/api/version':
            self._version()
        else:
            self._json(404, {'error': 'Not found'})

    def do_PUT(self):
        if self.path.startswith('/api/drug/'):
            drug_id = self.path.split('/')[-1]
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self._update_drug(drug_id, body)

    def do_POST(self):
        if self.path == '/api/drugs':
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self._add_drug(body)

    def do_DELETE(self):
        if self.path.startswith('/api/drug/'):
            drug_id = self.path.split('/')[-1]
            self._delete_drug(drug_id)

    # ── Handlers ──

    def _html(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))

    def _stats(self):
        c = get_db(); cur = c.cursor()
        cur.execute("SELECT COUNT(*) as c FROM drugs"); total = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM drugs WHERE specialty_id='oncology_breast'"); breast = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM drugs WHERE specialty_id='oncology_heme'"); heme = cur.fetchone()['c']
        c.close()
        self._json(200, {'total': total, 'breast': breast, 'heme': heme})

    def _drugs(self, params):
        c = get_db(); cur = c.cursor()
        q = params.get('q', [''])[0]
        cat = params.get('category', [''])[0]
        sql = """SELECT d.id, d.generic_name, d.trade_names, d.specialty_id, d.indication, d.clinical_tags, d.stage,
                        cr.therapy_line, cr.prior_auth_required as prior_auth, cr.condition as conditions,
                        d.nhi_price, d.price_unit, d.dosage_info
                 FROM drugs d LEFT JOIN coverage_rules cr ON cr.drug_id = d.id WHERE 1=1"""
        p = []
        if q:
            sql += " AND (LOWER(d.generic_name) LIKE LOWER(?) OR LOWER(d.trade_names) LIKE LOWER(?))"
            p += [f'%{q}%', f'%{q}%']
        if cat:
            sql += " AND d.specialty_id=?"
            p.append(cat)
        sql += " ORDER BY d.generic_name"
        cur.execute(sql, p)
        drugs = []
        for r in cur.fetchall():
            tags = r['clinical_tags'] or '{}'
            try:
                tags = json.loads(tags)
            except:
                tags = {}
            drugs.append({
                'id': r['id'], 'generic_name': r['generic_name'], 'trade_names': r['trade_names'],
                'specialty_id': r['specialty_id'], 'indication': r['indication'],
                'clinical_tags': tags, 'stage': r['stage'] or '',
                'therapy_line': r['therapy_line'], 'prior_auth': bool(r['prior_auth']),
                'conditions': r['conditions'],
                'nhi_price': r['nhi_price'], 'price_unit': r['price_unit'] or '',
                'dosage_info': r['dosage_info'] or '',
            })
        c.close()
        self._json(200, drugs)

    def _drug_detail(self, drug_id):
        c = get_db(); cur = c.cursor()
        cur.execute("""SELECT d.*, cr.therapy_line, cr.prior_auth_required as prior_auth, cr.condition as conditions
                       FROM drugs d LEFT JOIN coverage_rules cr ON cr.drug_id=d.id WHERE d.id=?""", (drug_id,))
        r = cur.fetchone(); c.close()
        if not r:
            return self._json(404, {'error': 'Not found'})
        self._json(200, {
            'id': r['id'], 'generic_name': r['generic_name'], 'trade_names': r['trade_names'],
            'specialty_id': r['specialty_id'], 'indication': r['indication'],
            'clinical_tags': r['clinical_tags'], 'stage': r['stage'] or '',
            'therapy_line': r['therapy_line'], 'prior_auth': bool(r['prior_auth']),
            'conditions': r['conditions'],
            'nhi_price': r['nhi_price'], 'price_unit': r['price_unit'] or '',
            'dosage_info': r['dosage_info'] or '',
        })

    def _update_drug(self, drug_id, body):
        c = get_db(); cur = c.cursor()
        cur.execute("UPDATE drugs SET generic_name=?, trade_names=?, specialty_id=?, indication=? WHERE id=?",
                    (body['generic_name'], body.get('trade_names', ''), body['specialty_id'], body.get('indication', ''), drug_id))
        if body.get('conditions') is not None:
            cur.execute("UPDATE coverage_rules SET condition=? WHERE drug_id=?", (body['conditions'], drug_id))
        c.commit(); c.close()
        self._json(200, {'ok': True})

    def _add_drug(self, body):
        c = get_db(); cur = c.cursor()
        cur.execute("INSERT INTO drugs (generic_name, trade_names, specialty_id, indication, created_date) VALUES (?,?,?,?,?)",
                    (body['generic_name'], body.get('trade_names', ''), body['specialty_id'], body.get('indication', ''), datetime.now().date()))
        drug_id = cur.lastrowid
        cur.execute("INSERT INTO coverage_rules (drug_id, condition) VALUES (?,?)", (drug_id, body.get('conditions', '')))
        c.commit(); c.close()
        self._json(201, {'ok': True, 'id': drug_id})

    def _delete_drug(self, drug_id):
        c = get_db(); cur = c.cursor()
        cur.execute("DELETE FROM coverage_rules WHERE drug_id=?", (drug_id,))
        cur.execute("DELETE FROM drugs WHERE id=?", (drug_id,))
        c.commit(); c.close()
        self._json(200, {'ok': True})

    def _version(self):
        # Check if there's a newer version available (compare file dates)
        import os
        docx_files = list(Path(__file__).parent.glob("完整給付規定*.docx"))
        info = {'update_available': False, 'message': '', 'current_file': ''}
        if docx_files:
            newest = max(docx_files, key=lambda f: f.stat().st_mtime)
            info['current_file'] = newest.name
            info['last_modified'] = datetime.fromtimestamp(newest.stat().st_mtime).strftime('%Y-%m-%d')
        self._json(200, info)

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_HEAD(self):
        p = urllib.parse.urlparse(self.path)
        if p.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    host, port = '127.0.0.1', 8080
    print("=" * 60)
    print("  健保藥物給付規定查詢系統")
    print("=" * 60)
    print(f"\n  網址：http://{host}:{port}")
    print(f"  資料庫：{DB_PATH}")
    print(f"\n  按 Ctrl+C 停止伺服器")
    print("=" * 60)
    server = HTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已停止。")
        server.server_close()


if __name__ == '__main__':
    main()

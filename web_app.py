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
    # 自動補欄位（相容舊資料庫）
    cols = [r[1] for r in conn.execute('PRAGMA table_info(drugs)').fetchall()]
    if 'drug_image_url' not in cols:
        conn.execute('ALTER TABLE drugs ADD COLUMN drug_image_url TEXT')
        conn.commit()
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

/* ── Inner Tabs ── */
.inner-tabs{display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:1rem}
.inner-tab{padding:.6rem 1.2rem;border:none;background:none;font-size:.85rem;font-weight:600;color:var(--muted);cursor:pointer;border-bottom:3px solid transparent;transition:all .15s}
.inner-tab:hover{color:var(--primary)}
.inner-tab.active{color:#be185d;border-bottom-color:#be185d}
.tab-content{display:none}.tab-content.active{display:block}

/* ── Regimen Calculator ── */
.reg-section{margin-bottom:1.2rem}
.reg-section h3{font-size:.9rem;font-weight:700;margin-bottom:.5rem;color:#1e293b}
.patient-inputs{display:flex;gap:1rem;flex-wrap:wrap;align-items:end;background:var(--card);padding:1rem;border-radius:10px;border:1px solid var(--border)}
.patient-inputs .field{flex:1;min-width:110px}
.patient-inputs label{display:block;font-size:.73rem;font-weight:600;color:var(--muted);margin-bottom:.2rem}
.patient-inputs input,.patient-inputs select{width:100%;padding:.4rem .5rem;border:2px solid var(--border);border-radius:6px;font-size:.85rem}
.patient-inputs input:focus,.patient-inputs select:focus{border-color:#be185d;outline:none}
.bsa-display{background:#fce7f3;color:#be185d;padding:.3rem .6rem;border-radius:6px;font-weight:700;font-size:.85rem;align-self:center}
.condition-bar{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}
.cond-btn{padding:.35rem .7rem;border-radius:18px;border:2px solid #e2e8f0;background:#fff;font-size:.78rem;font-weight:600;cursor:pointer;transition:all .12s}
.cond-btn:hover{border-color:#be185d;color:#be185d}
.cond-btn.active{background:#be185d;color:#fff;border-color:#be185d}
.regimen-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.6rem}
.reg-card{background:var(--card);border:2px solid var(--border);border-radius:10px;padding:.8rem;cursor:pointer;transition:all .15s}
.reg-card:hover{border-color:#be185d;box-shadow:0 2px 8px rgba(190,24,93,.12)}
.reg-card.selected{border-color:#be185d;background:#fdf2f8}
.reg-card h4{font-size:.82rem;margin-bottom:.2rem;color:#1e293b}
.reg-card .reg-desc{font-size:.72rem;color:var(--muted)}
.phase-box{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.8rem;margin-bottom:.8rem}
.phase-box h4{font-size:.82rem;color:#6d28d9;margin-bottom:.5rem;display:flex;justify-content:space-between}
.drug-row{display:flex;align-items:center;gap:.5rem;padding:.4rem 0;border-bottom:1px solid #f1f5f9;flex-wrap:wrap}
.drug-row:last-child{border-bottom:none}
.drug-row .drug-info{flex:1;min-width:180px}
.drug-row .drug-name-r{font-weight:600;font-size:.82rem}
.drug-row .drug-dose{font-size:.73rem;color:var(--muted)}
.drug-row .vial-combo{font-size:.73rem;color:#6d28d9;font-weight:500}
.drug-row .drug-cost{font-weight:700;font-size:.85rem;color:#7c3aed;min-width:100px;text-align:right}
.nhi-toggle{display:inline-flex;border-radius:5px;overflow:hidden;border:1.5px solid #d1d5db;font-size:.7rem}
.nhi-toggle button{padding:.15rem .45rem;border:none;background:#f8fafc;color:#64748b;cursor:pointer;font-weight:600;transition:.12s}
.nhi-toggle button.on-nhi{background:#059669;color:#fff}
.nhi-toggle button.on-self{background:#dc2626;color:#fff}
.reg-summary{background:#fdf2f8;border:2px solid #f9a8d4;border-radius:12px;padding:1rem;margin-top:.5rem}
.reg-summary .sum-line{display:flex;justify-content:space-between;padding:.2rem 0;font-size:.85rem}
.reg-summary .sum-total{font-weight:700;font-size:1.05rem;border-top:2px solid #f9a8d4;margin-top:.3rem;padding-top:.5rem}
.reg-summary .sum-nhi{color:#059669}
.reg-summary .sum-self{color:#dc2626}
.reg-summary .sum-grand{color:#6d28d9}
.reg-summary .sum-note{font-size:.73rem;color:var(--muted);margin-top:.5rem;font-style:italic}
.add-on-row{display:flex;align-items:center;gap:.8rem;padding:.3rem 0}
.add-on-row input[type=checkbox]{width:16px;height:16px;accent-color:#be185d}
.add-on-label{font-size:.82rem;flex:1}
.add-on-price{font-size:.82rem;font-weight:600;color:#7c3aed}

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
<div id="offlineBar" style="display:none;background:#f59e0b;color:#fff;text-align:center;padding:0.4rem;font-size:0.85rem;font-weight:600">離線模式 — 使用快取資料，部分功能可能受限</div>
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
            <button class="btn btn-outline" onclick="openManageTools()">管理工具</button>
        </div>
    </div>

    <!-- ===== Breast Cancer Page ===== -->
    <div id="breastPage" class="dept-page">
        <button class="back-btn" onclick="showLanding()">&#8592; 返回首頁</button>
        <h2 style="margin:.5rem 0 1rem;color:var(--pink)">乳癌藥物給付查詢</h2>

        <div class="inner-tabs">
            <button class="inner-tab active" id="tabDrugs" onclick="switchBreastTab('drugs')">藥物查詢</button>
            <button class="inner-tab" id="tabRegimen" onclick="switchBreastTab('regimen')">處方費用計算</button>
        </div>

        <div class="tab-content active" id="tabDrugsContent">
        <div class="filter-panel">
            <h3>臨床條件篩選</h3>
            <div class="search-row">
                <input type="text" id="breastSearch" placeholder="搜尋藥物名稱 ..." autocomplete="off">
                <button class="btn btn-primary" onclick="filterBreast()">搜尋</button>
                <button class="btn btn-outline" onclick="resetBreastFilters()">重置</button>
            </div>
            <div class="filter-group">
                <label>疾病分期</label>
                <div class="filter-chip" data-f="stage" data-v="early" onclick="toggleChip(this)">eBC 早期乳癌（Stage I-II）</div>
                <div class="filter-chip" data-f="stage" data-v="advanced" onclick="toggleChip(this)">LABC 局部晚期（Stage III）</div>
                <div class="filter-chip" data-f="stage" data-v="metastatic" onclick="toggleChip(this)">mBC 轉移性乳癌（Stage IV）</div>
            </div>
            <div class="filter-group">
                <label>受體狀態（ER / PR / HER2）</label>
                <div class="filter-chip" data-f="er_pr" data-v="positive" onclick="toggleChip(this)">ER/PR 陽性</div>
                <div class="filter-chip" data-f="er_pr" data-v="negative" onclick="toggleChip(this)">ER/PR 陰性</div>
                <div class="filter-chip" data-f="her2" data-v="positive" onclick="toggleChip(this)">HER2 陽性（IHC3+/FISH+）</div>
                <div class="filter-chip" data-f="her2" data-v="negative" onclick="toggleChip(this)">HER2 陰性</div>
                <span id="tnbcBadge" style="display:none;background:#dc3545;color:#fff;padding:0.25rem 0.75rem;border-radius:1rem;font-size:0.85rem;font-weight:600;margin-left:0.5rem;vertical-align:middle">TNBC 三陰性乳癌</span>
            </div>
            <div class="filter-group">
                <label>特殊條件</label>
                <div class="filter-chip" data-f="ln" data-v="true" onclick="toggleChip(this)">淋巴結轉移</div>
                <div class="filter-chip" data-f="tnbc" data-v="true" onclick="toggleChip(this)">TNBC 三陰性</div>
                <div class="filter-chip" data-f="brca" data-v="true" onclick="toggleChip(this)">BRCA 突變</div>
                <div class="filter-chip" data-f="esr1" data-v="true" onclick="toggleChip(this)">ESR1 突變</div>
                <div class="filter-chip" data-f="pik3ca" data-v="true" onclick="toggleChip(this)">PIK3CA 突變</div>
                <div class="filter-chip" data-f="menopause" data-v="pre" onclick="toggleChip(this)">停經前</div>
                <div class="filter-chip" data-f="menopause" data-v="post" onclick="toggleChip(this)">停經後</div>
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
        </div><!-- end tabDrugsContent -->

        <div class="tab-content" id="tabRegimenContent">
            <div id="regimenApp"></div>
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

// ── Offline Cache ──
let _offlineMode = false;
async function cachedFetch(url, opts){
    const key = 'nhi_cache_' + url;
    try {
        const r = await fetch(url, opts);
        if(r.ok && (!opts || !opts.method || opts.method==='GET')){
            const data = await r.json();
            try{ localStorage.setItem(key, JSON.stringify(data)); }catch(e){}
            return {ok:true, json:()=>Promise.resolve(data)};
        }
        return r;
    } catch(e) {
        // Offline fallback
        const cached = localStorage.getItem(key);
        if(cached){
            if(!_offlineMode){
                _offlineMode = true;
                const bar=document.getElementById('offlineBar');
                if(bar) bar.style.display='block';
            }
            return {ok:true, json:()=>Promise.resolve(JSON.parse(cached))};
        }
        throw e;
    }
}

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
    // Pre-cache all data for offline use
    cachedFetch('/api/stats');
    cachedFetch('/api/drugs?specialty=oncology_breast');
    cachedFetch('/api/drugs?specialty=oncology_heme');
    cachedFetch('/api/formulations');
});

// ── Landing ──
async function loadLanding(){
    const r=await cachedFetch('/api/stats'); const d=await r.json();
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
    switchBreastTab('drugs');
}
function switchBreastTab(tab){
    document.querySelectorAll('#breastPage .inner-tab').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('#breastPage .tab-content').forEach(c=>c.classList.remove('active'));
    if(tab==='drugs'){
        document.getElementById('tabDrugs').classList.add('active');
        document.getElementById('tabDrugsContent').classList.add('active');
        if(!breastDrugs.length){
            cachedFetch('/api/drugs?category=oncology_breast').then(r=>r.json()).then(d=>{breastDrugs=d;renderBreast(breastDrugs)});
        }
    } else {
        document.getElementById('tabRegimen').classList.add('active');
        document.getElementById('tabRegimenContent').classList.add('active');
        if(!_regimenInited) initRegimenCalc();
    }
}
async function showHeme(){
    document.getElementById('landingPage').style.display='none';
    document.getElementById('hemePage').classList.add('active');
    document.getElementById('breastPage').classList.remove('active');
    activeFilters={};
    const r=await cachedFetch('/api/drugs?category=oncology_heme'); hemeDrugs=await r.json();
    renderHeme(hemeDrugs);
}

// ── Filters ──
function toggleChip(el){
    el.classList.toggle('active');
    const f=el.dataset.f, v=el.dataset.v;
    if(el.classList.contains('active')){activeFilters[f]=v}
    else{delete activeFilters[f]}
    // TNBC auto-detection
    const tnbc=document.getElementById('tnbcBadge');
    if(tnbc){
        if(activeFilters.er_pr==='negative' && activeFilters.her2==='negative'){
            tnbc.style.display='inline-block';
        } else {
            tnbc.style.display='none';
        }
    }
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
    if(!s)return'<span style="color:var(--muted)">*待確認</span>';
    const m={'early':'eBC(I-II)','advanced':'LABC(III)','metastatic':'mBC(IV)'};
    return s.split(',').map(x=>m[x]||x).join('、');
}
function lineLabel(n){
    if(!n) return '-';
    if(n<=2) return '<span class="badge" style="background:#d1fae5;color:#065f46">第'+n+'線</span>';
    return '<span class="badge" style="background:#fef3c7;color:#92400e">第'+n+'線</span>';
}

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

// ── Drug Interactions ──
const DRUG_INTERACTIONS = {
  'Tamoxifen':{
    interactions:[
      {drug:'Paroxetine / Fluoxetine (CYP2D6 強效抑制劑)',severity:'high',desc:'CYP2D6 抑制劑會降低 Tamoxifen 轉化為活性代謝物 Endoxifen，顯著降低療效。應避免併用，改用 Venlafaxine 或 Escitalopram。'},
      {drug:'Warfarin',severity:'moderate',desc:'Tamoxifen 可能增強 Warfarin 抗凝效果，需密切監測 INR。'},
      {drug:'Letrozole / Anastrozole',severity:'high',desc:'不建議與 AI 類藥物同時使用，會相互抵消作用。'}
    ]
  },
  'Capecitabine':{
    interactions:[
      {drug:'Warfarin',severity:'high',desc:'Capecitabine 顯著增強 Warfarin 抗凝作用，可能導致致命性出血。需密切監測 INR 或改用 LMWH。'},
      {drug:'Phenytoin',severity:'moderate',desc:'可能增加 Phenytoin 血中濃度，需監測藥物濃度。'},
      {drug:'Allopurinol',severity:'moderate',desc:'可能降低 Capecitabine 活性，應避免併用。'}
    ]
  },
  'Palbociclib':{
    interactions:[
      {drug:'CYP3A4 強效抑制劑 (Ketoconazole, Itraconazole)',severity:'high',desc:'顯著增加 Palbociclib 血中濃度。若需併用，Palbociclib 應減量至 75mg。'},
      {drug:'CYP3A4 強效誘導劑 (Rifampin, Phenytoin)',severity:'high',desc:'顯著降低 Palbociclib 血中濃度，應避免併用。'},
      {drug:'PPI / H2 blocker',severity:'moderate',desc:'胃酸抑制劑可能降低吸收，建議與食物同服。'}
    ]
  },
  'Ribociclib':{
    interactions:[
      {drug:'QTc 延長藥物 (Ondansetron, Azithromycin)',severity:'high',desc:'Ribociclib 本身可延長 QTc，與其他 QTc 延長藥物併用風險增加。需定期監測心電圖。'},
      {drug:'CYP3A4 強效抑制劑',severity:'high',desc:'顯著增加血中濃度，需減量。'},
      {drug:'CYP3A4 強效誘導劑',severity:'high',desc:'顯著降低血中濃度，應避免併用。'}
    ]
  },
  'Abemaciclib':{
    interactions:[
      {drug:'CYP3A4 強效抑制劑 (Ketoconazole)',severity:'high',desc:'增加血中濃度，需減量至 100mg BID。'},
      {drug:'CYP3A4 強效誘導劑',severity:'high',desc:'降低血中濃度，應避免併用。'}
    ]
  },
  'Lapatinib':{
    interactions:[
      {drug:'CYP3A4 抑制劑 / 誘導劑',severity:'high',desc:'CYP3A4 抑制劑增加暴露量；誘導劑降低療效。需調整劑量。'},
      {drug:'PPI / H2 blocker',severity:'moderate',desc:'減少 Lapatinib 溶解度與吸收，應避免併用。'},
      {drug:'葡萄柚汁',severity:'moderate',desc:'CYP3A4 抑制，增加 Lapatinib 暴露量。'}
    ]
  },
  'Olaparib':{
    interactions:[
      {drug:'CYP3A4 強效抑制劑',severity:'high',desc:'增加 Olaparib 暴露量，需減量至 150mg BID。'},
      {drug:'CYP3A4 強效誘導劑',severity:'high',desc:'顯著降低療效，應避免併用。'}
    ]
  },
  'Docetaxel':{
    interactions:[
      {drug:'CYP3A4 抑制劑 (Ketoconazole, Erythromycin)',severity:'moderate',desc:'可能增加 Docetaxel 暴露量及毒性，需密切監測。'},
      {drug:'Platinum compounds',severity:'low',desc:'先給予 Docetaxel 再給 Cisplatin/Carboplatin 可降低骨髓抑制。'}
    ]
  },
  'Paclitaxel':{
    interactions:[
      {drug:'Cisplatin',severity:'moderate',desc:'先給 Paclitaxel 再給 Cisplatin，順序影響骨髓毒性程度。'},
      {drug:'CYP2C8 / CYP3A4 抑制劑',severity:'moderate',desc:'可能增加 Paclitaxel 暴露量。'}
    ]
  },
  'Letrozole':{
    interactions:[
      {drug:'Tamoxifen',severity:'high',desc:'不應同時併用，會降低 Letrozole 血中濃度。'},
      {drug:'CYP2A6 / CYP3A4 強效抑制劑',severity:'moderate',desc:'可能影響 Letrozole 代謝。'}
    ]
  },
  'Everolimus':{
    interactions:[
      {drug:'CYP3A4 / P-gp 強效抑制劑',severity:'high',desc:'顯著增加暴露量。若需併用，Everolimus 減量至 2.5mg/day。'},
      {drug:'CYP3A4 強效誘導劑',severity:'high',desc:'顯著降低暴露量，應避免併用或加倍劑量。'},
      {drug:'活疫苗',severity:'high',desc:'免疫抑制狀態下禁止接種活疫苗。'}
    ]
  },
  'Pembrolizumab':{
    interactions:[
      {drug:'全身性類固醇 (>10mg Prednisone/day)',severity:'moderate',desc:'高劑量類固醇可能降低免疫治療效果。若可能，應在開始 Pembrolizumab 前停用。'},
      {drug:'免疫抑制劑',severity:'moderate',desc:'可能降低免疫治療效果，應盡量避免。'}
    ]
  }
};

// ── Side Effects ──
const SIDE_EFFECTS = {
  'Epirubicin':{common:['噁心/嘔吐','骨髓抑制(白血球低下)','落髮','口腔黏膜炎'],serious:['心臟毒性(累積劑量>900mg/m²)','嚴重嗜中性白血球低下併發燒'],management:'監測LVEF(每3個月)。累積劑量需記錄。使用止吐藥預防。'},
  'Cyclophosphamide':{common:['噁心/嘔吐','骨髓抑制','落髮','出血性膀胱炎'],serious:['嚴重骨髓抑制','出血性膀胱炎'],management:'充足水分攝取。高劑量時需使用 Mesna 預防膀胱炎。'},
  'Docetaxel':{common:['骨髓抑制','落髮','水腫/體液滯留','周邊神經病變','甲床變化'],serious:['嚴重嗜中性白血球低下','過敏反應'],management:'需前給藥 Dexamethasone 預防水腫及過敏。監測周邊神經症狀。GCSF 預防嗜中性低下。'},
  'Paclitaxel':{common:['骨髓抑制','周邊神經病變','關節痛/肌肉痛','落髮','過敏反應'],serious:['嚴重過敏/呼吸困難','嚴重周邊神經病變'],management:'需前給藥(Dexamethasone+Diphenhydramine+Famotidine)。監測神經症狀，Grade 2 以上考慮減量。'},
  'Carboplatin':{common:['骨髓抑制(血小板低下為主)','噁心/嘔吐','腎功能異常','疲倦'],serious:['嚴重血小板低下','過敏反應(重複暴露後)'],management:'依 GFR 調整劑量(Calvert formula)。監測 CBC、腎功能。重複療程注意過敏反應。'},
  'Capecitabine':{common:['手足症候群','腹瀉','噁心','口腔黏膜炎','疲倦'],serious:['嚴重手足症候群','嚴重腹瀉脫水','DPD缺乏致命毒性'],management:'手足症候群：使用潤膚膏、避免壓力。Grade 2 停藥至恢復後減量。監測腹瀉。DPD 基因檢測建議。'},
  'Trastuzumab':{common:['輸注反應(寒顫/發燒)','疲倦','腹瀉','頭痛'],serious:['心臟毒性(LVEF下降)','嚴重輸注反應'],management:'每3個月監測 LVEF。LVEF<45% 暫停治療。首次輸注速度緩慢。避免與 Anthracycline 同時使用。'},
  'Pertuzumab':{common:['腹瀉','落髮','噁心','疲倦','皮疹'],serious:['心臟毒性(與Trastuzumab加乘)','嚴重腹瀉'],management:'與 Trastuzumab 合用時加強 LVEF 監測。腹瀉嚴重時給予 Loperamide。'},
  'Trastuzumab emtansine':{common:['疲倦','噁心','肌肉骨骼疼痛','血小板低下','肝功能異常'],serious:['肝毒性','血小板低下出血','心臟毒性','間質性肺炎'],management:'每次給藥前監測血小板及肝功能。血小板<50000 延遲治療。監測 LVEF。'},
  'Sacituzumab govitecan':{common:['嗜中性白血球低下','腹瀉','噁心/嘔吐','落髮','疲倦'],serious:['嚴重嗜中性低下','嚴重腹瀉'],management:'考慮預防性 GCSF。腹瀉時早期使用 Loperamide+Atropine。UGT1A1*28 基因型影響毒性。'},
  'Palbociclib':{common:['嗜中性白血球低下','疲倦','噁心','口腔黏膜炎','落髮','腹瀉'],serious:['嚴重嗜中性低下(Grade 3/4 常見)','肺栓塞'],management:'每月監測 CBC（前6個月每2週）。Grade 3 嗜中性低下：暫停至恢復>1000再減量。與食物同服增加吸收。'},
  'Ribociclib':{common:['嗜中性白血球低下','噁心','疲倦','腹瀉','肝功能異常'],serious:['QTc 延長','嚴重肝毒性','嗜中性低下'],management:'前2個月每2週監測 CBC、肝功能、心電圖。QTc>500ms 停藥。避免併用 QTc 延長藥物。'},
  'Abemaciclib':{common:['腹瀉(最常見,>80%)','嗜中性低下','噁心','疲倦','腹痛'],serious:['嚴重腹瀉脫水','肝毒性','靜脈血栓','間質性肺炎'],management:'第一次腹瀉立即開始 Loperamide。Grade 2 腹瀉持續>24hr 考慮減量。每月監測 CBC 及肝功能。'},
  'Tamoxifen':{common:['熱潮紅','陰道分泌物','月經不規則','疲倦'],serious:['子宮內膜癌(長期使用)','靜脈血栓/肺栓塞','中風'],management:'定期婦科檢查(每年子宮超音波)。有異常出血立即就醫。有血栓史者考慮改用 AI。'},
  'Letrozole':{common:['關節痛/肌肉痛','熱潮紅','骨質疏鬆','疲倦','膽固醇升高'],serious:['骨折(骨密度下降)','心血管事件'],management:'定期骨密度檢測(DEXA)。補充鈣+維他命D。關節痛可用運動/物理治療緩解。監測血脂。'},
  'Exemestane':{common:['關節痛','熱潮紅','疲倦','多汗','失眠'],serious:['骨質疏鬆/骨折'],management:'同 Letrozole：骨密度監測、鈣+維D補充。'},
  'Fulvestrant':{common:['注射部位疼痛','噁心','骨骼疼痛','熱潮紅','疲倦'],serious:['肝功能異常','血栓事件'],management:'注射速度緩慢(1-2分鐘/邊)，兩側臀部各一針。監測肝功能。'},
  'Olaparib':{common:['噁心','疲倦','貧血','嘔吐','腹瀉'],serious:['骨髓增生不良症候群(MDS)/急性骨髓性白血病(AML)','嚴重貧血'],management:'每月監測 CBC。貧血需排除 MDS/AML。噁心可用止吐藥預防。避免與 CYP3A4 抑制劑併用。'},
  'Pembrolizumab':{common:['疲倦','皮疹/搔癢','腹瀉','關節痛'],serious:['免疫相關副作用：肺炎/肝炎/腸炎/內分泌疾病/皮膚毒性','心肌炎'],management:'每次治療前監測甲狀腺功能、肝功能。教育病人辨識免疫副作用症狀。Grade 2 以上給予類固醇。'},
  'Everolimus':{common:['口腔潰瘍/口腔炎','皮疹','疲倦','腹瀉','食慾下降'],serious:['間質性肺炎','嚴重感染','高血糖'],management:'預防性使用 Dexamethasone 漱口水。監測空腹血糖、血脂、CBC。出現咳嗽/呼吸困難需排除肺炎。'},
  'Enhertu':{common:['噁心/嘔吐','疲倦','落髮','白血球低下','便秘'],serious:['間質性肺疾病(ILD，致命風險)','嗜中性低下'],management:'每次治療前評估肺部症狀。出現咳嗽/呼吸困難立即胸部CT。Grade 1 ILD 停藥觀察；Grade 2+ 永久停藥。'},
  'Lapatinib':{common:['腹瀉','手足症候群','皮疹','噁心','疲倦'],serious:['肝毒性','QTc延長','間質性肺炎'],management:'監測肝功能（治療前及每4-6週）。空腹服用。腹瀉管理同其他標靶藥。'},
  'Vinorelbine':{common:['骨髓抑制','便秘','噁心','注射部位刺激','周邊神經病變'],serious:['嚴重嗜中性低下','嚴重便秘/腸阻塞'],management:'靜脈注射需確認管路通暢，避免外漏。預防便秘。監測 CBC。'},
  'Doxorubicin':{common:['噁心/嘔吐','骨髓抑制','落髮','口腔黏膜炎'],serious:['心臟毒性(累積劑量>550mg/m²)','嚴重骨髓抑制'],management:'監測LVEF。記錄累積劑量。Liposomal 劑型心毒性較低。'}
};

// ── Renal Dose Adjustments ──
const RENAL_ADJUSTMENTS = {
  'Carboplatin':{method:'calvert',note:'使用 Calvert formula: Dose(mg) = AUC × (GFR + 25)。GFR 以實測或估算值計算。'},
  'Capecitabine':{
    adjustments:[
      {gfr_min:51,gfr_max:999,pct:100,note:'正常劑量'},
      {gfr_min:30,gfr_max:50,pct:75,note:'減量至75%'},
      {gfr_min:0,gfr_max:29,pct:0,note:'禁用 (CrCl < 30)'}
    ],
    note:'CrCl 30-50 mL/min：起始劑量減至 75%。CrCl < 30：禁忌使用。'
  },
  'Cisplatin':{
    adjustments:[
      {gfr_min:60,gfr_max:999,pct:100,note:'正常劑量'},
      {gfr_min:46,gfr_max:59,pct:75,note:'減量至75%'},
      {gfr_min:31,gfr_max:45,pct:50,note:'減量至50%'},
      {gfr_min:0,gfr_max:30,pct:0,note:'禁用'}
    ],
    note:'腎毒性高，需充分水化。CrCl < 60 考慮改用 Carboplatin。'
  },
  'Methotrexate':{
    adjustments:[
      {gfr_min:61,gfr_max:999,pct:100,note:'正常劑量'},
      {gfr_min:31,gfr_max:60,pct:50,note:'減量至50%'},
      {gfr_min:0,gfr_max:30,pct:0,note:'禁用'}
    ],
    note:'腎功能不全時排除延遲，毒性顯著增加。需監測藥物濃度。'
  },
  'Olaparib':{
    adjustments:[
      {gfr_min:51,gfr_max:999,pct:100,note:'正常劑量 (300mg BID)'},
      {gfr_min:31,gfr_max:50,pct:67,note:'減量至 200mg BID'},
      {gfr_min:0,gfr_max:30,pct:0,note:'不建議使用（資料不足）'}
    ],
    note:'CrCl 31-50：減量至 200mg BID。CrCl < 30：不建議。'
  },
  'Pemetrexed':{
    adjustments:[
      {gfr_min:45,gfr_max:999,pct:100,note:'正常劑量'},
      {gfr_min:0,gfr_max:44,pct:0,note:'不建議使用'}
    ],
    note:'CrCl < 45 mL/min 不建議使用。'
  },
  'Etoposide':{
    adjustments:[
      {gfr_min:51,gfr_max:999,pct:100,note:'正常劑量'},
      {gfr_min:16,gfr_max:50,pct:75,note:'減量至75%'},
      {gfr_min:0,gfr_max:15,pct:50,note:'減量至50%'}
    ],
    note:'腎功能不全時需減量，密切監測骨髓抑制。'
  }
};

// ── Detail ──
async function showDetail(id){
    const r=await cachedFetch('/api/drug/'+id);const d=await r.json();
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
    // Side effects card
    const drugName = d.generic_name || d.trade_names || '';
    const seKey = Object.keys(SIDE_EFFECTS).find(k=>drugName.toLowerCase().includes(k.toLowerCase())||k.toLowerCase().includes(drugName.toLowerCase()));
    if(seKey){
        const se=SIDE_EFFECTS[seKey];
        h+=`<div class="detail-sec"><h3>副作用速查</h3>
            <div style="display:grid;gap:0.5rem">
                <div><strong>常見副作用：</strong><span style="color:#666">${se.common.join('、')}</span></div>
                <div><strong style="color:#dc3545">嚴重副作用：</strong><span style="color:#dc3545">${se.serious.join('、')}</span></div>
                <div style="background:#f0fdf4;padding:0.5rem 0.75rem;border-radius:0.5rem;border-left:3px solid #22c55e"><strong>處置建議：</strong>${se.management}</div>
            </div>
        </div>`;
    }
    // Drug interactions
    const iaKey = Object.keys(DRUG_INTERACTIONS).find(k=>drugName.toLowerCase().includes(k.toLowerCase())||k.toLowerCase().includes(drugName.toLowerCase()));
    if(iaKey){
        const ia=DRUG_INTERACTIONS[iaKey];
        let iaHtml='';
        ia.interactions.forEach(i=>{
            const sev=i.severity==='high'?'background:#fef2f2;border-left:3px solid #dc3545;':'background:#fffbeb;border-left:3px solid #f59e0b;';
            const sevLabel=i.severity==='high'?'<span style="color:#dc3545;font-weight:700">高風險</span>':'<span style="color:#f59e0b;font-weight:700">中風險</span>';
            iaHtml+=`<div style="${sev}padding:0.5rem 0.75rem;border-radius:0.5rem;margin-bottom:0.4rem">
                <div style="display:flex;justify-content:space-between;align-items:center"><strong>${i.drug}</strong>${sevLabel}</div>
                <div style="font-size:0.85rem;color:#555;margin-top:0.2rem">${i.desc}</div>
            </div>`;
        });
        h+=`<div class="detail-sec"><h3>藥物交互作用</h3>${iaHtml}</div>`;
    }
    // Renal dose adjustment
    const raKey = Object.keys(RENAL_ADJUSTMENTS).find(k=>drugName.toLowerCase().includes(k.toLowerCase())||k.toLowerCase().includes(drugName.toLowerCase()));
    if(raKey){
        const ra=RENAL_ADJUSTMENTS[raKey];
        let raHtml=`<div style="background:#eff6ff;padding:0.5rem 0.75rem;border-radius:0.5rem;border-left:3px solid #3b82f6;margin-bottom:0.5rem"><strong>腎功能調整：</strong>${ra.note}</div>`;
        if(ra.adjustments){
            raHtml+='<table style="width:100%;border-collapse:collapse;font-size:0.85rem"><tr style="background:#f1f5f9"><th style="padding:0.4rem;text-align:left">CrCl (mL/min)</th><th style="padding:0.4rem;text-align:center">劑量調整</th><th style="padding:0.4rem;text-align:left">備註</th></tr>';
            ra.adjustments.forEach(a=>{
                const range=a.gfr_max>=999?'≥'+a.gfr_min:a.gfr_min+'-'+a.gfr_max;
                const pctColor=a.pct===100?'#22c55e':a.pct>0?'#f59e0b':'#dc3545';
                raHtml+=`<tr style="border-bottom:1px solid #e2e8f0"><td style="padding:0.4rem">${range}</td><td style="padding:0.4rem;text-align:center;font-weight:600;color:${pctColor}">${a.pct>0?a.pct+'%':'禁用'}</td><td style="padding:0.4rem;color:#666">${a.note}</td></tr>`;
            });
            raHtml+='</table>';
        }
        h+=`<div class="detail-sec"><h3>腎功能劑量調整</h3>${raHtml}</div>`;
    }
    // Cost calculator — combo takes priority for HP dual-blockade drugs
    const combo = getComboForDrug(d.generic_name, d.trade_names);
    if(combo){
        h+=buildComboCalc(combo, d.generic_name);
    } else if(d.nhi_price && dosage){
        h+=buildCostCalc(d, dosage);
    }
    const infoUrl = d.drug_image_url ||
        `https://www.nhi.gov.tw/QueryPharmacy/Drug_List.aspx?n1=${encodeURIComponent(d.trade_names||d.generic_name)}`;
    h+=`<div class="btn-row">
        <button class="btn btn-outline btn-sm" onclick="closeDetail();openEditDrug(${d.id})">編輯此藥物</button>
        <a class="btn btn-outline btn-sm" href="${infoUrl}" target="_blank" rel="noopener noreferrer"
           style="text-decoration:none;display:inline-flex;align-items:center;gap:.3rem">
           查看藥品說明書 ↗
        </a>
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
    const r=await cachedFetch('/api/drug/'+id);const d=await r.json();
    document.getElementById('editBody').innerHTML=`
        <h2>編輯藥物</h2>
        <div class="edit-form">
            <div class="form-row"><label>藥物名稱</label><input id="eN" value="${esc(d.generic_name)}"></div>
            <div class="form-row"><label>商品名</label><input id="eT" value="${esc(d.trade_names||'')}"></div>
            <div class="form-row"><label>分類</label><select id="eS">
                <option value="oncology_breast" ${d.specialty_id==='oncology_breast'?'selected':''}>乳癌</option>
                <option value="oncology_heme" ${d.specialty_id==='oncology_heme'?'selected':''}>血液腫瘤</option>
                <option value="oncology_other" ${d.specialty_id==='oncology_other'?'selected':''}>其他腫瘤</option>
            </select></div>
            <div class="form-row"><label>疾病分期</label><select id="eStage">
                <option value="" ${!d.stage?'selected':''}>未指定</option>
                <option value="early" ${d.stage==='early'?'selected':''}>eBC 早期 (Stage I-II)</option>
                <option value="advanced" ${d.stage==='advanced'?'selected':''}>LABC 局部晚期 (Stage III)</option>
                <option value="metastatic" ${d.stage==='metastatic'?'selected':''}>mBC 轉移性 (Stage IV)</option>
                <option value="early,advanced" ${d.stage==='early,advanced'?'selected':''}>早期+局部晚期</option>
                <option value="early,metastatic" ${d.stage==='early,metastatic'?'selected':''}>早期+轉移性</option>
                <option value="early,metastatic,advanced" ${d.stage==='early,metastatic,advanced'?'selected':''}>全分期</option>
                <option value="metastatic,advanced" ${d.stage==='metastatic,advanced'?'selected':''}>晚期+轉移性</option>
            </select></div>
            <div class="form-row"><label>療程線</label><select id="eLine">
                <option value="" ${!d.therapy_line?'selected':''}>未指定</option>
                <option value="1" ${d.therapy_line==1?'selected':''}>第1線</option>
                <option value="2" ${d.therapy_line==2?'selected':''}>第2線</option>
                <option value="3" ${d.therapy_line==3?'selected':''}>第3線</option>
                <option value="4" ${d.therapy_line==4?'selected':''}>第4線</option>
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
        stage:document.getElementById('eStage').value,
        therapy_line:document.getElementById('eLine').value||null,
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
                <option value="oncology_other">其他腫瘤</option>
            </select></div>
            <div class="form-row"><label>疾病分期</label><select id="eStage">
                <option value="">未指定</option>
                <option value="early">eBC 早期 (Stage I-II)</option>
                <option value="advanced">LABC 局部晚期 (Stage III)</option>
                <option value="metastatic">mBC 轉移性 (Stage IV)</option>
                <option value="early,advanced">早期+局部晚期</option>
                <option value="early,metastatic">早期+轉移性</option>
                <option value="early,metastatic,advanced">全分期</option>
                <option value="metastatic,advanced">晚期+轉移性</option>
            </select></div>
            <div class="form-row"><label>療程線</label><select id="eLine">
                <option value="">未指定</option>
                <option value="1">第1線</option>
                <option value="2">第2線</option>
                <option value="3">第3線</option>
                <option value="4">第4線</option>
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
        stage:document.getElementById('eStage').value,
        therapy_line:document.getElementById('eLine').value||null,
        indication:document.getElementById('eI').value,
        conditions:document.getElementById('eC').value,
    };
    if(!body.generic_name){alert('請輸入藥物名稱');return}
    await fetch('/api/drugs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    closeEdit();alert('已新增');loadLanding();
}
// ── Manage Tools ──
function openManageTools(){
    document.getElementById('editBody').innerHTML=`
        <h2>管理工具</h2>
        <div class="edit-form">
            <div style="display:grid;gap:0.75rem">
                <button class="btn btn-outline" onclick="closeEdit();openAddDrug()">新增藥物</button>
                <button class="btn btn-outline" onclick="closeEdit();exportDrugList()">匯出藥物清單</button>
                <button class="btn btn-outline" onclick="closeEdit();showDownloads()">資料來源下載</button>
            </div>
            <div class="btn-row" style="margin-top:1rem">
                <button class="btn btn-outline btn-sm" onclick="closeEdit()">關閉</button>
            </div>
        </div>`;
    document.getElementById('editModal').classList.add('show');
}
async function exportDrugList(){
    const r=await cachedFetch('/api/drugs');const drugs=await r.json();
    let csv='藥物名稱,商品名,分類,分期,適應症\\n';
    drugs.forEach(d=>{csv+='"'+d.generic_name+'","'+(d.trade_names||'')+'","'+d.specialty_id+'","'+(d.stage||'')+'","'+(d.indication||'').replace(/"/g,'""')+'"\\n'});
    const blob=new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='NHI_drug_list.csv';a.click();
}
function showDownloads(){
    document.getElementById('editBody').innerHTML=`
        <h2>資料來源與下載</h2>
        <div class="edit-form" style="font-size:0.95rem">
            <p style="color:#666;margin-bottom:1rem">以下為本系統使用之原始資料，供使用者核對參考：</p>
            <table style="width:100%;border-collapse:collapse">
                <tr style="border-bottom:1px solid #eee"><td style="padding:0.5rem"><strong>健保藥品給付規定</strong></td>
                    <td style="padding:0.5rem;color:#666">115/03/23 版本</td></tr>
                <tr style="border-bottom:1px solid #eee"><td style="padding:0.5rem"><strong>健保藥價</strong></td>
                    <td style="padding:0.5rem;color:#666">115 年藥品支付價格（115/04/01 生效）</td></tr>
                <tr style="border-bottom:1px solid #eee"><td style="padding:0.5rem"><strong>台大醫院藥價</strong></td>
                    <td style="padding:0.5rem;color:#666">2024/12/05 更新，66 品項</td></tr>
                <tr style="border-bottom:1px solid #eee"><td style="padding:0.5rem"><strong>SQLite 資料庫</strong></td>
                    <td style="padding:0.5rem"><code>nhi_drug_coverage.db</code></td></tr>
                <tr><td style="padding:0.5rem"><strong>台大藥價原始檔</strong></td>
                    <td style="padding:0.5rem"><code>2024_12_5_price.csv</code></td></tr>
            </table>
            <p style="color:#999;margin-top:1rem;font-size:0.85rem">本系統僅供參考，實際給付以健保署公告為準。藥價依健保支付標準，自費藥品市場價格可能不同。</p>
            <div class="btn-row" style="margin-top:1rem">
                <button class="btn btn-outline btn-sm" onclick="closeEdit()">關閉</button>
            </div>
        </div>`;
    document.getElementById('editModal').classList.add('show');
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

// ══════════════════════════════════════════════════════
// ── Regimen Calculator ──
// ══════════════════════════════════════════════════════
let _regimenInited = false;
let _formulations = {};   // drug_key → [{dose_mg, nhi_price, ntuh_price, ...}]
let _selectedRegimen = null;
let _patientWt = 60, _patientHt = 165, _patientBSA = 1.66;
let _regimenNHI = {};     // drug_key → true/false
let _regimenAddOns = {};  // addon_key → true/false
let _patientConditions = {};  // her2, hr, ln

const REGIMENS = [
  {
    id:'ec_thp', name:'EC → THP → HP', tags:['HER2+','early'],
    desc:'HER2+ 早期乳癌術前/術後輔助化療（標準18週期）',
    phases:[
      {name:'EC Phase', freq:'q3w', cycles:4, drugs:[
        {key:'epirubicin', name:'Epirubicin', dose_type:'bsa', dose:90, unit:'mg/m²'},
        {key:'cyclophosphamide', name:'Cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
      ]},
      {name:'THP Phase', freq:'q3w', cycles:4, drugs:[
        {key:'docetaxel', name:'Docetaxel', dose_type:'bsa', dose:75, unit:'mg/m²'},
        {key:'trastuzumab', name:'Herceptin', dose_type:'kg', dose:6, loading:8, unit:'mg/kg'},
        {key:'pertuzumab', name:'Perjeta', dose_type:'fixed', dose:420, loading:840, unit:'mg'}
      ]},
      {name:'HP 維持 Phase', freq:'q3w', cycles:10, drugs:[
        {key:'trastuzumab', name:'Herceptin', dose_type:'kg', dose:6, unit:'mg/kg'},
        {key:'pertuzumab', name:'Perjeta', dose_type:'fixed', dose:420, unit:'mg'}
      ]}
    ],
    nhi_rules:{
      'N+': {epirubicin:true,cyclophosphamide:true,docetaxel:true,trastuzumab:true,pertuzumab:false},
      'N0': {epirubicin:true,cyclophosphamide:true,docetaxel:true,trastuzumab:false,pertuzumab:false}
    }
  },
  {
    id:'tchp', name:'TCHP → HP', tags:['HER2+','early'],
    desc:'Docetaxel + Carboplatin + Herceptin + Perjeta',
    phases:[
      {name:'TCHP Phase', freq:'q3w', cycles:6, drugs:[
        {key:'docetaxel', name:'Docetaxel', dose_type:'bsa', dose:75, unit:'mg/m²'},
        {key:'carboplatin', name:'Carboplatin', dose_type:'auc', dose:6, unit:'AUC'},
        {key:'trastuzumab', name:'Herceptin', dose_type:'kg', dose:6, loading:8, unit:'mg/kg'},
        {key:'pertuzumab', name:'Perjeta', dose_type:'fixed', dose:420, loading:840, unit:'mg'}
      ]},
      {name:'HP 維持 Phase', freq:'q3w', cycles:12, drugs:[
        {key:'trastuzumab', name:'Herceptin', dose_type:'kg', dose:6, unit:'mg/kg'},
        {key:'pertuzumab', name:'Perjeta', dose_type:'fixed', dose:420, unit:'mg'}
      ]}
    ],
    nhi_rules:{
      'N+': {docetaxel:true,carboplatin:true,trastuzumab:true,pertuzumab:false},
      'N0': {docetaxel:true,carboplatin:true,trastuzumab:false,pertuzumab:false}
    }
  },
  {
    id:'ec_t', name:'EC → T', tags:['HER2-','early'],
    desc:'Epirubicin + Cyclophosphamide → Docetaxel',
    phases:[
      {name:'EC Phase', freq:'q3w', cycles:4, drugs:[
        {key:'epirubicin', name:'Epirubicin', dose_type:'bsa', dose:90, unit:'mg/m²'},
        {key:'cyclophosphamide', name:'Cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
      ]},
      {name:'T Phase', freq:'q3w', cycles:4, drugs:[
        {key:'docetaxel', name:'Docetaxel', dose_type:'bsa', dose:75, unit:'mg/m²'}
      ]}
    ],
    nhi_rules:{'default':{epirubicin:true,cyclophosphamide:true,docetaxel:true}}
  },
  {
    id:'tc', name:'TC', tags:['HER2-','early'],
    desc:'Docetaxel + Cyclophosphamide × 4',
    phases:[
      {name:'TC Phase', freq:'q3w', cycles:4, drugs:[
        {key:'docetaxel', name:'Docetaxel', dose_type:'bsa', dose:75, unit:'mg/m²'},
        {key:'cyclophosphamide', name:'Cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
      ]}
    ],
    nhi_rules:{'default':{docetaxel:true,cyclophosphamide:true}}
  },
  {
    id:'ac_wph', name:'AC → wPH', tags:['HER2+','early'],
    desc:'AC × 4 → weekly Paclitaxel + Herceptin × 12 週',
    phases:[
      {name:'AC Phase', freq:'q3w', cycles:4, drugs:[
        {key:'doxorubicin_lipo', name:'Lipo-Dox', dose_type:'bsa', dose:60, unit:'mg/m²'},
        {key:'cyclophosphamide', name:'Cyclophosphamide', dose_type:'bsa', dose:600, unit:'mg/m²'}
      ]},
      {name:'wPH Phase (weekly × 12)', freq:'weekly', cycles:12, drugs:[
        {key:'paclitaxel', name:'Paclitaxel', dose_type:'bsa', dose:80, unit:'mg/m²'},
        {key:'trastuzumab', name:'Herceptin', dose_type:'kg', dose:2, loading:4, unit:'mg/kg'}
      ]}
    ],
    nhi_rules:{
      'N+': {doxorubicin_lipo:true,cyclophosphamide:true,paclitaxel:true,trastuzumab:true},
      'N0': {doxorubicin_lipo:true,cyclophosphamide:true,paclitaxel:true,trastuzumab:false}
    }
  },
  {
    id:'tdm1', name:'T-DM1 (Kadcyla)', tags:['HER2+','metastatic'],
    desc:'Trastuzumab emtansine 3.6mg/kg q3w（第二線）',
    phases:[
      {name:'T-DM1', freq:'q3w', cycles:14, drugs:[
        {key:'trastuzumab_emtansine', name:'Kadcyla', dose_type:'kg', dose:3.6, unit:'mg/kg'}
      ]}
    ],
    nhi_rules:{'default':{trastuzumab_emtansine:true}}
  },
  {
    id:'trodelvy', name:'Trodelvy', tags:['TNBC','metastatic'],
    desc:'Sacituzumab govitecan 10mg/kg d1,8 q3w',
    phases:[
      {name:'Trodelvy', freq:'q3w', cycles:8, admins_per_cycle:2, drugs:[
        {key:'sacituzumab_govitecan', name:'Trodelvy', dose_type:'kg', dose:10, unit:'mg/kg'}
      ]}
    ],
    nhi_rules:{'default':{sacituzumab_govitecan:true}}
  },
  {
    id:'cdk_ai', name:'CDK4/6i + AI', tags:['HR+','HER2-','metastatic'],
    desc:'CDK4/6 抑制劑 + 芳香環酶抑制劑（第一線荷爾蒙治療）',
    phases:[
      {name:'CDK4/6i + AI (28天/cycle)', freq:'q4w', cycles:12, drugs:[
        {key:'palbociclib', name:'Ibrance (Palbociclib)', dose_type:'fixed_oral', dose:125, days:21, unit:'mg/day'},
        {key:'letrozole', name:'Letrozole', dose_type:'fixed_oral', dose:2.5, days:28, unit:'mg/day'}
      ]}
    ],
    nhi_rules:{'default':{palbociclib:true,letrozole:true}}
  },
  {
    id:'xeloda', name:'Xeloda (Capecitabine)', tags:['metastatic'],
    desc:'Capecitabine 1000mg/m² BID d1-14 q3w',
    phases:[
      {name:'Xeloda', freq:'q3w', cycles:8, drugs:[
        {key:'capecitabine', name:'Xeloda', dose_type:'bsa_oral', dose:1000, days:14, freq_daily:2, unit:'mg/m² BID'}
      ]}
    ],
    nhi_rules:{'default':{capecitabine:true}}
  },
  {
    id:'enhertu', name:'Enhertu', tags:['HER2+','metastatic'],
    desc:'Trastuzumab deruxtecan 5.4mg/kg q3w（非健保）',
    phases:[
      {name:'Enhertu', freq:'q3w', cycles:12, drugs:[
        {key:'trastuzumab_deruxtecan', name:'Enhertu', dose_type:'kg', dose:5.4, unit:'mg/kg'}
      ]}
    ],
    nhi_rules:{'default':{trastuzumab_deruxtecan:false}}
  }
];

const ADDONS = [
  {key:'antiemetic_high', name:'高致吐風險止吐（Emend + Aloxi + Dexamethasone）', price:2625, per:'cycle'},
  {key:'antiemetic_mod', name:'中致吐風險止吐（Aloxi + Dexamethasone）', price:822, per:'cycle'},
  {key:'gcsf', name:'GCSF (Pegfilgrastim/Ziextenzo)', price:9685, per:'cycle'},
  {key:'zoladex', name:'卵巢抑制 Zoladex 3.6mg (q4w)', price:3885, per:'month'},
  {key:'ice', name:'化療冷卻帽 + 手套', price:18850, per:'course'},
  {key:'oncotype', name:'Oncotype DX 基因檢測', price:170000, per:'once'}
];

async function initRegimenCalc(){
  _regimenInited = true;
  // Load formulations from DB
  try {
    const r = await cachedFetch('/api/formulations');
    const data = await r.json();
    _formulations = {};
    data.forEach(f => {
      if(!_formulations[f.drug_key]) _formulations[f.drug_key] = [];
      _formulations[f.drug_key].push(f);
    });
  } catch(e){ console.error('Failed to load formulations', e); }

  const app = document.getElementById('regimenApp');
  app.innerHTML = `
    <div class="reg-section">
      <h3>患者資訊</h3>
      <div class="patient-inputs">
        <div class="field"><label>體重 (kg)</label><input type="number" id="regWt" value="60" min="30" max="150" onchange="updatePatient()"></div>
        <div class="field"><label>身高 (cm)</label><input type="number" id="regHt" value="165" min="140" max="200" onchange="updatePatient()"></div>
        <div class="bsa-display" id="regBSA">BSA: 1.66 m²</div>
        <div class="field"><label>GFR (mL/min, for Carboplatin)</label><input type="number" id="regGFR" value="80" min="20" max="150" onchange="updatePatient()"></div>
      </div>
    </div>
    <div class="reg-section">
      <h3>疾病特徵</h3>
      <div class="condition-bar">
        <button class="cond-btn" data-g="her2" data-v="positive" onclick="toggleCond(this)">HER2+</button>
        <button class="cond-btn" data-g="her2" data-v="negative" onclick="toggleCond(this)">HER2-</button>
        <button class="cond-btn" data-g="hr" data-v="positive" onclick="toggleCond(this)">HR+</button>
        <button class="cond-btn" data-g="hr" data-v="negative" onclick="toggleCond(this)">HR-</button>
        <button class="cond-btn" data-g="ln" data-v="positive" onclick="toggleCond(this)">淋巴結轉移 N+</button>
        <button class="cond-btn" data-g="ln" data-v="negative" onclick="toggleCond(this)">淋巴結無轉移 N0</button>
        <button class="cond-btn" data-g="stage" data-v="early" onclick="toggleCond(this)">早期</button>
        <button class="cond-btn" data-g="stage" data-v="metastatic" onclick="toggleCond(this)">轉移性</button>
      </div>
    </div>
    <div class="reg-section">
      <h3>選擇處方</h3>
      <div class="regimen-cards" id="regimenCards"></div>
    </div>
    <div id="regimenDetail"></div>
    <div class="reg-section" id="addonSection" style="display:none">
      <h3>支持性治療（選填）</h3>
      <div id="addonList"></div>
    </div>
    <div id="regimenSummary"></div>
  `;
  renderRegimenCards();
  renderAddOns();
  updatePatient();
}

function updatePatient(){
  _patientWt = parseFloat(document.getElementById('regWt').value)||60;
  _patientHt = parseFloat(document.getElementById('regHt').value)||165;
  _patientBSA = Math.sqrt((_patientHt * _patientWt)/3600);
  document.getElementById('regBSA').textContent = 'BSA: ' + _patientBSA.toFixed(2) + ' m²';
  if(_selectedRegimen) calcRegimen();
}

function toggleCond(el){
  const g = el.dataset.g, v = el.dataset.v;
  // Deactivate siblings in same group
  document.querySelectorAll('.cond-btn[data-g="'+g+'"]').forEach(b=>{
    if(b!==el) b.classList.remove('active');
  });
  el.classList.toggle('active');
  if(el.classList.contains('active')) _patientConditions[g]=v;
  else delete _patientConditions[g];
  renderRegimenCards();
  if(_selectedRegimen) applyNHIRules();
}

function renderRegimenCards(){
  const container = document.getElementById('regimenCards');
  if(!container) return;
  const conds = _patientConditions;
  let html = '';
  REGIMENS.forEach(reg => {
    // Filter by conditions
    let relevant = true;
    if(conds.her2==='positive' && reg.tags.includes('HER2-') && !reg.tags.includes('HER2+')) relevant = false;
    if(conds.her2==='negative' && reg.tags.includes('HER2+') && !reg.tags.includes('HER2-')) relevant = false;
    if(conds.stage==='early' && reg.tags.includes('metastatic') && !reg.tags.includes('early')) relevant = false;
    if(conds.stage==='metastatic' && reg.tags.includes('early') && !reg.tags.includes('metastatic')) relevant = false;
    if(conds.hr==='negative' && reg.tags.includes('HR+') && !reg.tags.includes('HR-')) relevant = false;
    const sel = _selectedRegimen && _selectedRegimen.id===reg.id ? ' selected':'';
    const opacity = relevant ? '' : ' style="opacity:.4"';
    html += `<div class="reg-card${sel}"${opacity} onclick="selectRegimen('${reg.id}')">
      <h4>${reg.name}</h4>
      <div class="reg-desc">${reg.desc}</div>
      <div style="margin-top:.3rem">${reg.tags.map(t=>'<span class="badge badge-tag">'+t+'</span>').join(' ')}</div>
    </div>`;
  });
  container.innerHTML = html;
}

function selectRegimen(id){
  _selectedRegimen = REGIMENS.find(r=>r.id===id);
  if(!_selectedRegimen) return;
  renderRegimenCards();
  applyNHIRules();
  document.getElementById('addonSection').style.display='';
}

function applyNHIRules(){
  if(!_selectedRegimen) return;
  const rules = _selectedRegimen.nhi_rules;
  const ln = _patientConditions.ln;
  let ruleSet;
  if(ln==='positive' && rules['N+']) ruleSet = rules['N+'];
  else if(ln==='negative' && rules['N0']) ruleSet = rules['N0'];
  else ruleSet = rules['default'] || rules['N+'] || Object.values(rules)[0] || {};
  // Apply but allow override
  Object.keys(ruleSet).forEach(k => { _regimenNHI[k] = ruleSet[k]; });
  calcRegimen();
}

function toggleDrugNHI(drugKey){
  _regimenNHI[drugKey] = !_regimenNHI[drugKey];
  calcRegimen();
}

// Vial optimization: find cheapest combo of vials covering required dose
function optimizeVials(doseMg, drugKey, useNHI){
  const forms = (_formulations[drugKey]||[]).filter(f=>f.dose_mg > 0);
  if(forms.length === 0) return {cost:0, combo:[], totalMg:doseMg};
  const priceKey = useNHI ? 'nhi_price' : 'ntuh_price';
  // Only use formulations with the relevant price
  const available = forms.filter(f => f[priceKey] != null && f[priceKey] > 0)
    .map(f => ({dose_mg:f.dose_mg, price:f[priceKey], desc:f.formulation, unit:f.dose_unit}))
    .sort((a,b) => b.dose_mg - a.dose_mg);
  if(available.length === 0){
    // Fallback: use any price
    const fb = forms.filter(f => (f.ntuh_price||f.nhi_price) > 0)
      .map(f => ({dose_mg:f.dose_mg, price:f.ntuh_price||f.nhi_price, desc:f.formulation, unit:f.dose_unit}))
      .sort((a,b) => b.dose_mg - a.dose_mg);
    if(fb.length===0) return {cost:0, combo:[], totalMg:doseMg};
    available.push(...fb);
  }

  let best = {cost:Infinity, combo:[], totalMg:0};
  const large = available[0];
  const small = available.length > 1 ? available[available.length-1] : large;

  const maxLarge = Math.ceil(doseMg / large.dose_mg) + 1;
  for(let nL=0; nL<=maxLarge; nL++){
    const rem = doseMg - nL * large.dose_mg;
    let nS = 0;
    if(rem > 0 && large !== small) nS = Math.ceil(rem / small.dose_mg);
    else if(rem > 0) continue; // only one size available, handled by nL
    const total = nL * large.dose_mg + nS * small.dose_mg;
    if(total < doseMg - 0.01) continue;
    const cost = nL * large.price + nS * small.price;
    if(cost < best.cost){
      best = {cost, totalMg:total, combo:[]};
      if(nL > 0) best.combo.push({count:nL, dose_mg:large.dose_mg, price:large.price, desc:large.desc, unit:large.unit});
      if(nS > 0) best.combo.push({count:nS, dose_mg:small.dose_mg, price:small.price, desc:small.desc, unit:small.unit});
    }
  }
  return best;
}

function calcRegimen(){
  if(!_selectedRegimen) return;
  const reg = _selectedRegimen;
  let detailHtml = '';
  let nhiTotal = 0, selfTotal = 0;
  const gfr = parseFloat(document.getElementById('regGFR')?.value)||80;

  reg.phases.forEach((phase, pi) => {
    let phaseNHI = 0, phaseSelf = 0;
    let drugRows = '';
    const adminsPerCycle = phase.admins_per_cycle || 1;

    phase.drugs.forEach(drug => {
      const isNHI = _regimenNHI[drug.key] !== undefined ? _regimenNHI[drug.key] : true;
      const nhiClass = isNHI ? 'on-nhi' : '';
      const selfClass = isNHI ? '' : 'on-self';

      // Calculate dose per administration
      let doseMg = 0;
      let doseLabel = '';
      if(drug.dose_type === 'bsa'){
        doseMg = drug.dose * _patientBSA;
        doseLabel = drug.dose + drug.unit + ' = ' + Math.round(doseMg) + 'mg';
      } else if(drug.dose_type === 'kg'){
        doseMg = drug.dose * _patientWt;
        doseLabel = drug.dose + drug.unit + ' = ' + Math.round(doseMg) + 'mg';
      } else if(drug.dose_type === 'auc'){
        doseMg = drug.dose * (gfr + 25); // Calvert formula
        doseLabel = 'AUC ' + drug.dose + ' (GFR=' + gfr + ') = ' + Math.round(doseMg) + 'mg';
      } else if(drug.dose_type === 'fixed'){
        doseMg = drug.dose;
        doseLabel = drug.dose + drug.unit;
      } else if(drug.dose_type === 'fixed_oral'){
        // Oral daily drug, dose is per day, calculate total for cycle
        doseMg = drug.dose; // per day
        const daysPerCycle = drug.days || 21;
        doseLabel = drug.dose + drug.unit + ' × ' + daysPerCycle + '天';
      } else if(drug.dose_type === 'bsa_oral'){
        doseMg = drug.dose * _patientBSA;
        const freqD = drug.freq_daily || 1;
        doseLabel = drug.dose + drug.unit + ' = ' + Math.round(doseMg) + 'mg/次 × ' + freqD + '次/天 × ' + (drug.days||14) + '天';
      }

      // Loading dose for first cycle
      let loadingMg = 0;
      if(drug.loading){
        if(drug.dose_type === 'kg') loadingMg = drug.loading * _patientWt;
        else loadingMg = drug.loading;
      }

      // Calculate cost per cycle with vial optimization
      let costPerCycle = 0, vialInfo = '';
      const cycles = phase.cycles;

      if(drug.dose_type === 'fixed_oral'){
        // Oral: tablets per day × days per cycle
        const tabsPerDay = Math.ceil(doseMg / getSmallestFormulation(drug.key));
        const daysPerCycle = drug.days || 21;
        const tabsPerCycle = tabsPerDay * daysPerCycle;
        const tabPrice = getBestTabPrice(drug.key, isNHI);
        costPerCycle = tabsPerCycle * tabPrice;
        const totalTabs = tabsPerCycle * cycles;
        vialInfo = tabsPerDay + ' 顆/天 × ' + daysPerCycle + '天 = ' + tabsPerCycle + ' 顆/cycle';
        const totalCost = costPerCycle * cycles;
        if(isNHI) phaseNHI += totalCost; else phaseSelf += totalCost;
        drugRows += buildDrugRow(drug, doseLabel, vialInfo, costPerCycle, totalCost, cycles, isNHI, nhiClass, selfClass);
        return;
      }
      if(drug.dose_type === 'bsa_oral'){
        // Oral BSA: tablets per dose × freq × days per cycle
        const dosePerAdmin = doseMg;
        const smallest = getSmallestFormulation(drug.key);
        const tabsPerAdmin = Math.ceil(dosePerAdmin / smallest);
        const freqD = drug.freq_daily || 1;
        const daysPerCycle = drug.days || 14;
        const tabsPerCycle = tabsPerAdmin * freqD * daysPerCycle;
        const tabPrice = getBestTabPrice(drug.key, isNHI);
        costPerCycle = tabsPerCycle * tabPrice;
        const totalTabs = tabsPerCycle * cycles;
        vialInfo = tabsPerAdmin + '顆 × ' + freqD + '次/天 × ' + daysPerCycle + '天 = ' + tabsPerCycle + '顆/cycle';
        const totalCost = costPerCycle * cycles;
        if(isNHI) phaseNHI += totalCost; else phaseSelf += totalCost;
        drugRows += buildDrugRow(drug, doseLabel, vialInfo, costPerCycle, totalCost, cycles, isNHI, nhiClass, selfClass);
        return;
      }

      // IV drugs: vial optimization
      if(loadingMg > 0 && cycles >= 1){
        const loadOpt = optimizeVials(loadingMg, drug.key, isNHI);
        const maintOpt = optimizeVials(doseMg, drug.key, isNHI);
        const loadCost = loadOpt.cost * adminsPerCycle;
        const maintCost = maintOpt.cost * adminsPerCycle;
        const totalCost = loadCost + maintCost * (cycles - 1);
        const loadCombo = loadOpt.combo.map(c=>c.count+'×'+c.dose_mg+'mg').join('+');
        const maintCombo = maintOpt.combo.map(c=>c.count+'×'+c.dose_mg+'mg').join('+');
        vialInfo = '首劑(' + loadCombo + ') + 後續(' + maintCombo + ')×' + (cycles-1);
        if(adminsPerCycle > 1) vialInfo += ' [每週期'+adminsPerCycle+'次]';
        costPerCycle = maintCost;
        if(isNHI) phaseNHI += totalCost; else phaseSelf += totalCost;
        drugRows += buildDrugRow(drug, doseLabel, vialInfo, costPerCycle, totalCost, cycles, isNHI, nhiClass, selfClass, loadCost);
      } else {
        const opt = optimizeVials(doseMg, drug.key, isNHI);
        costPerCycle = opt.cost * adminsPerCycle;
        const totalCost = costPerCycle * cycles;
        const combo = opt.combo.map(c=>c.count+'×'+c.dose_mg+'mg').join(' + ');
        vialInfo = combo || '—';
        if(adminsPerCycle > 1) vialInfo += ' [每週期'+adminsPerCycle+'次]';
        if(isNHI) phaseNHI += totalCost; else phaseSelf += totalCost;
        drugRows += buildDrugRow(drug, doseLabel, vialInfo, costPerCycle, totalCost, cycles, isNHI, nhiClass, selfClass);
      }
    });

    nhiTotal += phaseNHI; selfTotal += phaseSelf;
    const cycleDays = phase.freq==='q3w'?21:phase.freq==='q4w'?28:phase.freq==='weekly'?7:21;
    const months = (phase.cycles * cycleDays / 30).toFixed(1);
    detailHtml += `<div class="phase-box">
      <h4><span>${phase.name} (${phase.freq} × ${phase.cycles})</span><span style="font-size:.73rem;color:var(--muted)">~${months} 個月</span></h4>
      ${drugRows}
      <div style="display:flex;justify-content:space-between;font-size:.78rem;font-weight:600;margin-top:.4rem;padding-top:.4rem;border-top:1px dashed var(--border)">
        <span>Phase 小計</span>
        <span>${phaseNHI>0?'<span class="sum-nhi">健保 NT$'+phaseNHI.toLocaleString()+'</span> ':''}${phaseSelf>0?'<span class="sum-self">自費 NT$'+phaseSelf.toLocaleString()+'</span>':''}</span>
      </div>
    </div>`;
  });

  // Add-ons cost
  let addonTotal = 0, addonHtml = '';
  ADDONS.forEach(a => {
    if(!_regimenAddOns[a.key]) return;
    let cost = a.price;
    if(a.per==='cycle'){
      const totalCycles = reg.phases.reduce((s,p)=>s+p.cycles,0);
      cost = a.price * totalCycles;
    } else if(a.per==='month'){
      const totalMonths = reg.phases.reduce((s,p)=>s+p.cycles*(p.freq==='q3w'?21:p.freq==='q4w'?28:7)/30,0);
      cost = a.price * Math.ceil(totalMonths);
    }
    addonTotal += cost;
    addonHtml += `<div class="sum-line"><span>${a.name}</span><span>NT$ ${cost.toLocaleString()}</span></div>`;
  });
  selfTotal += addonTotal;

  const grandTotal = nhiTotal + selfTotal;
  document.getElementById('regimenDetail').innerHTML = detailHtml;
  document.getElementById('regimenSummary').innerHTML = `<div class="reg-summary">
    <div class="sum-line" style="font-weight:700;font-size:.9rem;margin-bottom:.3rem"><span>${reg.name} 療程費用總計</span><span>體重 ${_patientWt}kg / BSA ${_patientBSA.toFixed(2)} m²</span></div>
    ${nhiTotal>0?'<div class="sum-line sum-nhi"><span>健保給付</span><span>NT$ '+nhiTotal.toLocaleString()+'</span></div>':''}
    ${addonHtml?'<div style="border-top:1px dashed #f9a8d4;margin:.3rem 0;padding-top:.3rem;font-size:.78rem;color:var(--muted)">支持性治療：</div>'+addonHtml:''}
    <div class="sum-line sum-total sum-self"><span>患者自費總計</span><span>NT$ ${selfTotal.toLocaleString()}</span></div>
    <div class="sum-line sum-total sum-grand"><span>全療程合計（含健保）</span><span>NT$ ${grandTotal.toLocaleString()}</span></div>
    <div class="sum-note">* 此為依健保支付標準之估算，各醫院實際收費可能不同。藥價來源：115年健保藥價調整（115/04/01生效）、台大醫院藥品價目表（2024/12/05）。含首劑loading dose。藥品搭配以最經濟組合計算。</div>
    <div style="text-align:center;margin-top:0.75rem">
      <button class="btn btn-outline btn-sm" onclick="printRegimen()">列印 / 匯出 PDF</button>
    </div>
  </div>`;
}

function buildDrugRow(drug, doseLabel, vialInfo, costPerCycle, totalCost, cycles, isNHI, nhiClass, selfClass, loadCost){
  return `<div class="drug-row">
    <div class="drug-info">
      <div class="drug-name-r">${drug.name}</div>
      <div class="drug-dose">${doseLabel}</div>
      <div class="vial-combo">${vialInfo}</div>
    </div>
    <div class="nhi-toggle">
      <button class="${nhiClass}" onclick="_regimenNHI['${drug.key}']=true;calcRegimen()">健保</button>
      <button class="${selfClass}" onclick="_regimenNHI['${drug.key}']=false;calcRegimen()">自費</button>
    </div>
    <div class="drug-cost">
      ${loadCost?'<div style="font-size:.7rem;color:var(--muted)">首劑 NT$'+loadCost.toLocaleString()+'</div>':''}
      <div>${cycles}次 = NT$ ${totalCost.toLocaleString()}</div>
    </div>
  </div>`;
}

function printRegimen(){
  const detail = document.getElementById('regimenDetail').innerHTML;
  const summary = document.getElementById('regimenSummary').innerHTML;
  const w = window.open('','_blank','width=800,height=600');
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>療程費用試算</title>
    <style>
      body{font-family:'Noto Sans TC','Microsoft JhengHei',sans-serif;padding:2rem;max-width:700px;margin:0 auto;color:#1e293b;font-size:13px}
      h2{text-align:center;margin-bottom:0.5rem}
      .phase-box{border:1px solid #e2e8f0;border-radius:8px;padding:0.75rem;margin-bottom:0.75rem}
      .phase-box h4{display:flex;justify-content:space-between;margin:0 0 0.5rem}
      .drug-row{display:flex;justify-content:space-between;padding:0.3rem 0;border-bottom:1px solid #f1f5f9;gap:0.5rem}
      .drug-info{flex:1} .drug-name-r{font-weight:600} .drug-dose,.vial-combo{font-size:0.8rem;color:#666}
      .drug-cost{text-align:right;font-weight:600;white-space:nowrap}
      .nhi-toggle{display:none}
      .reg-summary{border:2px solid #7c3aed;border-radius:8px;padding:1rem;margin-top:1rem}
      .sum-line{display:flex;justify-content:space-between;padding:0.2rem 0}
      .sum-nhi{color:#22c55e} .sum-self{color:#dc3545}
      .sum-total{border-top:1px solid #e2e8f0;padding-top:0.3rem;margin-top:0.3rem;font-weight:700}
      .sum-grand{font-size:1.05rem;color:#7c3aed}
      .sum-note{font-size:0.75rem;color:#999;margin-top:0.5rem}
      .print-footer{text-align:center;margin-top:1.5rem;font-size:0.75rem;color:#aaa;border-top:1px solid #eee;padding-top:0.5rem}
      button{display:none}
      @media print{body{padding:0.5rem}}
    </style>
  </head><body>
    <h2>健保腫瘤藥物療程費用試算</h2>
    <div style="text-align:center;color:#666;margin-bottom:1rem">列印日期：${new Date().toLocaleDateString('zh-TW')}</div>
    ${detail}${summary}
    <div class="print-footer">NHI Oncology Drug Calculator — 本資料僅供參考，實際給付以健保署公告為準</div>
  </body></html>`);
  w.document.close();
  setTimeout(()=>w.print(),300);
}

function getSmallestFormulation(drugKey){
  const forms = _formulations[drugKey]||[];
  const valid = forms.filter(f=>f.dose_mg > 0);
  if(valid.length===0) return 1;
  return Math.min(...valid.map(f=>f.dose_mg));
}

function getBestTabPrice(drugKey, useNHI){
  const forms = _formulations[drugKey]||[];
  const pk = useNHI ? 'nhi_price' : 'ntuh_price';
  const valid = forms.filter(f=>f[pk]>0);
  if(valid.length===0){
    const fb = forms.filter(f=>(f.ntuh_price||f.nhi_price)>0);
    return fb.length>0 ? (fb[0].ntuh_price||fb[0].nhi_price) : 0;
  }
  return valid[0][pk];
}

function renderAddOns(){
  const container = document.getElementById('addonList');
  if(!container) return;
  container.innerHTML = ADDONS.map(a => `<div class="add-on-row">
    <input type="checkbox" id="addon_${a.key}" onchange="_regimenAddOns['${a.key}']=this.checked;if(_selectedRegimen)calcRegimen()">
    <label class="add-on-label" for="addon_${a.key}">${a.name}</label>
    <span class="add-on-price">NT$ ${a.price.toLocaleString()} / ${a.per==='cycle'?'每週期':a.per==='month'?'每月':a.per==='once'?'一次':a.per==='course'?'整個療程':a.per}</span>
  </div>`).join('');
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
        elif path == '/api/formulations':
            self._formulations(params)
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

    def _formulations(self, params):
        c = get_db(); cur = c.cursor()
        drug_key = params.get('drug', [''])[0]
        sql = "SELECT * FROM drug_formulations"
        p = []
        if drug_key:
            sql += " WHERE drug_key = ?"
            p.append(drug_key)
        sql += " ORDER BY drug_key, dose_mg DESC"
        cur.execute(sql, p)
        rows = [dict(r) for r in cur.fetchall()]
        c.close()
        self._json(200, rows)

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
            'drug_image_url': r['drug_image_url'] or '',
        })

    def _update_drug(self, drug_id, body):
        c = get_db(); cur = c.cursor()
        cur.execute("UPDATE drugs SET generic_name=?, trade_names=?, specialty_id=?, indication=?, stage=? WHERE id=?",
                    (body['generic_name'], body.get('trade_names', ''), body['specialty_id'], body.get('indication', ''), body.get('stage', ''), drug_id))
        if body.get('conditions') is not None:
            cur.execute("UPDATE coverage_rules SET condition=? WHERE drug_id=?", (body['conditions'], drug_id))
        if body.get('therapy_line') is not None:
            cur.execute("UPDATE coverage_rules SET therapy_line=? WHERE drug_id=?", (body['therapy_line'], drug_id))
        c.commit(); c.close()
        self._json(200, {'ok': True})

    def _add_drug(self, body):
        c = get_db(); cur = c.cursor()
        cur.execute("INSERT INTO drugs (generic_name, trade_names, specialty_id, indication, stage, created_date) VALUES (?,?,?,?,?,?)",
                    (body['generic_name'], body.get('trade_names', ''), body['specialty_id'], body.get('indication', ''), body.get('stage', ''), datetime.now().date()))
        drug_id = cur.lastrowid
        cur.execute("INSERT INTO coverage_rules (drug_id, condition, therapy_line) VALUES (?,?,?)", (drug_id, body.get('conditions', ''), body.get('therapy_line')))
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
    import argparse as _ap
    _p = _ap.ArgumentParser()
    _p.add_argument('--port', type=int, default=8080)
    _a = _p.parse_args()
    host, port = '127.0.0.1', _a.port
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

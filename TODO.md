# TODO — 待下個 Session 執行

> 這份是給下次新 session 接手用的規格書。
> 截至 commit 7ca0218 (v1.9) 的 backlog。

---

## 🎯 主要任務：Dashboard 模式（全景式單頁面）

### 動機
電腦螢幕夠大，使用者一次想看所有結果。
目前 Workspace 是單純資料輸入 → 散落在不同分頁查結果。
要做的：**輸入一次，所有 calculator + AJCC + 健保藥物 + ICD + NCCN + 重大傷病** 一頁顯示。

### 設計

#### 入口
- **方案 A（推薦）**：在 Workspace 頁加切換按鈕「📋 全景模式 / 📑 表單模式」
- **方案 B**：landing 多一張「📊 Dashboard」卡片（第 10 張）

→ 建議方案 A，避免 landing 卡片爆炸。

#### 桌面佈局（≥1200px）

```
┌────────────────────────────────────────────────┐
│  📋 病人 Workspace [全景模式 ▼]                 │
├──────────────┬─────────────────────────────────┤
│ 左側輸入區     │ 右側結果區（CSS Grid 自動排版）   │
│ (固定寬 380px)│                                 │
│              │ ┌AJCC期別┐ ┌CTS5┐ ┌PREDICT─┐  │
│ ── 基本資料 ── │ │ IIA → IA│ │ 3.4 │ │ 5y/10y/15y│  │
│ MRN          │ │ Anatomic│ │ Med │ │ 92/84/75% │  │
│ 年齡         │ │+v9 Prog │ │     │ └──────────┘  │
│ 身高         │ └─────────┘ └─────┘                │
│ 體重         │                                  │
│ Cr           │ ┌NPI──┐ ┌Magee┐ ┌RCB──┐ ┌IHC4─┐│
│              │ │ 3.6 │ │24.1 │ │N/A  │ │-114 │ │
│ ── 腫瘤位置 ── │ │ Mod │ │Inter│ │     │ │ Low │ │
│ 側別 象限     │ └─────┘ └─────┘ └─────┘ └─────┘│
│              │                                  │
│ ── TNM ──    │ ┌Gail─┐ ┌H-score──┐             │
│ T N M       │ │ 5y  │ │  0      │             │
│ Size, Grade  │ │ 1.8%│ │ Negative│             │
│ Nodes (n+)   │ └─────┘ └─────────┘             │
│              │                                  │
│ ── 生物標記 ── │ ┌─重大傷病─┐ ┌─ICD-10─┐         │
│ ER PR HER2   │ │ ✓ 符合   │ │ C50.411│         │
│ Ki67 BRCA    │ │ IIA 期   │ │ 右乳UO │         │
│ PD-L1        │ └──────────┘ └────────┘         │
│              │                                  │
│ ── 治療脈絡 ── │ ┌─NHI 給付符合的藥物─────────────┐│
│ Menopause    │ │ ✓ Tamoxifen   ✓ Letrozole    │ │
│ ECOG         │ │ ✓ Anastrozole ✓ Palbociclib  │ │
│ Phase        │ │ ✗ Olaparib (需 BRCA+)        │ │
│ Prior Tx     │ │ ... (依 Workspace 自動篩選)  │ │
│              │ └────────────────────────────────┘│
│              │                                  │
│              │ ┌─NCCN 治療指引快速連結────────┐  │
│              │ │ 對應 BINV 流程節點：BINV-3   │  │
│              │ │ [→ 開啟流程圖]               │  │
│              │ └─────────────────────────────┘   │
│              │                                  │
│              │ [📋 產生整合摘要] [💾 匯出 JSON]  │
└──────────────┴─────────────────────────────────┘
```

#### 平板（768-1199px）
左輸入區仍固定，但結果區改 2-column grid。

#### 手機（<768px）
垂直堆疊：輸入區在上，結果區在下，每個結果卡片占滿寬度。

### 技術實作要點

#### 1. CSS 佈局
```css
.dashboard-mode .ws-page {
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 1rem;
}
.dashboard-mode .ws-results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: .75rem;
}
@media (max-width: 1199px) {
    .dashboard-mode .ws-page { grid-template-columns: 320px 1fr; }
    .dashboard-mode .ws-results-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
    .dashboard-mode .ws-page { grid-template-columns: 1fr; }
    .dashboard-mode .ws-results-grid { grid-template-columns: 1fr; }
}
```

#### 2. 結果計算
擴充 `refreshWorkspaceDerived()`，把所有 calculator 的計算都跑一次：

```javascript
function refreshDashboardResults(){
    const p = _patient;
    if (!p.T || !p.N || !p.M) {
        document.querySelectorAll('.ws-result-card').forEach(c =>
            c.innerHTML = '<div class="ws-result-empty">需 T/N/M</div>');
        return;
    }
    // AJCC anatomic + v9 prognostic
    renderAjccPanel(p);
    // CTS5
    if (p.size && p.nodes_pos !== '' && p.grade && p.age) renderCTS5Panel(p);
    // PREDICT (if all required fields present)
    if (p.age && p.size && p.er && p.her2) renderPredictPanel(p);
    // NPI, Magee, IHC4, RCB, Gail, H-score
    renderNPIPanel(p);
    renderMageePanel(p);
    renderIHC4Panel(p);
    renderRCBPanel(p);
    renderGailPanel(p);
    // NHI lookup (already in Workspace)
    refreshNHIEligibility();
    // ICD code, 重大傷病
    renderICDPanel(p);
    renderCatastrophicPanel(p);
    // NCCN link
    renderNCCNPanel(p);
}
```

每個 panel 都是純讀取 `_patient`，計算，渲染到指定 div。

#### 3. 結果卡片 component
```javascript
function renderResultCard(id, title, value, subtitle, color){
    return `<div class="ws-result-card" id="result-${id}">
        <div class="result-title">${title}</div>
        <div class="result-value" style="color:${color}">${value}</div>
        <div class="result-subtitle">${subtitle}</div>
    </div>`;
}
```

#### 4. Workspace 結構修改

現有 Workspace HTML：分區塊輸入。
要改：
- 加上 `<div class="ws-results-grid" id="wsResults"></div>` 結果容器
- 加上模式切換按鈕
- `setPatientField()` 觸發 `refreshDashboardResults()` 而非只 `refreshWorkspaceDerived()`

#### 5. 重用既有 calculator 邏輯
**不要重複寫計算邏輯**。直接呼叫已有函式：
- `_predictPI_ERpos`, `_predictPI_ERneg`, `_predictMI`, `_predictBaseCumBC`, `_predictBaseCumOC`
- `_ajcc9Lookup`, `_ajccAnatomic`
- 但 `calcCTS5/PEPI/Magee/...` 直接讀 DOM input — 需要 refactor 或建立 `pure` 版本：

```javascript
// 建議：加 *Pure 版本 (ES module 友善 + Workspace dashboard 用)
function calcCTS5Pure(N, T, G, A){ /* returns score + risk group */ }
function calcNPIPure(size_cm, node_stage, grade){ /* ... */ }
function calcMageePure(ns, size, er, pr, her2cat, ki67){ /* ... */ }
// ... etc
```

然後既有 `calcCTS5()` 變成：
```javascript
function calcCTS5(){
    const result = calcCTS5Pure(+inputs);
    renderCTS5Result(result);
}
```

這順便為 ARCHITECTURE.md Phase 1 模組化打基礎。

#### 6. 重要 UX 細節
- 任何缺資料的 panel 顯示「需 X / Y」而不是錯誤
- Hover 結果卡片顯示完整 citation
- 點結果卡片可跳到對應分頁查詳細
- Print 按鈕產生整合 PDF

### 估計工作量
- HTML / CSS：1.5 小時
- JS（重用 + 新 panels）：2 小時
- Sanity test + dark mode 覆蓋：30 分鐘
- 手機響應式微調：30 分鐘
- **總計：4-5 小時**

### 不要做的事
- ❌ 不要重寫已有 calculator 邏輯（重用 + Pure 版本）
- ❌ 不要動 landing 結構（dashboard 仍走 Workspace 入口）
- ❌ 不要在 dashboard 內 inline 修改病人資料 → 仍走 setPatientField + localStorage
- ❌ 不要把 dashboard 結果存 localStorage（每次根據 _patient 即時算）

---

## 🌗 任務 2：Dark Mode 全面覆蓋

### 現況
基礎 dark mode 已實作（`body.dark` + Ctrl+D toggle）。
但**新加的元素未必有完整 dark 樣式**。

### 待 audit 的元素
- [ ] Issue Report Modal (`.issue-modal`, `.issue-card`, `.issue-info`)
- [ ] Settings panel (`.settings-card`, `.settings-mode`, `.settings-section.beta`)
- [ ] AJCC v9 lookup result panel
- [ ] PREDICT v1.8 success banner（`#f0fdf4` 在 dark mode 看起來怪）
- [ ] All 9 Calculator panels (PREDICT/CTS5/PEPI/NPI/Magee/IHC4/H-score/RCB/Gail)
- [ ] Workspace 結果區（dashboard 完成後）
- [ ] Module badges (`.module-badge.stable / .beta-inside`)
- [ ] Validation harness HTML（`tests/predict_validation_auto.html` 獨立頁，不繼承 dark）

### 執行方式
1. 開瀏覽器，按 Ctrl+D 切到 dark mode
2. 點過所有 9 張卡片 + 所有 calc tabs + 設定 + issue modal
3. 截圖對照淺色版 — 找出不協調處
4. 補 `body.dark` CSS

### 估計：30-45 分鐘

---

## 📱 任務 3：手機/平板響應式 audit

### 現況
已有 media queries，但需實機驗證。

### 測試 checklist
- [ ] iPhone SE (375×667) — landing 卡片是否擠？
- [ ] iPhone 14 Pro (393×852)
- [ ] iPad (768×1024)
- [ ] iPad Pro (1024×1366)
- [ ] Android 中階機 (360×640)

### 已知潛在問題
1. AJCC 的 prognostic biomarker 區塊在窄螢幕擠壓
2. Calculator 9 個 tabs 換行後可能排版亂
3. Workspace ws-form 在手機可能太擠
4. Issue modal 在小螢幕可能切到 viewport 外
5. Trials 列表在手機是否好讀
6. Surgery 自費清單分組標題在手機 line-height

### 執行方式
1. Chrome DevTools → Toggle device toolbar
2. 測試以上 5 種尺寸
3. 找出問題 → 加 `@media` 補修

### 估計：1 小時

---

## 🔧 任務 4：其他 backlog（可有可無）

### 4a. PREDICT v4.0 升級（含 radiotherapy）
- 論文 paywall 擋住，但 R 套件可能有 v4 版本可裝
- 嘗試：`install.packages("predictv4", ...)` 看有無
- 若有，重跑 R snapshot
- 若無，留 v2.1 + 外連 v4

### 4b. MSK Nomograms 實作
- Bevilacqua 2007 SLN nomogram
- Van Zee 2003 Non-SLN nomogram
- 論文 paywall，可能找得到 supplementary 表
- 若不行，繼續外連

### 4c. 模組化重構
- 開新 branch `refactor/modularize`
- 照 ARCHITECTURE.md Phase 1 進行
- 從 `core/flags.js` 抽出開始
- 寫新版 `build.py` concat 所有 module → index.html

### 4d. 設 Netlify Branch Deploys
- Site settings → Build & deploy → Branches
- 啟用 develop / feature/* 預覽 URL
- 寫到 DEVELOPMENT.md §3 的詳細步驟

### 4e. 鍵盤快捷鍵
- Esc 返回上頁
- 1–9 切換 dept-card
- `/` 開搜尋
- `?` 顯示快捷鍵列表

### 4f. 個案摘要整合列印（橫跨多分頁）
- Workspace dashboard 完成後做
- 一鍵列印含所有結果的單頁 PDF

---

## 📝 Session 開頭給新 AI 的 prompt 範例

```
我接手 NTUH_Breast_Caculator (https://github.com/erichuang777777/NTUH_Breast_Caculator)
工作目錄：D:\NHI_Drug_Caculator
最新版本：v1.9 (commit 7ca0218)

請看 TODO.md 從「任務 1：Dashboard 模式」開始實作。
規範：
1. 不要為快速做出錯
2. 每個改動都跑 JS syntax check (Python regex + node --check)
3. 每次完成 commit 前都 sync 到 NP_dashboard 的 template
4. PREDICT 已通過 R 驗證 (tests/predict_validation_auto.html)，改動不要破壞
5. AJCC v9 用 data/ajcc9_lookup.js 1440-entry 查表
6. 每個 calculator 都有獨立 FEATURE_FLAGS，可關閉
7. Beta 功能會自動加紅色徽章 + 設定面板有警示
```

---

## 📚 重要參考檔案

| 路徑 | 用途 |
|---|---|
| `index.html` | 主程式（單檔約 540KB） |
| `data/ajcc9_lookup.js` | AJCC v9 1440-entry 查表 |
| `tests/predict_snapshot.json` | R-validated PREDICT 標準答案（2595 cases） |
| `tests/predict_validation_auto.html` | 自動驗證工具 |
| `ARCHITECTURE.md` | 模組化重構藍圖 |
| `DEVELOPMENT.md` | 開發流程指南 |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Issue 範本 |

---

## ✅ 已完成（截至 v1.9）

- [x] PREDICT v2.1 + R 驗證 (100% pass, max 0.02% err)
- [x] AJCC v9 1440-entry 查表 (replaces simplified rules)
- [x] 9 個 calculator (PREDICT, CTS5, PEPI, NPI, Magee, IHC4, H-score, RCB, Gail)
- [x] Workspace + NHI 反向查詢
- [x] Feature Flags 13 個 + 齒輪設定面板
- [x] Stable/Beta 徽章
- [x] GitHub Issue 一鍵回報
- [x] Dark Mode 基礎（Ctrl+D toggle）
- [x] develop branch + ARCHITECTURE.md
- [x] 9 個 git tags (v1.0–v1.9)

---

*建立於 v1.9 / 2026-05-09*

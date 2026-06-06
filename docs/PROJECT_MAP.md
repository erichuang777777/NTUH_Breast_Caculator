# Project Map

這份文件只回答一件事：人要改這個專案時，應該先看哪裡。

## 一句話架構

```text
index.html
  -> assets/css/app.css
  -> assets/js/legacy-app.js
  -> assets/js/modules/drug-cards.js
  -> /api/* from web_app.py or data/api/*.json
  -> nhi_drug_coverage.db as source of truth
```

目前前端仍是 legacy SPA。不要期待它已經是乾淨模組化專案；新的整理目標是先建立清楚的閱讀路徑，再逐步拆小。

## 目前工作模式

| 使用情境 | 介面 |
|---|---|
| 手機 / 平板 / 舊 iPad Safari | 快速卡片入口 |
| 桌面大螢幕 | Patient Journey 工作台 |
| 管理藥物資料 | `admin.html` + `web_app.py` admin endpoints |
| Netlify production | 靜態 `index.html` + `netlify/functions/api.js` + `data/api/*.json` |
| 本機維護 | `python web_app.py` + SQLite |

## 最常改的地方

| 你要改什麼 | 先看 |
|---|---|
| 桌面 Patient Journey 外觀 | `assets/css/app.css`，搜尋 `patient-journey-dashboard` |
| 桌面 Patient Journey 內容 | `assets/js/legacy-app.js`，搜尋 `renderModalDashboardOverview` |
| 共同病人變數 | `assets/js/legacy-app.js`，搜尋 `PATIENT_DEFAULTS`、`_patient`、`dashboardPatientContext` |
| 手機/平板卡片入口 | `assets/js/legacy-app.js`，搜尋 `loadLanding` |
| 舊 iPad Safari 觸控 | `assets/js/legacy-app.js`，搜尋 `bindLegacySafariTouchActivation` |
| 分期與亞型輸入 | `index.html` 的 `wsPage`，與 `assets/js/legacy-app.js` workspace functions |
| 乳癌藥物卡片 | `assets/js/modules/drug-cards.js` |
| 住院化療 | `assets/js/modules/drug-cards.js` 與 `assets/js/legacy-app.js` regimen section |
| 重卡編號 | `assets/js/modules/drug-cards.js`，搜尋 `selectIcdZone`; `assets/js/legacy-app.js`，搜尋 `deriveWorkspaceICD` |
| 臨床試驗 | `clinical_trials_lib/` 與 `assets/js/modules/drug-cards.js` trial section |
| PREDICT / Gail / other calculators | `assets/js/legacy-app.js`，搜尋 `calcPredict`、`dashboardCalcScoreSummary` |
| API 回傳 | `web_app.py` |
| 靜態 JSON 匯出 | `api_export.py` |

## 核心檔案分層

### Frontend

```text
index.html
assets/css/app.css
assets/js/legacy-app.js
assets/js/modules/drug-cards.js
assets/js/modules/ajcc/
```

`legacy-app.js` 是最大技術債。短期不要在裡面新增大段無關功能；若新增可獨立模組，優先放到 `assets/js/modules/`，再由 `index.html` 載入。

### Backend / API

```text
web_app.py
api_calculators.py
api_export.py
netlify/functions/api.js
```

本機以 `web_app.py` 為主。Netlify production 以靜態 JSON 和 `netlify/functions/api.js` 為主。

### Data

```text
nhi_drug_coverage.db
data/api/
data/patches/
data/viz_data.json
NTUH_catastrophic_apply.txt
```

`nhi_drug_coverage.db` 是藥物/價格 source of truth。  
`data/api/*.json` 是給 Netlify 靜態 API 使用的匯出結果。  
`data/viz_data.json` 是 NCCN / journey visual data 的主要候選來源。  
`NTUH_catastrophic_apply.txt` 是院內重卡來源檔，不是 runtime entry。

### Breast Clinical Logic

```text
breast_cancer_tools/
specialties/breast/
tests/
```

`breast_cancer_tools/` 保留原始演算法。  
`specialties/breast/` 是較乾淨的 specialty wrapper。  
新演算法應優先在這層整理，再接回前端。

### Clinical Trials

```text
app/
clinical_trials_lib/
run.py
```

這一組是臨床試驗搜尋/整合模組。若只改前端 trial card，不一定需要碰這裡。

## 安全修改流程

### 前端 UI 修改

1. 改 `index.html` / `assets/css/app.css` / `assets/js/*`
2. 更新 query string cache version，例如 `?v=20260529a`
3. 跑：

```bash
node --check assets/js/legacy-app.js
node --check assets/js/modules/drug-cards.js
```

4. 桌面與手機各截圖檢查一次。

### DB / 藥價 / 給付修改

1. 建 patch file 到 `data/patches/`
2. `python tools/db_patch.py <patch> --dry-run`
3. `python tools/db_patch.py <patch>`
4. `python api_export.py`
5. `python tools/check_api.py`

不要直接用 ad hoc SQL 改 DB，除非明確是緊急修復。

### Python 修改

```bash
python tools/check_api.py
python -m py_compile web_app.py api_export.py api_calculators.py tools/db_patch.py tools/check_api.py
python -m pytest tests\test_breast_specialty_toolkit.py breast_cancer_tools\tests -q
```

## Patient Journey Roadmap

現在的方向：

```text
patientContext
  -> disease stage
  -> subtype
  -> treatment phase
  -> NCCN node
  -> tool summaries
```

已建立的前端概念：

- `dashboardPatientContext()`
- `dashboardJourneyState()`
- `renderModalDashboardOverview()`

下一步應該把 `data/viz_data.json` 接成可查詢的 journey node source，並讓每個 node 保留：

- guideline version/date
- page 或 algorithm ID
- citation text
- matching variables
- required missing variables
- suggested next tool cards

## 暫時不要做的事

- 不要把 `legacy-app.js` 一次性大拆；風險高，且容易破壞手機/iPad 觸控。
- 不要搬 `index.html`、`web_app.py`、`nhi_drug_coverage.db` 這些 runtime entry。
- 不要把本地大型來源資料夾直接加進版控。
- 不要讓 Patient Journey 只變成另一個文字查詢頁；它應該吃共同病人變數。

## 建議後續整理順序

1. 把 Patient Journey 相關 JS 從 `legacy-app.js` 抽到 `assets/js/modules/patient-journey.js`。
2. 把 workspace patient state 抽到 `assets/js/modules/patient-context.js`。
3. 把 dashboard card summary 抽到 `assets/js/modules/dashboard-summary.js`。
4. 只保留 `legacy-app.js` 作為舊功能相容層。

這樣可以逐步降低閱讀負擔，而不需要一次重寫整個前端。

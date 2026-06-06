# NTUH Breast Calculator

乳癌健保藥物查詢、住院化療費用試算、院內重卡編號、乳癌分期/亞型與 Patient Journey 工作台。

這個 repo 目前同時支援兩種使用方式：

- **手機/平板**：快速卡片入口，適合臨床現場快速查詢。
- **桌面版**：Patient Journey 工作台，使用同一組病人變數串起分期、亞型、藥物、化療、重卡、臨床試驗與 NCCN 節點。

## 先看這些

| 目的 | 檔案 |
|---|---|
| 快速知道專案怎麼讀 | [docs/PROJECT_MAP.md](docs/PROJECT_MAP.md) |
| 模組邊界與抽換契約 | [docs/MODULE_BOUNDARIES.md](docs/MODULE_BOUNDARIES.md) |
| 跨癌別模組契約 | [docs/MULTI_CANCER_MODULE_CONTRACT.md](docs/MULTI_CANCER_MODULE_CONTRACT.md) |
| 外部資料接入規範 | [docs/EXTERNAL_DATA_INTEGRATION.md](docs/EXTERNAL_DATA_INTEGRATION.md) |
| legacy 拆分路線 | [docs/REFACTOR_ROADMAP.md](docs/REFACTOR_ROADMAP.md) |
| 本機啟動 | 本 README 的「快速開始」 |
| API 端點 | [API.md](API.md) |
| 部署 | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| 資料來源 | [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) |
| 維護規則 | [docs/MAINTENANCE.md](docs/MAINTENANCE.md) 與 [AGENTS.md](AGENTS.md) |

## 快速開始

```bash
python web_app.py
```

然後打開：

```text
http://127.0.0.1:8080/
```

## 主要入口

| 區域 | 主要檔案 | 說明 |
|---|---|---|
| 前台頁面 | `index.html` | SPA 主頁，手機卡片入口與桌面 Patient Journey 都從這裡進入 |
| 前端主邏輯 | `assets/js/legacy-app.js` | 目前最大技術債；包含 dashboard、workspace、calculator、Patient Journey glue code |
| 可抽換前端邊界 | `assets/js/modules/*-adapter.js`, `assets/js/modules/*-state.js`, `assets/js/modules/benchmark-*.js` | Patient context、Agent gateway、Agent panel state、Benchmark loader/browser 的小型模組 |
| 癌別模組範本 | `assets/js/modules/disease/breast/manifest.json` | 第一個 disease module manifest；其他癌別照此格式新增 |
| 乳癌藥物/重卡/臨床試驗 UI | `assets/js/modules/drug-cards.js` | 藥物卡片、住院化療、重卡圖例、試驗結果等 |
| 樣式 | `assets/css/app.css` | 主樣式；含手機卡片與桌面 Patient Journey layout |
| 本機 API/Admin | `web_app.py` | 本機 server、API、後台寫入 |
| 靜態 API 匯出 | `api_export.py` | DB 變更後輸出 `data/api/*.json` |
| 資料庫 | `nhi_drug_coverage.db` | SQLite source of truth |

## 常用指令

| 指令 | 用途 |
|---|---|
| `python web_app.py` | 啟動本機主站 |
| `python tools/check_api.py` | 檢查 API/data 匯出一致性 |
| `python -m py_compile web_app.py api_export.py api_calculators.py tools/db_patch.py tools/check_api.py` | Python 語法檢查 |
| `node --check assets/js/legacy-app.js` | 前端主 JS 語法檢查 |
| `node --check assets/js/modules/drug-cards.js` | drug-cards JS 語法檢查 |
| `python -m pytest tests\test_breast_specialty_toolkit.py breast_cancer_tools\tests -q` | 乳癌演算法測試 |

## 資料修改原則

不要直接手動 SQL 修改 `nhi_drug_coverage.db`。資料修正請走：

1. 建立 `data/patches/*.json`
2. `python tools/db_patch.py data/patches/<patch>.json --dry-run`
3. `python tools/db_patch.py data/patches/<patch>.json`
4. `python api_export.py`
5. `python tools/check_api.py`

詳細規則見 [AGENTS.md](AGENTS.md)。

## NCCN / Patient Journey

目前方向是：

```text
共同病人變數 -> NCCN journey 節點定位 -> 工具卡片顯示當前節點需要的資訊
```

相關位置：

- 共同病人變數：`_patient` / `_patient_workspace` in `assets/js/legacy-app.js`
- 桌面 Patient Journey shell：`renderModalDashboardOverview()` in `assets/js/legacy-app.js`
- NCCN 視覺/流程資料：`data/viz_data.json`

NCCN 內容接入時請保留 guideline version、page/algorithm ID 與引用資訊。

## 不要從這些開始讀

- `assets/js/legacy-app.js` 第 1 行的大型 `_STATIC_DRUGS` 會干擾閱讀；看功能時請先用 [docs/PROJECT_MAP.md](docs/PROJECT_MAP.md) 定位函式。
- `web_app.py` 很大，先確認是 API 問題還是前端問題再進去。
- `NTUH_catastrophic_apply.txt` 和 `ntuh_dashboard_modal_B.html` 是本地參考/來源檔，不是正式入口。

## 備註

本工具僅供醫療人員臨床查詢與試算輔助，不取代醫師判斷、健保署公告或院內正式流程。

# 健保腫瘤藥物查詢系統 — NHI Oncology Drug Calculator

台灣健保腫瘤科藥物查詢與療程費用試算工具，支援乳癌及血液腫瘤科。

## 功能特色

- **藥物查詢**：85 種健保給付腫瘤科藥物（乳癌 42 種、血液腫瘤 40 種）
- **健保藥價 + 台大藥價**：同時收錄 115 年健保支付標準及台大醫院 2024/12/05 藥品價目表（66 品項）
- **處方費用計算**（新分頁）：
  - 10 種常用化療處方：EC→THP→HP、TCHP→HP、EC→T、TC、AC→wPH、T-DM1、Trodelvy、CDK4/6i+AI、Xeloda、Enhertu
  - 輸入體重/身高自動計算 BSA，依處方劑量計算
  - Carboplatin 支援 AUC/Calvert 公式（需 GFR）
  - 藥品搭配最經濟組合（如 Epirubicin 2×50mg+5×10mg 優於 3×50mg）
  - 每個藥物可獨立切換健保/自費
  - 疾病特徵（HER2/HR/N+/N0）自動帶入健保預設
  - 支持性治療附加（止吐、GCSF、卵巢抑制、冷卻帽、基因檢測）
- **HP 雙標靶連動計算**（藥物詳情頁）：
  - 淋巴節轉移 (N+)：Herceptin 健保給付，Perjeta 自費
  - 淋巴節無轉移 (N0)：兩藥均需自費
  - 支援 6 個月 / 12 個月標準療程
- **給付條件查詢**：事前審查要求、療程線別、給付條件說明
- **品質評分**：97.1%（適應症覆蓋率 100%、療程線覆蓋率 98.8%）

## 快速啟動

### 環境需求

- Python 3.8+（無需額外安裝套件，使用標準函式庫）

### 執行

```bash
cd drug_appli
python web_app.py
```

瀏覽器開啟：http://localhost:8080

## HP 雙標靶療程費用試算（60kg，115年藥價）

| 情境 | 6 個月（8 週期） | 12 個月（18 週期） |
|------|----------------|------------------|
| **N+**：Herceptin 健保，Perjeta 自費 | 自費 NT$404,361 | 自費 NT$853,651 |
| **N0**：兩藥均自費 | 自費 NT$661,023 | 自費 NT$1,395,493 |

> 首劑起始劑量：Herceptin 8mg/kg（後續 6mg/kg），Perjeta 840mg（後續 420mg）

## 資料來源

| 資料 | 來源 |
|------|------|
| 藥品給付規定 | 全民健康保險藥品給付規定（115/03/23 版本） |
| 健保藥價 | 115 年藥品支付價格年度例行調整結果明細表（115/04/01 生效） |
| 台大藥價 | 台大醫院藥品價目表（2024/12/05 更新，66 品項） |
| Trodelvy 藥價 | NHI 藥品代碼 KC01206262（NT$29,039/180mg vial，113/02/01） |
| Vinblastine 藥價 | NHI 藥品代碼 BC21880229（NT$606/10mg vial） |

## 資料庫結構

```
nhi_drug_coverage.db
├── drugs              -- 藥物基本資料（generic_name, trade_names, nhi_price, dosage_info ...）
├── coverage_rules     -- 給付條件（therapy_line, condition, prior_auth_required ...）
└── drug_formulations  -- 各劑型品項（dose_mg, nhi_price, ntuh_price, category, regimen_use）
```

## 主要檔案

| 檔案 | 說明 |
|------|------|
| `web_app.py` | 主程式，單一檔案 SPA Web 應用（Python http.server） |
| `nhi_drug_coverage.db` | SQLite 藥物資料庫 |
| `validate_drugs.py` | 資料品質驗證工具 |
| `update_official_prices.py` | 官方 115 年藥價更新腳本 |
| `parse_docx.py` | 健保給付規定 DOCX 解析器 |
| `known_oncology_drugs.py` | 已知腫瘤科藥物清單 |
| `populate_prices.py` | 藥價初始化腳本 |
| `import_ntuh_prices.py` | 台大醫院藥價匯入腳本 |
| `2024_12_5_price.csv` | 台大醫院藥品價目表原始資料 |

## 注意事項

- 本系統僅供參考，實際給付以健保署公告為準
- 藥價依健保支付標準，自費藥品市場價格可能不同
- 療程費用試算未含給藥耗材、藥師費等其他費用
- 本系統聚焦於健保給付藥物，非健保藥物（如 Phesgo、Enhertu）不在範圍內

## License

資料來源：衛生福利部中央健康保險署（NHIA），全民健康保險藥品給付規定為公開資料。

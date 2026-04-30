# NHI Oncology Drug Calculator

台灣健保腫瘤科藥物查詢與療程費用試算系統。主要查詢站維持單一檔案 SPA；乳癌臨床決策工具另外整理成可替換的 specialty module，方便單獨更新部件。

## 快速啟動

```bash
python web_app.py
# 瀏覽器開啟 http://localhost:8080
```

## 功能

| 功能 | 說明 |
|------|------|
| 藥物查詢 | 86 種健保給付腫瘤藥物（乳癌 40、血腫 41、其他 5），支援篩選：受體狀態、分期、療程線、突變 |
| 療程費用計算 | 10 種常用處方，輸入體重/身高自動計算劑量，藥品搭配最經濟組合（vial optimization） |
| 雙藥價系統 | 健保支付標準（115/04/01）+ 台大醫院藥價（2024/12/05），每藥可獨立切換健保/自費 |
| HP 雙標靶 | N+ 自動帶入 Herceptin 健保 + Perjeta 自費；N0 兩藥自費。支援 6/12 個月 |
| 藥物交互作用 | 12 種藥物的交互作用提醒（CYP2D6、CYP3A4、QTc 等），依嚴重度標示 |
| 副作用速查 | 22 種藥物的常見/嚴重副作用及處置建議 |
| 腎功能調整 | 6 種藥物的 CrCl 分級劑量調整表（Carboplatin Calvert formula） |
| TNBC 自動偵測 | ER/PR- + HER2- 自動標示三陰性乳癌 |
| 列印/PDF | 療程費用試算結果一鍵匯出列印 |
| 離線模式 | API 資料自動快取至 localStorage，斷線時仍可查詢 |
| 管理工具 | 新增/編輯藥物（含分期、療程線）、匯出 CSV、資料來源下載 |

## 架構

```
web_app.py              ← 主程式（Python http.server + 內嵌 HTML/CSS/JS SPA）
nhi_drug_coverage.db    ← SQLite 資料庫
2024_12_5_price.csv     ← 台大藥價原始資料
import_ntuh_prices.py   ← 台大藥價匯入工具（建立 drug_formulations 表）
update_official_prices.py ← 健保藥價更新工具（115年官方藥價）
core/specialty_loader.py ← 載入 disease-specific specialty modules
specialties/breast/     ← 乳癌 specialty 包裝層（可單獨置換）
breast_cancer_tools/    ← 乳癌演算法實作與測試
```

### 資料庫 Schema

```sql
drugs              -- id, generic_name, trade_names, specialty_id, indication,
                   -- clinical_tags(JSON), stage, nhi_price, price_unit, dosage_info(JSON)
coverage_rules     -- drug_id, therapy_line, condition, prior_auth_required
drug_formulations  -- drug_key, brand_name, formulation, dose_mg, dose_unit,
                   -- category(IV/oral), nhi_price, ntuh_price, nhi_covered, regimen_use
```

### API 端點

| Method | Path | 說明 |
|--------|------|------|
| GET | `/` | SPA 主頁 |
| GET | `/api/stats` | 藥物統計（各科數量） |
| GET | `/api/drugs?category=oncology_breast` | 藥物列表（可依科別篩選） |
| GET | `/api/drug/:id` | 單一藥物詳情 |
| GET | `/api/formulations` | 藥品劑型及價格 |
| PUT | `/api/drug/:id` | 更新藥物資料 |
| POST | `/api/drugs` | 新增藥物 |
| DELETE | `/api/drug/:id` | 刪除藥物 |

## 資料來源

- 健保藥品給付規定 115/03/23 版
- 健保藥品支付價格 115/04/01 生效
- 台大醫院藥品價目表 2024/12/05

## 注意事項

本系統僅供參考，實際給付以健保署公告為準。藥價依健保支付標準，自費藥品市場價格可能不同。

## 未來規劃

- 臨床試驗篩選：AJCC T/N/M 分期 + 受體狀態 + 治療史，自動匹配適用臨床試驗

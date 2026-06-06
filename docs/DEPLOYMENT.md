# Deployment

## 目的

本文件只記錄上線方式、環境需求與常用更新指令。架構細節與資料來源拆到其他文件。

## 環境

### 主站

- Python 3.10+ 建議
- 無額外第三方套件即可啟動 `web_app.py`
- SQLite 檔案：`nhi_drug_coverage.db`

### Flask 臨床試驗模組

- 需安裝 `requirements.txt`
- 主要套件：`Flask`、`flask-cors`、`requests`、`Werkzeug`

安裝：

```bash
pip install -r requirements.txt
```

## 上線模式

### 1. 主站 / 本機維護版

```bash
python web_app.py
```

- 預設埠：`http://localhost:8080`
- 適合本機維護、資料校對、快速測試

### 2. 靜態部署版

```bash
python build_static.py
```

- 會由 `NP_dashboard/NHI Drug Calculator.html` + `nhi_drug_coverage.db` 重建 `index.html`
- `index.html` 為唯讀靜態輸出，可部署到 Netlify 或其他靜態主機
- `netlify.toml` 已在 repo 內

### 3. Flask 臨床試驗模組

```bash
python run.py
```

- 預設埠：`http://localhost:5000`
- 用於 ClinicalTrials.gov 整合，不是主查詢站的唯一部署方式

## 更新流程

### 常規資料更新

```bash
python update_official_prices.py
python import_ntuh_prices.py
python update_ntuh_prices.py --days 30
python build_static.py
```

### 驗證

```bash
python -m pytest tests\test_breast_specialty_toolkit.py breast_cancer_tools\tests -q
```

### 推版建議順序

1. 更新資料
2. 抽查重點藥物
3. 跑測試
4. 重建靜態頁
5. commit / push
6. 再部署靜態站

## 上線前檢查

- `nhi_drug_coverage.db` 是否為預期版本
- `index.html` 是否重新由最新資料重建
- 乳癌 specialty 模組是否仍能正常載入
- 重要藥物價格與給付條件是否經人工抽查
- 若有臨床試驗模組，確認 `requirements.txt` 已安裝

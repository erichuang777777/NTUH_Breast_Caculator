# Maintenance

> 新進維護者請先看 `README.md` 與 `docs/PROJECT_MAP.md`。本文件保留維護細節；DB 變更規則以根目錄 `AGENTS.md` 為準。

## 目標

本文件定義每週更新、人工確認與通報處理流程，避免維護時只靠口頭記憶。

## 每週例行

建議至少每週一次：

```bash
python update_ntuh_prices.py --days 7
python build_static.py
python -m pytest tests\test_breast_specialty_toolkit.py breast_cancer_tools\tests -q
```

檢查重點：

- 台大價格是否有明顯異動
- 重要乳癌藥物是否仍可正常查詢
- specialty 模組是否仍能正常載入

## 健保公告更新時

如果有新的健保藥價公告或給付規定：

```bash
python update_official_prices.py
python build_static.py
```

CI 也會每月自動跑一次 dry-run 與 API smoke check，對應 `.github/workflows/monthly-api-check.yml`。

之後要人工抽查：

- HER2 標靶
- CDK4/6 抑制劑
- 主要化療藥
- 卵巢抑制 / 骨轉移支持藥物

## 台大資料重建時

若收到新的台大價目表：

```bash
python import_ntuh_prices.py
python update_ntuh_prices.py --force
python build_static.py
```

## 人工確認清單

以下項目不應完全相信腳本輸出：

- 單藥給付文字與臨床情境是否一致
- 治療線是否仍正確
- 價格是否對到正確規格
- 品牌名 / 學名是否被誤填
- specialty wrapper 是否仍指向正確演算法模組

## 通報處理流程

建議固定流程：

1. 收到通報
2. 建立 GitHub issue
3. 標記問題類型
4. 對照資料來源
5. 修正資料或程式
6. 跑測試與重建
7. 關閉 issue，更新 changelog

### 問題類型建議

- `data-price`
- `data-coverage`
- `breast-module`
- `ui-static`
- `clinical-trials`

## specialty 模組維護

乳癌功能現在拆為：

- `specialties/breast/ihc4_predictor.py`
- `specialties/breast/ajcc_converter.py`
- `specialties/breast/stratification.py`
- `specialties/breast/toolkit.py`

維護原則：

- 若只換演算法入口，優先改 `specialties/breast/`
- 若改核心公式，再動 `breast_cancer_tools/`
- 不要把單一 specialty 的邏輯重新散回大頁面

## 提交前檢查

- `git status` 只包含預期修改
- `.pytest_cache/`、`__pycache__/` 不應被加入版控
- `README.md` 只保留總覽與操作入口
- 細節變更若有維護意義，補進 `docs/CHANGELOG.md`
# Maintenance Notes

> 新進維護者請先看 `README.md` 與 `docs/PROJECT_MAP.md`。本文件保留維護細節；DB 變更規則以根目錄 `AGENTS.md` 為準。

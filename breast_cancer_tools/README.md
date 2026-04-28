# 乳癌臨床分層工具模塊 (Breast Cancer Stratification Tools)

## 📋 概覽

這是一個為乳癌患者提供臨床決策支持的 Python 模塊，整合了多種診斷和預測工具：

- **IHC4 Score** - 基於免疫組織化學的預後評分
- **Predict Score** - 內分泌治療獲益預測
- **AJCC 分期** - 腫瘤-淋巴結-轉移 (TNM) 到 AJCC 分期的轉換
- **臨床分層** - 綜合決策支持系統

---

## 📁 目錄結構

```
breast_cancer_tools/
├── __init__.py                          # 模塊初始化
├── ihc4_predictor.py                    # IHC4 & Predict Score 計算
├── ajcc_converter.py                    # AJCC 分期轉換
├── stratification.py                    # 綜合分層決策
├── data/                                # 配置和數據文件
│   ├── ihc4_config.json
│   ├── ihc4_coefficients.json          # 迴歸係數
│   ├── ajcc_staging_9.json              # AJCC 9th Edition 分期表
│   ├── ajcc_staging_8.json              # AJCC 8th Edition 分期表
│   └── therapy_guidelines.json          # 治療建議指南
├── docs/                                # 文檔
│   ├── API_SPECIFICATION.md             # API 規格（已完成）
│   ├── IMPLEMENTATION_GUIDE.md          # 實現指南（已完成）
│   ├── INTEGRATION_GUIDE.md             # Flask 集成指南（已完成）
│   └── USAGE_GUIDE.md                   # 使用指南（待補充）
└── tests/                               # 單元測試
    ├── __init__.py
    ├── test_ihc4.py                     # IHC4 測試框架（已建立）
    ├── test_ajcc.py                     # AJCC 測試框架（待建立）
    └── test_stratification.py           # 分層測試框架（待建立）
```

---

## 🚀 快速開始

### 1. 安裝

本模塊無外部依賴，只需要 Python 3.7+

```bash
# 模塊已在 breast_cancer_tools/ 目錄中
# 導入時確保路徑正確
import sys
sys.path.insert(0, 'path/to/breast_cancer_tools')
```

### 2. 基本使用

```python
from breast_cancer_tools import IHC4Calculator, AJCCStageConverter

# 初始化計算器
ihc4_calc = IHC4Calculator()
ajcc_conv = AJCCStageConverter(edition=9)

# 計算 IHC4 Score
result = ihc4_calc.calculate(
    er_score=250,
    pr_score=150,
    her2_score=0,
    ki67_percentage=15.0,
    age=55
)
print(f"IHC4 Score: {result.ihc4_score}")
print(f"Risk: {result.risk_category}")
print(f"Subtype: {result.subtype.value}")

# 轉換 AJCC 分期
ajcc_result = ajcc_conv.convert(
    t="T2",
    n="N1a",
    m="M0",
    grade=2,
    er_status="Positive",
    pr_status="Positive",
    her2_status="Negative"
)
print(f"AJCC Stage: {ajcc_result.clinical_stage.value}")
```

---

## 📖 文檔

### 對使用者
- **[API_SPECIFICATION.md](docs/API_SPECIFICATION.md)** - REST API 規格和使用範例

### 對開發者
- **[IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)** - 詳細實現指南和計算邏輯
- **[INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)** - Flask 應用集成指南

---

## 📊 模塊說明

### IHC4Calculator (`ihc4_predictor.py`)

計算基於 4 個免疫組織化學標誌物的預後評分

**主要方法：**
- `calculate()` - 計算 IHC4 Score
- `calculate_predict_score()` - 基於 IHC4 計算內分泌治療獲益
- `get_subtype_classification()` - 判斷乳癌亞型
- `validate_input()` - 驗證輸入參數

**支持的亞型：**
- Luminal A
- Luminal B
- HER2-enriched
- Triple Negative

### AJCCStageConverter (`ajcc_converter.py`)

將 TNM 分類轉換為 AJCC 分期

**主要方法：**
- `convert()` - TNM 轉 AJCC 分期
- `get_prognostic_group()` - 確定預後分組
- `get_treatment_recommendation()` - 治療建議
- `compare_editions()` - 比較版本差異

**支持的版本：**
- AJCC 8th Edition (2017)
- AJCC 9th Edition (2023) - 含生物標誌物加權

### BreastCancerStratification (`stratification.py`)

整合的臨床決策支持系統

**主要方法：**
- `stratify()` - 綜合分層分析
- `recommend_therapy()` - 治療方案推薦
- `generate_report()` - 生成臨床報告

---

## 🔄 開發進度

### 已完成 ✅
- [x] 模塊架構設計
- [x] API 規格文檔
- [x] 實現指南
- [x] Flask 集成指南
- [x] 單元測試框架

### 進行中 🔄
- [ ] IHC4 計算邏輯實現
- [ ] Predict Score 計算
- [ ] AJCC 分期邏輯實現
- [ ] 數據配置文件 (JSON)
- [ ] 分層決策邏輯
- [ ] 單元測試實現

### 待進行 ⏳
- [ ] 集成測試
- [ ] 性能測試
- [ ] 前端 UI 實現
- [ ] 文檔補充

---

## 🛠️ 開發檢查清單

開發者可按以下步驟逐一實現：

### Phase 1: 核心計算邏輯
- [ ] 實現 `IHC4Calculator.calculate()`
- [ ] 實現 `IHC4Calculator.get_subtype_classification()`
- [ ] 建立 `data/ihc4_coefficients.json`
- [ ] 寫單元測試 (test_ihc4.py)

### Phase 2: AJCC 轉換
- [ ] 實現 `AJCCStageConverter.convert()`
- [ ] 實現 `AJCCStageConverter.get_prognostic_group()`
- [ ] 建立 `data/ajcc_staging_9.json` 和 `ajcc_staging_8.json`
- [ ] 建立 `data/therapy_guidelines.json`
- [ ] 寫單元測試 (test_ajcc.py)

### Phase 3: 分層決策
- [ ] 實現 `BreastCancerStratification.stratify()`
- [ ] 實現 `BreastCancerStratification.recommend_therapy()`
- [ ] 實現 `BreastCancerStratification.generate_report()`
- [ ] 寫單元測試 (test_stratification.py)

### Phase 4: 集成和測試
- [ ] 集成到 Flask 應用 (`app/app.py`)
- [ ] 集成測試
- [ ] 性能測試
- [ ] 前端 UI

### Phase 5: 部署和文檔
- [ ] 補充 USAGE_GUIDE.md
- [ ] 修改 requirements.txt (如有新依賴)
- [ ] 提交到 GitHub
- [ ] 部署到生產環境

---

## 📝 數據配置檔案格式

### `data/ihc4_config.json`
```json
{
  "version": "1.0",
  "er_positive_cutoff": 10,
  "pr_positive_cutoff": 10,
  "her2_positive_cutoff": 2,
  "ki67_low_cutoff": 13.25,
  "ki67_high_cutoff": 30,
  "coefficients": {
    "er": 0.8,
    "pr": 0.5,
    "her2": 0.4,
    "ki67": 1.2,
    "intercept": -5.0
  }
}
```

### `data/ajcc_staging_9.json`
```json
{
  "STAGE_0": {...},
  "STAGE_IA": {...},
  "STAGE_IB": {...},
  ...
}
```

詳見 IMPLEMENTATION_GUIDE.md

---

## 🧪 運行測試

```bash
# 安裝測試依賴
pip install pytest

# 運行所有測試
pytest tests/ -v

# 運行特定測試
pytest tests/test_ihc4.py -v

# 生成覆蓋率報告
pytest tests/ --cov=breast_cancer_tools --cov-report=html
```

---

## 🌐 Flask 應用集成

在 `app/app.py` 中添加路由（詳見 INTEGRATION_GUIDE.md）：

```python
@app.route('/api/breast-cancer/ihc4/calculate', methods=['POST'])
def calculate_ihc4():
    # ...
```

可用的 API 端點：
- `POST /api/breast-cancer/ihc4/calculate`
- `POST /api/breast-cancer/ajcc/stage`
- `POST /api/breast-cancer/stratification/full`

---

## 📚 參考資源

### 論文和指南
- Dowsett et al. Prediction of endocrine therapy benefit from ER and HER2 status. J Natl Cancer Inst. 2010;102(21):1618-1632.
- AJCC Cancer Staging Manual 8th and 9th Editions
- St Gallen International Breast Cancer Conference 2021
- NCCN Guidelines for Breast Cancer

### 線上工具
- PREDICT: https://www.predict.nhs.uk/
- AJCC Staging: https://cancerstaging.org/

---

## 📞 支持和反饋

有任何問題或建議，歡迎提交 Issue 或 Pull Request。

---

## 📄 許可

本模塊為開源項目，遵循相應的開源許可證。

---

## 版本歷史

### v1.0.0 (2024-04)
- 初始版本
- 模塊架構完成
- 文檔和規格完成
- 測試框架建立

**下一步：** 實現核心計算邏輯

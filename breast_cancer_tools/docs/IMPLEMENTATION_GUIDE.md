# 乳癌分層工具 - 實現指南

## 概覽

本文檔指導如何實現 `breast_cancer_tools` 模塊中的核心計算邏輯。

---

## 1. IHC4 Score 計算

### 理論背景

IHC4 是基於 4 個免疫組織化學 (IHC) 標誌物的預後評分：
- **ER** (雌激素受體)
- **PR** (孕激素受體)
- **HER2** (人類表皮生長因子受體 2)
- **Ki67** (增殖指數)

### 計算公式

```
IHC4 Score = ER component + PR component + HER2 component + Ki67 component

其中每個成分基於該標誌物的表達水平進行計算
```

### 實現步驟

#### Step 1: 標準化輸入值

```python
def normalize_scores(er, pr, her2, ki67):
    """
    將 H-score 或 IHC 轉換為標準化分數
    
    H-score (0-300):
    - 0-10: 陰性 (0)
    - 11-100: 弱陽性 (1)
    - 101-200: 中陽性 (2)
    - >200: 強陽性 (3)
    
    IHC (0-3+): 直接使用
    """
    pass
```

#### Step 2: 計算各成分分數

```python
def calculate_er_component(er_normalized):
    """
    ER 成分計算
    參考: Dowsett et al. 2010 regression coefficients
    """
    # TODO: 使用迴歸係數
    pass

def calculate_pr_component(pr_normalized):
    """PR 成分計算"""
    pass

def calculate_her2_component(her2_normalized):
    """HER2 成分計算"""
    pass

def calculate_ki67_component(ki67_percentage, age):
    """
    Ki67 成分計算
    需要考慮年齡因素
    """
    pass
```

#### Step 3: 匯總並分類

```python
def classify_risk(ihc4_score):
    """
    根據 IHC4 評分分類風險
    
    範圍參考：
    - Low: IHC4 < 2.0
    - Intermediate: 2.0-4.0
    - High: > 4.0
    """
    pass
```

### 參考係數（待驗證）

從 Dowsett et al. 2010 論文提取：

```python
coefficients = {
    "er_coef": 0.8,        # ER 係數
    "pr_coef": 0.5,        # PR 係數
    "her2_coef": 0.4,      # HER2 係數
    "ki67_coef": 1.2,      # Ki67 係數
    "intercept": -5.0      # 截距
}
```

### 數據來源

- 獲取官方 Dowsett et al. 2010 論文中的迴歸係數
- 驗證與 PREDICT 工具的計算結果一致性
- 建立本地係數數據庫 (`data/ihc4_coefficients.json`)

---

## 2. Predict Score 計算

### 理論背景

Predict Score 是基於 IHC4 加上臨床因素的內分泌治療獲益預測

### 計算邏輯

```
Predict Score = IHC4 Score + 臨床因素調整

臨床因素包括：
- 患者年齡
- 腫瘤大小
- 組織學分級
- 淋巴結狀態
```

### 實現步驟

```python
def calculate_predict_score(ihc4_score, age, tumor_size, grade, node_positive):
    """
    1. 從 IHC4 開始
    2. 根據年齡調整
    3. 根據腫瘤大小調整
    4. 根據分級調整
    5. 根據淋巴結狀態調整
    6. 計算內分泌治療獲益百分比
    """
    
    # 年齡調整
    age_adjustment = calculate_age_adjustment(age)
    
    # 腫瘤大小調整
    size_adjustment = calculate_size_adjustment(tumor_size)
    
    # 分級調整
    grade_adjustment = calculate_grade_adjustment(grade)
    
    # 淋巴結調整
    node_adjustment = 0.5 if node_positive else 0.0
    
    # 最終評分
    final_score = ihc4_score + age_adjustment + size_adjustment + grade_adjustment + node_adjustment
    
    return final_score
```

---

## 3. AJCC 分期轉換

### AJCC 9th Edition 要點

AJCC 9th Edition (2023) 引入了**生物標誌物加權的預後分組**

### TNM 到分期的映射表

建立 `data/ajcc_staging_9.json`：

```json
{
  "STAGE_0": {
    "tnm": ["Tis N0 M0"],
    "criteria": "Non-invasive carcinoma"
  },
  "STAGE_IA": {
    "tnm": ["T1 N0 M0"],
    "criteria": "Tumor ≤20mm, no lymph node involvement"
  },
  "STAGE_IB": {
    "tnm": ["T0 N1mi M0", "T1 N1mi M0"],
    "criteria": "Micrometastasis in lymph nodes"
  },
  ...
}
```

### 實現邏輯

```python
def convert_to_ajcc_stage(t, n, m, grade, er, pr, her2):
    """
    1. 驗證 TNM 輸入
    2. 查表確定基本分期
    3. 根據生物標誌物調整預後分組
    4. 生成治療建議
    """
    
    # 查詢基本分期
    stage = lookup_stage_table(t, n, m)
    
    # 確定預後分組 (AJCC 9th edition)
    prognostic_group = determine_prognostic_group(
        t, n, m, grade, er, pr, her2
    )
    
    # 查詢治療建議
    treatment = get_treatment_recommendation(stage, prognostic_group)
    
    return {
        "stage": stage,
        "prognostic_group": prognostic_group,
        "treatment": treatment
    }
```

### 預後分組判斷

AJCC 9th edition 將患者分為 4 個預後分組 (Prognostic Groups, PG)：

```
PG1: Excellent prognosis
PG2: Good prognosis
PG3: Intermediate prognosis
PG4: Poor prognosis

判斷因素：TNM, Grade, ER/PR, HER2 狀態
```

---

## 4. 亞型分類

### St Gallen 2021 標準

實現 `BreastCancerSubtype` 分類：

```python
def classify_subtype(er, pr, her2, ki67):
    """
    分類標準：
    
    Luminal A-like:
    - ER+ or PR+
    - HER2-
    - Ki67 low (<20%)
    
    Luminal B-like (HER2-):
    - ER+
    - HER2-
    - Ki67 high (≥20%) OR PR-
    
    Luminal B-like (HER2+):
    - ER+ or PR+
    - HER2+
    
    HER2-enriched:
    - ER-
    - PR-
    - HER2+
    
    Triple Negative:
    - ER-
    - PR-
    - HER2-
    """
    pass
```

---

## 5. 治療建議引擎

### 實現結構

```python
def get_treatment_recommendation(subtype, stage, grade, er, her2):
    """
    返回格式：
    {
        "surgery": bool,
        "chemotherapy": bool,
        "hormone_therapy": bool,
        "trastuzumab": bool,
        "pertuzumab": bool,
        "immunotherapy": bool,
        "cdk4_6_inhibitor": bool,
        "specific_drugs": [list],
        "notes": str
    }
    
    邏輯規則：
    1. 所有患者都應該接受手術評估
    2. Luminal A, stage IA → 可能不需要化療
    3. Luminal B, HER2+ → 需要化療 + 內分泌治療
    4. TNBC → 化療優先，考慮免疫治療
    5. HER2+ → 加入 Trastuzumab (Herceptin)
    """
    pass
```

---

## 6. 單元測試框架

### 測試用例結構

```python
# tests/test_ihc4.py

def test_ihc4_luminal_a():
    """測試 Luminal A 型（低風險）"""
    calculator = IHC4Calculator()
    result = calculator.calculate(
        er_score=250,
        pr_score=150,
        her2_score=0,
        ki67_percentage=10.0,
        age=50
    )
    assert result.subtype == BreastCancerSubtype.LUMINAL_A
    assert result.risk_category == "Low Risk"

def test_ihc4_luminal_b():
    """測試 Luminal B 型（中風險）"""
    pass

def test_ihc4_her2_positive():
    """測試 HER2+ 型"""
    pass

def test_ihc4_triple_negative():
    """測試三陰性乳癌"""
    pass

def test_ihc4_invalid_input():
    """測試無效輸入"""
    calculator = IHC4Calculator()
    with pytest.raises(ValueError):
        calculator.calculate(
            er_score=400,  # 超出範圍
            ...
        )
```

---

## 7. 配置文件結構

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

TNM 到分期的映射表（見上面的示例）

### `data/therapy_guidelines.json`

治療建議指南（按亞型和分期）

---

## 8. 開發檢查清單

- [ ] 實現 IHC4Calculator.calculate()
- [ ] 實現 IHC4Calculator.get_importance_score()
- [ ] 實現 AJCCStageConverter.convert()
- [ ] 實現 BreastCancerStratification.stratify()
- [ ] 建立所有配置文件 (JSON)
- [ ] 編寫單元測試 (>80% 覆蓋率)
- [ ] 集成到 Flask 應用 (app.py)
- [ ] 更新 API_SPECIFICATION.md 示例
- [ ] 建立前端 UI（可選）
- [ ] 文檔：USAGE_GUIDE.md

---

## 9. 參考資源

### 論文和指南
- Dowsett et al. J Natl Cancer Inst. 2010;102(21):1618-1632
- AJCC Cancer Staging Manual 9th Edition
- St Gallen International Consensus Conference 2021
- NCCN Guidelines for Breast Cancer

### 線上工具
- PREDICT: https://www.predict.nhs.uk/
- AJCC Staging: https://cancerstaging.org/

### 計算驗證
建議與上述官方工具進行結果對比驗證

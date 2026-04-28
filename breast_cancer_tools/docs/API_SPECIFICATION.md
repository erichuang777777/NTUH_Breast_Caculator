# 乳癌分層工具 API 規格文檔

## 概覽

提供乳癌臨床決策支持的 REST API，包含：
- IHC4 Score 計算
- Predict Score 計算  
- AJCC 分期轉換
- 臨床分層決策

## 基本信息

- **Base URL**: `/api/breast-cancer`
- **版本**: v1.0
- **Content-Type**: application/json

---

## API 端點

### 1. IHC4 Score 計算

#### 端點
```
POST /api/breast-cancer/ihc4/calculate
```

#### 請求體
```json
{
  "er_score": 250,              // ER H-score (0-300) 或 IHC (0-3+)
  "pr_score": 150,              // PR H-score (0-300) 或 IHC (0-3+)
  "her2_score": 0,              // HER2 H-score (0-300) 或 IHC (0-3+)
  "ki67_percentage": 15.0,      // Ki67 百分比 (0-100)
  "age": 55,                    // 患者年齡
  "tumor_grade": 2,             // 組織學分級 (1-3) - 可選
  "tumor_size_cm": 2.5          // 腫瘤大小 (cm) - 可選
}
```

#### 響應
```json
{
  "success": true,
  "data": {
    "ihc4_score": 3.45,
    "risk_category": "Intermediate Risk",
    "prognostic_group": "good",
    "subtype": "Luminal A",
    "predict_score": 15.2,
    "endocrine_benefit": "Significant",
    "recommendation": "Hormone therapy recommended",
    "details": {
      "er_component": 0.82,
      "pr_component": 0.45,
      "her2_component": 0.0,
      "ki67_component": 0.18
    }
  }
}
```

#### 錯誤響應
```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "ER score must be between 0 and 300",
    "field": "er_score"
  }
}
```

---

### 2. Predict Score 計算

#### 端點
```
POST /api/breast-cancer/predict-score/calculate
```

#### 請求體
```json
{
  "ihc4_score": 3.45,           // IHC4 評分
  "age": 55,                    // 患者年齡
  "tumor_size_cm": 2.5,         // 腫瘤大小 (cm)
  "grade": 2,                   // 組織學分級 (1-3)
  "node_positive": true         // 淋巴結轉移
}
```

#### 響應
```json
{
  "success": true,
  "data": {
    "predict_score": 15.2,
    "recurrence_risk_10yr": "8.5%",
    "endocrine_therapy_benefit": "Significant",
    "chemotherapy_benefit": "Limited",
    "recommendations": [
      "Hormone therapy with tamoxifen or aromatase inhibitor",
      "Consider CDK4/6 inhibitor if high risk features present"
    ]
  }
}
```

---

### 3. AJCC 分期轉換

#### 端點
```
POST /api/breast-cancer/ajcc/stage
```

#### 請求體
```json
{
  "t": "T2",                    // T classification
  "n": "N1a",                   // N classification  
  "m": "M0",                    // M classification
  "grade": 2,                   // 組織學分級 (1-3)
  "er_status": "Positive",      // "Positive" 或 "Negative"
  "pr_status": "Positive",
  "her2_status": "Negative",
  "ajcc_edition": 9             // 8 或 9 (預設: 9)
}
```

#### 響應
```json
{
  "success": true,
  "data": {
    "clinical_stage": "Stage IIA",
    "prognostic_group": "G2",
    "edition": 9,
    "survival_rate_5yr": "92%",
    "treatment_recommendation": {
      "surgery": true,
      "chemotherapy": true,
      "hormone_therapy": true,
      "trastuzumab": false,
      "immunotherapy": false,
      "radiotherapy": "Consider based on tumor characteristics"
    },
    "clinical_notes": [
      "HER2-negative Luminal disease",
      "Standard risk"
    ]
  }
}
```

---

### 4. 完整臨床分層

#### 端點
```
POST /api/breast-cancer/stratification/full
```

#### 請求體
```json
{
  "biomarkers": {
    "er_h_score": 250,
    "pr_h_score": 150,
    "her2_score": 0,
    "ki67_percentage": 15.0,
    "grade": 2,
    "tumor_size_cm": 2.5,
    "lymph_node_status": "N1a",
    "metastasis": "M0",
    "age": 55
  },
  "clinical_info": {
    "patient_id": "P12345",      // 可選，用於追蹤
    "provider_name": "Dr. Smith"  // 可選
  }
}
```

#### 響應
```json
{
  "success": true,
  "data": {
    "subtype": "Luminal B-like HER2-",
    "ajcc_stage": "Stage IIA",
    "ihc4_score": 3.45,
    "predict_score": 15.2,
    "risk_category": "Intermediate Risk",
    "recommended_therapy": {
      "surgery": true,
      "chemotherapy": true,
      "hormone_therapy": true,
      "radiation": "Consider",
      "specific_drugs": [
        "Paclitaxel + Trastuzumab (if high risk)",
        "Tamoxifen or Aromatase Inhibitor",
        "CDK4/6 inhibitor for metastatic disease"
      ]
    },
    "clinical_notes": [
      "Intermediate risk, suitable for standard adjuvant therapy",
      "Consider genetic testing (BRCA, etc.)",
      "Follow-up imaging in 1 year"
    ],
    "confidence_level": 0.92
  }
}
```

---

## 數據驗證規則

### IHC 評分範圍
```
H-score 系統:
- ER/PR: 0-300
- HER2: 0-300 (或轉換為 0-3+)
- Ki67: 0-100 (百分比)

IHC 系統 (可選):
- ER: 0-3+
- PR: 0-3+
- HER2: 0-3+
```

### TNM 分類有效值
```
T: T0, T1, T1mi, T1a, T1b, T1c, T2, T3, T4, T4a, T4b, T4c, T4d, TX
N: N0, N1, N2, N3, N1mi, N1a, N2a, N2b, N3a, N3b, N3c, NX
M: M0, M1, MX
```

### 年齡限制
```
最小: 18 歲
最大: 120 歲
```

---

## 錯誤代碼

| 代碼 | 說明 | HTTP狀態 |
|------|------|---------|
| INVALID_INPUT | 輸入參數無效 | 400 |
| OUT_OF_RANGE | 參數超出範圍 | 400 |
| MISSING_REQUIRED | 缺少必需參數 | 400 |
| NOT_FOUND | 資源不存在 | 404 |
| INTERNAL_ERROR | 伺服器內部錯誤 | 500 |

---

## 使用範例

### Python + Flask
```python
import requests

url = "http://localhost:5000/api/breast-cancer/ihc4/calculate"
payload = {
    "er_score": 250,
    "pr_score": 150,
    "her2_score": 0,
    "ki67_percentage": 15.0,
    "age": 55
}

response = requests.post(url, json=payload)
result = response.json()
print(f"IHC4 Score: {result['data']['ihc4_score']}")
print(f"Risk: {result['data']['risk_category']}")
```

### cURL
```bash
curl -X POST http://localhost:5000/api/breast-cancer/ihc4/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "er_score": 250,
    "pr_score": 150,
    "her2_score": 0,
    "ki67_percentage": 15.0,
    "age": 55
  }'
```

### JavaScript/Fetch
```javascript
const payload = {
  er_score: 250,
  pr_score: 150,
  her2_score: 0,
  ki67_percentage: 15.0,
  age: 55
};

fetch('/api/breast-cancer/ihc4/calculate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(payload)
})
.then(r => r.json())
.then(data => console.log(data));
```

---

## 版本歷史

### v1.0 (2024-04)
- 初始版本
- IHC4 計算
- Predict Score 計算
- AJCC 分期轉換
- 完整臨床分層

---

## 參考文獻

1. Dowsett et al. Prediction of endocrine therapy benefit from ER and HER2 status in breast cancer. J Natl Cancer Inst. 2010.
2. AJCC Cancer Staging Manual, 8th and 9th editions
3. Goldhirsch et al. Strategies for subtypes—dealing with the diversity of breast cancer. Nat Rev Clin Oncol. 2011.

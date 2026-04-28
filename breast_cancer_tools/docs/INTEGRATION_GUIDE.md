# Flask 應用集成指南

## 概覽

如何將 `breast_cancer_tools` 模塊集成到現有的 Flask Web 應用

---

## 1. Flask 路由集成

### 在 `app/app.py` 中添加以下代碼

```python
# 在檔案頂部
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'breast_cancer_tools'))

from breast_cancer_tools import (
    IHC4Calculator,
    AJCCStageConverter,
    BreastCancerStratification
)

# 初始化工具
ihc4_calc = IHC4Calculator()
ajcc_conv = AJCCStageConverter(edition=9)
stratifier = BreastCancerStratification()

# ========== 乳癌分層工具路由 ==========

@app.route('/api/breast-cancer/ihc4/calculate', methods=['POST'])
def calculate_ihc4():
    """計算 IHC4 Score"""
    try:
        data = request.get_json()
        
        result = ihc4_calc.calculate(
            er_score=data.get('er_score'),
            pr_score=data.get('pr_score'),
            her2_score=data.get('her2_score'),
            ki67_percentage=data.get('ki67_percentage'),
            age=data.get('age'),
            tumor_grade=data.get('tumor_grade'),
            tumor_size_cm=data.get('tumor_size_cm')
        )
        
        return jsonify({
            'success': True,
            'data': {
                'ihc4_score': result.ihc4_score,
                'risk_category': result.risk_category,
                'subtype': result.subtype.value,
                'recommendation': result.recommendation
            }
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/api/breast-cancer/ajcc/stage', methods=['POST'])
def convert_ajcc():
    """轉換 AJCC 分期"""
    try:
        data = request.get_json()
        
        result = ajcc_conv.convert(
            t=data.get('t'),
            n=data.get('n'),
            m=data.get('m'),
            grade=data.get('grade'),
            er_status=data.get('er_status'),
            pr_status=data.get('pr_status'),
            her2_status=data.get('her2_status'),
            is_pathologic=data.get('is_pathologic', False)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'clinical_stage': result.clinical_stage.value,
                'prognostic_group': result.prognostic_group,
                'treatment_recommendation': result.treatment_recommendation
            }
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/breast-cancer/stratification', methods=['POST'])
def stratify_breast_cancer():
    """完整臨床分層分析"""
    try:
        data = request.get_json()
        biomarker_data = data.get('biomarkers', {})
        
        from breast_cancer_tools.stratification import BiomarkerPanel
        
        biomarker = BiomarkerPanel(
            er_h_score=biomarker_data.get('er_h_score'),
            pr_h_score=biomarker_data.get('pr_h_score'),
            her2_score=biomarker_data.get('her2_score'),
            ki67_percentage=biomarker_data.get('ki67_percentage'),
            grade=biomarker_data.get('grade'),
            tumor_size_cm=biomarker_data.get('tumor_size_cm'),
            lymph_node_status=biomarker_data.get('lymph_node_status'),
            metastasis=biomarker_data.get('metastasis'),
            age=biomarker_data.get('age')
        )
        
        result = stratifier.stratify(biomarker)
        
        return jsonify({
            'success': True,
            'data': {
                'subtype': result.subtype,
                'ajcc_stage': result.ajcc_stage,
                'ihc4_score': result.ihc4_score,
                'risk_category': result.risk_category,
                'recommended_therapy': result.recommended_therapy,
                'clinical_notes': result.clinical_notes,
                'confidence_level': result.confidence_level
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## 2. 前端集成

### 在 HTML 中添加新的分頁

```html
<!-- app/templates/index.html -->

<!-- 添加到 tabs 區域 -->
<div class="tabs">
    <button class="tab-btn active" data-tab="drugs">藥物計算</button>
    <button class="tab-btn" data-tab="trials">臨床試驗</button>
    <button class="tab-btn" data-tab="breast-cancer">乳癌分層工具</button>  <!-- 新增 -->
</div>

<!-- 乳癌分層工具內容 -->
<div id="breast-cancer-tab" class="tab-content" style="display: none;">
    <div class="section">
        <h2>乳癌臨床分層決策工具</h2>
        
        <!-- IHC 評分輸入 -->
        <div class="form-section">
            <h3>免疫組織化學評分</h3>
            <div class="form-group">
                <label>ER H-score (0-300):</label>
                <input type="number" id="erScore" min="0" max="300">
            </div>
            <div class="form-group">
                <label>PR H-score (0-300):</label>
                <input type="number" id="prScore" min="0" max="300">
            </div>
            <div class="form-group">
                <label>HER2 H-score (0-300):</label>
                <input type="number" id="her2Score" min="0" max="300">
            </div>
            <div class="form-group">
                <label>Ki67 百分比 (0-100):</label>
                <input type="number" id="ki67Percentage" min="0" max="100" step="0.1">
            </div>
        </div>
        
        <!-- 臨床信息 -->
        <div class="form-section">
            <h3>臨床信息</h3>
            <div class="form-group">
                <label>年齡:</label>
                <input type="number" id="age" min="18" max="120">
            </div>
            <div class="form-group">
                <label>組織學分級 (1-3):</label>
                <select id="grade">
                    <option>選擇...</option>
                    <option value="1">Grade 1</option>
                    <option value="2">Grade 2</option>
                    <option value="3">Grade 3</option>
                </select>
            </div>
            <div class="form-group">
                <label>腫瘤大小 (cm):</label>
                <input type="number" id="tumorSize" min="0" max="50" step="0.1">
            </div>
            <div class="form-group">
                <label>淋巴結狀態:</label>
                <select id="nodeStatus">
                    <option>選擇...</option>
                    <option value="N0">N0 - 無淋巴結轉移</option>
                    <option value="N1">N1 - 1-3 淋巴結</option>
                    <option value="N2">N2 - 4-9 淋巴結</option>
                    <option value="N3">N3 - ≥10 淋巴結</option>
                </select>
            </div>
        </div>
        
        <button onclick="analyzeBreastCancer()" class="btn-primary">進行分析</button>
        
        <!-- 結果區域 -->
        <div id="bc-results" style="display: none; margin-top: 30px;">
            <div class="result-card">
                <h3>分層結果</h3>
                <div id="bc-result-content"></div>
            </div>
        </div>
    </div>
</div>

<!-- JavaScript -->
<script>
async function analyzeBreastCancer() {
    const payload = {
        biomarkers: {
            er_h_score: parseInt(document.getElementById('erScore').value),
            pr_h_score: parseInt(document.getElementById('prScore').value),
            her2_score: parseInt(document.getElementById('her2Score').value),
            ki67_percentage: parseFloat(document.getElementById('ki67Percentage').value),
            grade: parseInt(document.getElementById('grade').value),
            tumor_size_cm: parseFloat(document.getElementById('tumorSize').value),
            lymph_node_status: document.getElementById('nodeStatus').value,
            metastasis: "M0",
            age: parseInt(document.getElementById('age').value)
        }
    };
    
    try {
        const response = await fetch('/api/breast-cancer/stratification', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayBreastCancerResults(result.data);
        } else {
            alert(`錯誤: ${result.error}`);
        }
    } catch (error) {
        console.error('分析失敗:', error);
        alert('分析失敗，請檢查輸入');
    }
}

function displayBreastCancerResults(data) {
    const resultsDiv = document.getElementById('bc-results');
    const contentDiv = document.getElementById('bc-result-content');
    
    let html = `
        <p><strong>乳癌亞型:</strong> ${data.subtype}</p>
        <p><strong>AJCC 分期:</strong> ${data.ajcc_stage}</p>
        <p><strong>IHC4 評分:</strong> ${data.ihc4_score?.toFixed(2) || 'N/A'}</p>
        <p><strong>風險類別:</strong> ${data.risk_category}</p>
        <p><strong>信心程度:</strong> ${(data.confidence_level * 100).toFixed(1)}%</p>
        
        <h4>推薦治療:</h4>
        <ul>
            ${Object.entries(data.recommended_therapy || {})
                .filter(([key, val]) => typeof val === 'boolean' && val)
                .map(([key]) => `<li>${key.replace(/_/g, ' ')}</li>`)
                .join('')}
        </ul>
        
        <h4>臨床備註:</h4>
        <ul>
            ${(data.clinical_notes || [])
                .map(note => `<li>${note}</li>`)
                .join('')}
        </ul>
    `;
    
    contentDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}
</script>
```

---

## 3. 測試 API

### 使用 cURL 測試

```bash
# 測試 IHC4 計算
curl -X POST http://localhost:5000/api/breast-cancer/ihc4/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "er_score": 250,
    "pr_score": 150,
    "her2_score": 0,
    "ki67_percentage": 15.0,
    "age": 55
  }'

# 測試完整分層
curl -X POST http://localhost:5000/api/breast-cancer/stratification \
  -H "Content-Type: application/json" \
  -d '{
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
    }
  }'
```

---

## 4. 錯誤處理

確保實現合適的錯誤處理：

```python
class ValidationError(Exception):
    """輸入驗證錯誤"""
    pass

class CalculationError(Exception):
    """計算錯誤"""
    pass

@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({
        'success': False,
        'error': str(e),
        'error_code': 'VALIDATION_ERROR'
    }), 400
```

---

## 5. 性能優化

### 緩存計算結果

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_ihc4_calculation(er, pr, her2, ki67, age):
    """緩存 IHC4 計算結果"""
    return ihc4_calc.calculate(er, pr, her2, ki67, age)
```

### 非同步計算（可選）

```python
from threading import Thread
import queue

def async_stratification(biomarker, callback):
    """在後台線程中進行分層"""
    def worker():
        result = stratifier.stratify(biomarker)
        callback(result)
    
    thread = Thread(target=worker, daemon=True)
    thread.start()
```

---

## 6. 部署檢查清單

- [ ] 所有計算邏輯已實現
- [ ] API 端點已集成到 Flask 應用
- [ ] 前端 UI 已添加
- [ ] 單元測試通過 (>80% 覆蓋率)
- [ ] 集成測試通過
- [ ] 錯誤處理完整
- [ ] 性能測試合格
- [ ] 文檔已更新
- [ ] 提交到 GitHub

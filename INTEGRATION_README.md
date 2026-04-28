# NHI 藥品計算 + 臨床試驗分析整合

## 🎯 項目概述

這是一個將 **臨床試驗分析功能** 與你的 **NHI_Drug_Calculator** 項目整合的完整方案。

### 新增功能
- ✅ 乳癌臨床試驗分析
- ✅ 血液科臨床試驗分析  
- ✅ 患者版和醫師版統一 Web 界面（Tab 頁切換）
- ✅ 與 ClinicalTrials.gov API 實時同步
- ✅ 試驗重要程度評分系統

## 📁 項目結構

```
NHI_Drug_Calculator/
├── app/
│   ├── app.py                 # Flask 應用主程序
│   └── templates/
│       └── index.html         # Web UI 界面（患者版 + 醫師版）
├── clinical_trials_lib/
│   ├── clinical_trials_core.py # 臨床試驗分析核心引擎
│   └── __init__.py
├── run.py                      # 啟動腳本
├── requirements.txt            # Python 依賴
├── INTEGRATION_README.md       # 本文件
└── (你的原有代碼...)
```

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 運行應用

```bash
python run.py
```

或者直接運行 Flask：

```bash
python -m flask --app app.app run
```

### 3. 訪問應用

打開瀏覽器，訪問：
```
http://localhost:5000
```

## 🎨 用戶界面特點

### 統一的分頁設計

**左側 Tab 菜單**:
- 👥 患者版 - 只顯示正在招募的試驗，包含聯絡方式
- 👨‍⚕️ 醫師版 - 顯示全球試驗評分和排名

**控制條**:
- 科室選擇：乳癌 / 血液科
- 位置搜索：默認台灣，可修改
- 重新載入按鈕

### 患者版特點
- 只顯示 "正在招募中" 的試驗
- 聯絡人、電話、Email 直接顯示
- 清晰的地點信息
- 直接連結到 ClinicalTrials.gov

### 醫師版特點
- 試驗統計 (Phase 分佈、已發表結果、已終止等)
- 重要程度評分 (🔴🟠🟡🟢)
- 詳細的試驗信息
- 評分理由說明
- 前 10 最重要試驗展示

## 📊 API 端點

### 獲取試驗數據
```
GET /api/trials/<specialty>?location=Taiwan
```

**參數**:
- `specialty`: `breast` 或 `hematology`
- `location`: 位置（可選，默認 Taiwan）
- `refresh`: `true` 強制刷新緩存

**響應示例**:
```json
{
  "specialty": "breast",
  "location": "Taiwan",
  "total_count": 100,
  "trials": [...],
  "statistics": {
    "phase1": 20,
    "phase2": 26,
    "phase3": 32,
    "with_results": 31,
    "recruiting": 19,
    "terminated": 11
  }
}
```

### 患者視圖
```
GET /api/patient-view/<specialty>?location=Taiwan
```

只返回正在招募的試驗。

### 醫師視圖
```
GET /api/doctor-view/<specialty>?location=Taiwan
```

返回前 10 個最重要的試驗。

### 健康檢查
```
GET /api/health
```

```json
{
  "status": "ok",
  "version": "1.0.0",
  "supported_specialties": ["breast", "hematology"]
}
```

## 🔗 與現有代碼整合

### 方案 1: 保持獨立，通過 iframe 嵌入

在你的現有頁面中：
```html
<iframe src="http://localhost:5000" style="width: 100%; height: 600px;"></iframe>
```

### 方案 2: 統一 Flask 應用

1. 複製 `app/` 和 `clinical_trials_lib/` 到你的項目
2. 在你現有的 Flask 應用中導入：

```python
from app import app as clinical_trials_app

# 註冊藍圖或路由
@app.route('/trials')
def trials():
    return render_template('trials/index.html')
```

### 方案 3: 作為 API 服務

運行獨立的 Flask 應用（推薦）：
```bash
python run.py  # 在 5000 端口
```

從你的前端調用 API：
```javascript
fetch('http://localhost:5000/api/trials/breast')
  .then(r => r.json())
  .then(data => console.log(data))
```

## 📈 試驗評分標準

### 乳癌評分
| 因素 | 分數 | 說明 |
|------|------|------|
| Phase 3 | +30 | 關鍵性試驗 |
| 10+ 國家 | +20 | 全球試驗 |
| 20+ 地點 | +15 | 大規模試驗 |
| 已發表結果 | +20 | 有發表數據 |
| 正在招募 | +15 | 活躍試驗 |
| 已完成 | +5 | 已完成並發表 |

### 血液科評分
| 因素 | 分數 | 說明 |
|------|------|------|
| Phase 3 | +30 | 關鍵性試驗 |
| Phase 2 | +10 | 臨床評估 |
| 10+ 國家 | +20 | 全球試驗 |
| 500+ 人入組 | +15 | 大規模 |
| 200-499 人 | +10 | 中等規模 |
| 已發表結果 | +20 | 有發表數據 |
| 正在招募 | +15 | 活躍試驗 |

## 🔄 數據更新

### 緩存機制

試驗數據會被緩存以提高性能。要強制更新：

```
GET /api/trials/breast?refresh=true
```

### 自動更新 (可選)

使用 APScheduler 定期更新：

```python
from apscheduler.schedulers.background import BackgroundScheduler

def refresh_trials():
    # 重新獲取數據
    pass

scheduler = BackgroundScheduler()
scheduler.add_job(refresh_trials, 'cron', hour=0)
scheduler.start()
```

## 🛠️ 自訂化

### 修改評分權重

編輯 `clinical_trials_lib/clinical_trials_core.py`：

```python
def get_importance_score(self, trial: Dict) -> Tuple[int, List[str]]:
    score = 0
    reasons = []
    
    if 'PHASE3' in trial['phases']:
        score += 40  # 增加權重
        reasons.append("✅ Phase 3")
    # ...
```

### 修改 UI 樣式

編輯 `app/templates/index.html` 中的 `<style>` 部分。

### 添加新科室

在 `clinical_trials_lib/clinical_trials_core.py` 中：

```python
class OncologyAnalyzer(SpecialtyAnalyzer):
    def __init__(self, location: str = "Taiwan"):
        super().__init__(location)
        self.specialty_name = "腫瘤科"
    
    def get_importance_score(self, trial: Dict) -> Tuple[int, List[str]]:
        # 實現腫瘤科評分邏輯
        pass
```

然後在 `app/app.py` 中註冊：

```python
from clinical_trials_core import OncologyAnalyzer

oncology_analyzer = OncologyAnalyzer()

@app.route('/api/trials/oncology')
def get_trials_oncology():
    # 實現腫瘤科邏輯
    pass
```

## 📱 響應式設計

應用程序完全響應式，支持：
- 💻 桌面 (1400px+)
- 📱 平板 (768px - 1400px)  
- 📱 手機 (< 768px)

## 🔐 安全性考慮

### CORS 配置

目前啟用了 CORS。生產環境中應該限制：

```python
from flask_cors import CORS

CORS(app, origins=["https://yourdomain.com"])
```

### 速率限制 (可選)

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/api/trials/<specialty>')
@limiter.limit("100 per hour")
def get_trials(specialty):
    pass
```

## 🐛 故障排除

### 問題：API 超時

**解決方案**:
```python
response = requests.get(url, timeout=60)  # 增加超時
```

### 問題：CORS 錯誤

確保在 `app.py` 中啟用 CORS：
```python
from flask_cors import CORS
CORS(app)
```

### 問題：無法連接到 ClinicalTrials.gov

檢查網絡連接和 API 是否可用：
```bash
curl https://clinicaltrials.gov/api/v2/studies
```

## 📚 文檔

- `app.py` - Flask 應用和 API 端點
- `clinical_trials_core.py` - 分析引擎
- `templates/index.html` - 前端界面

## 🚀 部署

### 本地開發
```bash
python run.py
```

### Heroku 部署

1. 創建 `Procfile`:
```
web: python run.py
```

2. 部署:
```bash
heroku create your-app-name
git push heroku main
heroku logs --tail
```

### Docker 部署

創建 `Dockerfile`:
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

構建和運行：
```bash
docker build -t nhi-trials .
docker run -p 5000:5000 nhi-trials
```

## 📝 許可證

MIT License

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 💬 聯絡方式

如有問題，請提出 Issue 或聯絡開發團隊。

---

**版本**: 1.0.0  
**最後更新**: 2026-04-02  
**狀態**: ✅ 生產就緒

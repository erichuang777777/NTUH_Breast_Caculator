# 架構設計 — NTUH Breast Calculator

> 模組化重構藍圖。實作分階段進行，預計 2-3 個 session。

---

## 目前現況問題

- `index.html` 已 **530KB 單一檔案**（含 CSS/HTML/JS 全部 inline）
- 9 個功能模組（landing/breast/inpatient/icd/surgery/trials/AJCC/calculator/workspace）緊密耦合
- 修一處要在 5000 行裡找
- 加新模組要小心污染既有功能
- Diff 不易閱讀，code review 困難
- 無法做單元測試

## 目標架構

```
D:\NHI_Drug_Caculator\
├── src/
│   ├── core/
│   │   ├── state.js              # _patient global state, localStorage
│   │   ├── router.js             # show* functions 集中管理
│   │   ├── flags.js              # FEATURE_FLAGS 系統
│   │   ├── ui.js                 # 共用 UI helpers (Modal, Toast)
│   │   └── dark-mode.js
│   ├── modules/
│   │   ├── breast/
│   │   │   ├── breast.html       # HTML 片段
│   │   │   ├── breast.css        # module-specific styles
│   │   │   └── breast.js         # filterBreast, openDetail, etc.
│   │   ├── inpatient/
│   │   │   ├── inpatient.html
│   │   │   ├── inpatient.css
│   │   │   └── inpatient.js      # INP_REGIMENS, calcInpDose, etc.
│   │   ├── icd/
│   │   │   ├── icd.html
│   │   │   ├── icd.css
│   │   │   └── icd.js            # ICD_BY_QUAD lookup, selectIcdZone
│   │   ├── surgery/
│   │   │   ├── surgery.html
│   │   │   ├── surgery.css
│   │   │   └── surgery.js        # SURGERY_ITEMS, surg total
│   │   ├── trials/
│   │   │   ├── trials.html
│   │   │   ├── trials.js         # searchTrials, exportTrialsCSV
│   │   │   └── trials.css
│   │   ├── ajcc/
│   │   │   ├── ajcc.html
│   │   │   ├── ajcc.js           # _ajccAnatomic, calcAJCC, setAJCCMode
│   │   │   └── ajcc.css
│   │   ├── calculator/
│   │   │   ├── calculator.html   # tabs container
│   │   │   ├── calculator.css
│   │   │   ├── predict.js        # PREDICT v2.3 / v4.0
│   │   │   ├── cts5.js
│   │   │   ├── pepi.js
│   │   │   ├── npi.js
│   │   │   ├── magee.js
│   │   │   ├── ihc4.js
│   │   │   ├── hscore.js
│   │   │   ├── rcb.js
│   │   │   └── gail.js
│   │   └── workspace/
│   │       ├── workspace.html
│   │       ├── workspace.js      # _patient state, refreshDerived
│   │       ├── workspace.css
│   │       └── nhi-lookup.js     # NHI 給付反向查詢
│   └── data/                     # static data (drug lists, ICD codes)
│       ├── drugs.json            # 從 SQLite 匯出
│       ├── icd-lookup.json
│       └── inp-regimens.json
├── public/                       # 靜態資產
├── tests/                        # 測試
│   ├── predict_validation.html   # PREDICT 對照 NHS 官方
│   ├── ajcc_test.js              # AJCC 期別測試
│   └── calculators_test.js       # CTS5/PEPI/Magee/etc 測試
├── build.py                      # 取代 build_static.py
├── nhi_drug_coverage.db
├── netlify.toml
└── DEVELOPMENT.md
```

## 重構步驟

### Phase 1（第 1 session）— 基礎設施
1. 建 `src/core/` 目錄
2. 抽出 `flags.js`、`dark-mode.js`、`state.js`、`router.js`
3. 改寫 `build.py`：concat 所有 module 檔案 → 注入 `index.html` template
4. 確保 build 後與目前 index.html 等價（regression test）

### Phase 2（第 2 session）— Calculator 拆分
1. 抽出每個 calculator (`predict.js`, `cts5.js`, ...) 到獨立檔案
2. 抽出 `calculator.html` template
3. Build 階段組合
4. 驗證所有 9 個 calculator 仍可運作

### Phase 3（第 3 session）— 其他模組
1. AJCC, Workspace（最複雜）
2. Breast, Inpatient
3. ICD, Surgery, Trials

### Phase 4（第 4 session）— 收尾
1. 移除 `index.html` 直接編輯（只能改 template）
2. 加入 watch script（檔案改自動重 build）
3. 加入單元測試 CI

## Build 流程設計

```python
# build.py（新版）
import json, re
from pathlib import Path

SRC = Path('src')
TEMPLATE = SRC / 'index.template.html'
OUT = Path('index.html')

def collect_css():
    """合併所有 .css 檔"""
    css = ''
    for path in sorted(SRC.glob('**/*.css')):
        css += f'/* === {path.name} === */\n' + path.read_text() + '\n'
    return css

def collect_js():
    """按依賴順序合併 .js 檔"""
    order = [
        'core/flags.js',          # 先 init flags
        'core/state.js',
        'core/dark-mode.js',
        'core/ui.js',
        'core/router.js',
        'modules/**/*.js',        # modules 之間互不依賴
    ]
    js = ''
    for pattern in order:
        for path in sorted(SRC.glob(pattern)):
            js += f'// === {path.name} ===\n' + path.read_text() + '\n'
    return js

def collect_html_panels():
    """合併所有 module HTML 片段"""
    panels = ''
    for path in sorted(SRC.glob('modules/*/[!_]*.html')):
        panels += path.read_text() + '\n'
    return panels

def build():
    template = TEMPLATE.read_text()
    out = template
    out = out.replace('<!--{{CSS}}-->', f'<style>{collect_css()}</style>')
    out = out.replace('<!--{{HTML_PANELS}}-->', collect_html_panels())
    out = out.replace('<!--{{JS}}-->', f'<script>{collect_js()}</script>')
    # Inject SQLite drug data
    out = inject_drug_data(out)
    OUT.write_text(out)
    print(f'OK: {len(out):,} chars → index.html')

if __name__ == '__main__':
    build()
```

`src/index.template.html`:

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>乳癌小幫手</title>
    <!--{{CSS}}-->
</head>
<body>
    <div id="app">
        <div id="landingPage"></div>
        <!--{{HTML_PANELS}}-->
    </div>
    <!--{{JS}}-->
</body>
</html>
```

## 模組之間依賴管理

每個模組 export 一個 init 函數：

```javascript
// src/modules/calculator/calculator.js
window.CalculatorModule = {
    init() {
        // wire up event listeners
        // call sub-calculators init
        if (window.CalculatorModule.Predict) window.CalculatorModule.Predict.init();
        if (window.CalculatorModule.CTS5) window.CalculatorModule.CTS5.init();
        // ...
    },
    show() {
        document.getElementById('calcPage').classList.add('active');
        this.init();
    },
    hide() {
        document.getElementById('calcPage').classList.remove('active');
    }
};
```

## 共用 state 抽取

所有跨模組共用的狀態移到 `core/state.js`：

```javascript
// src/core/state.js
window.AppState = {
    patient: {},     // workspace state
    flags: {},       // feature flags
    drugs: [],       // drug list
    formulations: [],
    
    load() { /* load from localStorage */ },
    save() { /* save to localStorage */ },
    onPatientChange(callback) { /* event bus */ }
};
```

## 測試策略

每個 calculator 在自己的 `.js` 檔尾段加：

```javascript
// 自我測試（development only）
if (typeof TEST !== 'undefined' && TEST) {
    console.assert(calcCTS5_pure(0, 20, 2, 55) === ..., 'CTS5 baseline');
    // ...
}
```

Build 時可加 `?test=1` URL param 啟動測試模式。

## 下次 session 起點

1. 開新 branch: `git checkout -b refactor/modularize`
2. 從 `src/core/flags.js` 開始抽出（最獨立）
3. 寫初版 `build.py`，跑一次驗證 output 等於目前 index.html
4. 進入 Phase 1 流程

## 暫時的 workaround（在重構完成前）

- 加新功能時用 `// === MODULE: X ===` 註解標出邊界
- 不要在 PR 中混雜多個模組的改動
- 每次 push 前都 `node --check` 驗證 JS syntax

---

*最後更新：2026-05-09*

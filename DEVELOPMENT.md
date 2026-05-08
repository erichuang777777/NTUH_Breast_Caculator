# 開發指南 — NTUH Breast Calculator

> 給開發者與維護者的工作流程文件。每次新功能上線前請複習一次。

---

## 1. 專案結構

```
D:\NHI_Drug_Caculator\
├── index.html                      ← 線上靜態版本（Netlify 部署）
├── NP_dashboard/
│   └── NHI Drug Calculator.html    ← 開發模板（build_static.py 從這裡產生 index.html）
├── nccn_viewer.html                ← NCCN 治療指引獨立 viewer
├── data/                           ← 執行期資料
│   ├── ajcc_lookup.json
│   ├── viz_data.json               (NCCN 視覺化資料)
│   ├── flowcharts.json             (29 個 BINV 流程圖)
│   ├── page_index.json
│   ├── cross_references.json
│   └── references.json
├── breast_cancer_tools/            ← Python 模組（IHC4/AJCC/Stratification）
├── specialties/breast/             ← 模組化重構版 Python
├── clinical_trials_lib/            ← 臨床試驗 Python 庫
├── core/                           ← Specialty loader
├── app/                            ← Flask web 整合 app
├── tests/                          ← Python 測試
├── build_static.py                 ← 從 template 產生 index.html
├── web_app.py                      ← Flask backend（local dev）
├── nhi_drug_coverage.db            ← SQLite 健保藥物資料
└── DEVELOPMENT.md                  ← 你正在看的這份
```

---

## 2. Git 分支策略（保護線上版本）

### 規則

```
master      ← 線上正式版（Netlify auto-deploy；永遠是可用的）
  ↑
develop     ← 開發整合版（給自己 / 同事測試用）
  ↑
feature/*   ← 個別功能分支（一個 feature 一個 branch）
```

### 工作流程

```bash
# 開新功能
git checkout develop
git pull origin develop
git checkout -b feature/my-new-thing

# 開發 ... commit ...

# 整合到 develop
git checkout develop
git merge feature/my-new-thing
git push origin develop
# → 在 Netlify 預覽 URL 確認沒壞

# 測試 OK 後上線
git checkout master
git merge develop
git tag -a v1.x -m "新版說明"
git push origin master --tags
# → Netlify 自動部署 master
```

### 黃金規則

- **master 不能直接 commit**：所有變更從 develop merge 進來
- **每次 merge 進 master 前必須在 develop 預覽 URL 確認過**
- **重大 release 一定打 tag**（`v1.0`, `v1.1`...）萬一壞了可以 rollback
- **緊急 hotfix**：可以從 master 開 `hotfix/*` branch，修完直接 merge 回 master 並 cherry-pick 回 develop

---

## 3. Netlify Branch Deploys（啟用步驟）

每個 branch 自動有獨立預覽 URL，給自己/同事測試用。

### 啟用

1. 登入 Netlify → 進入 NTUH_Breast_Caculator 站台
2. **Site settings → Build & deploy → Continuous deployment → Branches**
3. **Branch deploys**: 改成 "All" 或 "Let me add individual branches"
4. **Deploy previews**: 啟用（PR 自動產生預覽）

### 結果

```
master          → https://ntuh-breast-caculator.netlify.app          (正式版)
develop         → https://develop--ntuh-breast-caculator.netlify.app (開發版)
feature/predict → https://feature-predict--ntuh-breast-caculator.netlify.app
```

把 develop 預覽 URL 給同事測試，不影響正式版。

---

## 4. Feature Flags（網頁內功能開關）

### 設計

每個功能都有開關，存在 `localStorage._feature_flags`。使用者可以在網頁右下角齒輪 ⚙ 開啟/關閉。

### 兩種模式

| 模式 | Beta 功能 | 用途 |
|---|---|---|
| **正式版 (Stable)** | 全部關閉 | 給病人/同事看的版本，只顯示已驗證功能 |
| **開發版 (Beta)** | 全部開啟 | 開發者 / 內測用 |

### 啟用方式（讓同事看到實驗功能）

**方法 1：齒輪設定**
- 齒輪 ⚙ → 切「開發版」 → 自動開啟所有 Beta 功能

**方法 2：URL 參數**
- 在網址後加 `?dev=1` → 一鍵啟用所有功能（一次性，需自己存到 localStorage 才會持續）
- 加 `?stable=1` → 強制只顯示穩定功能

### 加新功能時的步驟

```javascript
// 1. 在 FEATURE_FLAGS_DEFAULT 加入新 flag
const FEATURE_FLAGS_DEFAULT = {
    ...,
    myNewFeature: true,        // 預設開啟
};

// 2. 如果是 Beta，加到 FEATURE_FLAGS_BETA_KEYS
const FEATURE_FLAGS_BETA_KEYS = [..., 'myNewFeature'];

// 3. 在 renderSettings() 的 flags 陣列加描述
{key:'myNewFeature', label:'新功能名稱', stable:false, note:'尚未驗證...'}

// 4. 在程式碼中用 flag 包起來
if(FEATURE_FLAGS.myNewFeature){
    // show / enable feature
}

// 5. 在 loadLanding() 對應 dept-card 加 flag
if(F.myNewFeature) html += `<div class="dept-card ...">...</div>`;
```

### 目前的 Beta 功能（預設開啟，但同事可關掉測穩定版體驗）

- **PREDICT v2.3** — 存活率估算可能與 NHS 官方有 ±5% 誤差
- **AJCC 預後期別** — 簡化估算
- **健保給付反向查詢** — 給付規則需驗證

---

## 5. 版本管理（Tag / Release）

### Tag 命名

```
v1.0    初版（基礎乳癌藥物 + 住院化療）
v1.1    費用比較表 + 病患摘要列印
v1.2    PREDICT v2.3 + Workspace + Calculator + AJCC + NCCN  ← 目前
v1.x    下一版
```

### 打 tag 的步驟

```bash
# 在 master 上
git tag -a v1.3 -m "新增 XXX 功能 + 修正 YYY"
git push origin v1.3

# 列出所有 tag
git tag -l

# 看某個 tag 的詳細
git show v1.2
```

### Rollback（線上壞掉時）

```bash
# 方法 1: 從 Netlify 後台一鍵 rollback（推薦）
# Netlify → Deploys → 找到舊版 → "Publish deploy"

# 方法 2: 用 git 回到舊版
git checkout master
git reset --hard v1.1   # 危險：會丟失之後的 commit
git push --force origin master   # 更危險

# 方法 3: 用 revert（保留歷史，安全）
git revert <bad-commit-sha>
git push origin master
```

---

## 6. 部署流程（Netlify）

### 自動部署（已設定）

`master` 分支有任何 push → Netlify 自動建置並部署到正式 URL。

### 手動部署（緊急用）

1. 本地：`python build_static.py`（如果改了 template）
2. Netlify → Deploys → "Trigger deploy" → "Deploy site"

### `netlify.toml` 設定（已有）

```toml
[build]
  publish = "."
```

### 環境變數（如果需要）

Netlify → Site settings → Build & deploy → Environment

---

## 7. build_static.py 流程

從 `NP_dashboard/NHI Drug Calculator.html`（template）+ `nhi_drug_coverage.db`（SQLite）→ 產生 `index.html`。

### 兩個檔案的關係

- **template** (`NP_dashboard/NHI Drug Calculator.html`)：完整版（含 fetch API 呼叫）
- **index.html**：static 版（fetch 換成 alert read-only）

### 同步原則

由於我們手動編輯了 `index.html`，目前的策略是 **每次 push 前都把 index.html 複製回 template**：

```powershell
Copy-Item D:\NHI_Drug_Caculator\index.html "D:\NHI_Drug_Caculator\NP_dashboard\NHI Drug Calculator.html" -Force
```

下次跑 `python build_static.py` 時，所有 transform 都是 idempotent，只會刷新 SQLite 藥物資料區塊。

---

## 8. Code Review Checklist（push 前自查）

### 必查

- [ ] 沒有 `console.log` 殘留
- [ ] 沒有 hardcoded 病人資料 / API key
- [ ] 新功能有用 `FEATURE_FLAGS` 包起來（如果是實驗性）
- [ ] 改過 `index.html` 後**已同步到 template**
- [ ] 本地用瀏覽器試過所有相關分頁
- [ ] localStorage 寫入有 try/catch
- [ ] 手機 viewport 顯示 OK（Chrome DevTools mobile mode）

### 加分項

- [ ] Dark mode 視覺也 OK
- [ ] `?dev=1` URL 也測過
- [ ] 改 calculator 公式時加了 citation
- [ ] 加新 dept-card 時 9 個 `show*` 函式都有 hide 它

---

## 9. 給同事測試的 SOP

當你開發了新功能想找同事幫忙測：

1. **不要直接推到 master**
2. 推到 `develop` 或 `feature/xxx` branch
3. 在 Netlify 拿到該 branch 的預覽 URL
4. 把 URL 給同事，並告訴他們：
   - 點右下角齒輪 ⚙ → 切「開發版 (Beta)」
   - 或網址後加 `?dev=1`
   - 試完請回報遇到的問題
5. 改完之後 → develop merge 回 master → 上線

---

## 10. 緊急聯絡

- 系統壞掉：Netlify Dashboard 一鍵 rollback 到上一個 deploy
- Git 操作不確定：先 `git stash` 保存 working changes，再實驗
- 寫死了 main：用 `git reflog` 找回 commit

---

## 11. 已知技術債

- `index.html` 仍是單一 480KB+ 檔案（未模組化）— 下次重構目標：拆 `src/modules/`
- Template 與 `index.html` 需手動同步（沒有自動 watch script）
- 沒有自動化測試（Playwright / Jest 都沒設定）
- Build 流程依賴本地 SQLite DB，CI 環境難重現

---

*最後更新：2026-05-09*

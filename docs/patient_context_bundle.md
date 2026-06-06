# Patient Context Bundle

Workspace 的 `Export structured data` 會輸出：

`onco_breast_patient_context_bundle.v1`

這份 JSON 是病人單一時間點 snapshot，可用於：

- 術前先填部分資料，術後再 import 回來補齊。
- 病理/手術紀錄解析後自動帶入欄位，再由人工確認。
- 未來接病人資料庫時，依 `patient_id` / `encounter_id` 載入最新 draft。
- 匯入病歷系統前，作為結構化資料交換格式。

主要欄位：

- `patient_context`: 使用者填寫或由解析器帶入的原始欄位。
- `derived.stage`: T/N/M、AJCC 解剖期別、預後期別與缺漏項。
- `derived.subtype`: 依 ER/PR/HER2/Ki-67 判讀的乳癌亞型。
- `derived.support`: 單一切點 decision support，包括候選治療、給付提醒、evidence block。
- `derived.scores`: PREDICT、CTS5、IHC4、Oncotype RS 等摘要。
- `derived.breast_drug_filter`: 乳癌藥物篩選條件與匹配數。
- `derived.trial_keyword`: 臨床試驗搜尋關鍵字。
- `derived.support_resources`: 社福、補助、贈藥、保險提醒摘要。

Import 同時支援新版 bundle 與舊版純 `_patient` JSON。若匯入新版 bundle，系統只會取 `patient_context` 回填，`derived` 會在本機重新計算。

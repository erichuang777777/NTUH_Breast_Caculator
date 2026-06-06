# 社福/補助/贈藥資料維護

Workspace 的「社福/補助/贈藥」卡片讀取：

`data/support_resources.json`

新增或更新項目時，請以 PR 修改這個 JSON 檔。每筆資料建議包含：

- `id`: 穩定英文代碼，請勿重複。
- `category`: 類別，例如 `勞保/請假`、`基金會/篩檢補助`、`贈藥/藥費協助`、`商業保險`。
- `title`: 卡片上顯示的名稱。
- `scope`: 適用範圍或提醒。
- `patient_timing`: 觸發時機，可用 `diagnosis`、`post_op`、`hospitalization`、`systemic_treatment`、`active_treatment`。
- `required_docs`: 常見需要文件。
- `owner`: 院內負責確認窗口。
- `status`: 建議用 `needs_local_verification`、`needs_current_program`、`patient_specific`。

這份資料只作為臨床工作區提醒，不作為資格判定。正式申請仍需由社工、個管師、保險窗口或方案窗口確認。

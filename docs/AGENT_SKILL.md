# OncoBreast Calculator Agent Skill

Version: v1.9
Audience: clinical decision-support agents, hospital workflow agents, and frontend copilots.
Deployment target: static Netlify site with read-only Netlify Functions.

## Purpose

OncoBreast Calculator is a single-timepoint breast cancer care copilot. It helps clinicians assemble a structured patient context and call small decision-support tools for:

- Breast cancer stage and subtype context.
- NHI breast drug lookup and reimbursement-oriented filtering.
- Common chemotherapy/targeted regimen and dose summaries.
- PREDICT v2.3/v3-style display, IHC4, CTS5, PEPI, NPI, Magee-style estimates, RCB, and non-SLN risk tools where fields are available.
- ICD/catastrophic illness card notes.
- Clinical trial summary cards.
- Care-support resources such as labor insurance, catastrophic illness certificate, foundation subsidy, patient assistance programs, and private insurance reminders.
- Pathology report beta extraction into editable patient context fields.
- Export/import of a patient context bundle for later EMR or database integration.

This skill is not a replacement for clinical judgment, institutional policy, official guideline text, or payer authorization review.

## Current Runtime Model

The in-page AI Agent calls an agent gateway first, then falls back to local rules if the gateway is unavailable.

- Local demo behavior: on `127.0.0.1` or `localhost`, the frontend automatically calls `/api/agent`.
- Local gateway: `web_app.py` proxies `/api/agent` to Ollama.
- Default local model: `gemma4:31b-cloud`.
- Local fallback: keyword/regex matching, tool opening, and fixed clinical helper replies.
- External behavior: the frontend can call a configured agent API endpoint and pass patient context, derived results, report text, and a tool registry.
- Netlify production API: read-only data and calculator endpoints are available under `/api/*`.
- Patient data persistence: not implemented in Netlify. Use an authenticated hospital backend for patient database, EMR write-back, admin updates, or PHI workflows.

## System Prompt Ownership

If the site is wrapped as an API, the system prompt should live in the server-side agent gateway, not in frontend code.

Recommended split:

- Frontend sends: user message, patient context, derived results, report text, and tool registry.
- Agent gateway owns: system prompt, model choice, guardrails, API keys, source policy, tool-calling rules, and logging/rate limits.
- Agent gateway should execute internal tools before asking the model to answer: field extraction, staging calculation, risk-score calculation, drug search, and formulation lookup.
- Model returns: `reply` and optional `tool_id`.
- Ordinary clinical questions should be answered in text. Use `tool_id` only when the user explicitly asks to open/call/show a tool.

The current local system prompt is implemented in `web_app.py` inside the `/api/agent` handler. For Netlify production, move the same policy into a Netlify Function or authenticated hospital backend.

## Natural Language Starters

Agents may present these as clickable prompt suggestions:

- 請只依左側 Patient Context 查詢這個病人的可用藥物。
- 請只依左側 Patient Context 判斷這個病人的 AJCC 分期。
- 我貼上病理報告後可以抽取哪些欄位？

## Tool Registry

Use `tool_id` to request the frontend to open a specific widget or page.

| tool_id | Label | Typical user intent |
|---|---|---|
| `wsPage` | 分期與亞型 | stage, subtype, patient context, pathology extraction |
| `breastPage` | 乳癌藥物 | drug eligibility, reimbursement, HER2/ER-related drug lookup |
| `inpatientPage` | 常用配方與劑量 | chemotherapy, targeted therapy, regimen, dose |
| `icdPage` | 重卡/ICD | catastrophic illness card, ICD, hospital internal number |
| `trialsPage` | 臨床試驗 | clinical trials and matching summary |
| `calcPage` | PREDICT | PREDICT v2.3/v3 display and survival benefit summary |
| `ihc4Page` | IHC4 | IHC4 score summary |
| `cts5Page` | CTS5 | late recurrence score summary |
| `pepiPage` | PEPI | post-neoadjuvant endocrine prognostic index |
| `supportResources` | 照護支持 | insurance, subsidy, patient assistance, foundation resources |
| `apiPage` | API Guide | endpoint documentation and browser smoke test |

## External Agent Request Contract

When an external agent endpoint is configured, the frontend posts this payload:

```json
{
  "message": "HER2 陽性 LN 轉移病人有哪些藥可以用？",
  "patient_context": {
    "age": 49,
    "cT": "T2",
    "cN": "N1",
    "cM": "M0",
    "er": "+",
    "pr": "+",
    "her2": "+",
    "ki67": 20
  },
  "derived": {
    "stage": {},
    "subtype": "HR+/HER2+",
    "missing": [],
    "phase_label": "single-timepoint workspace"
  },
  "report_text": "optional pasted pathology report text",
  "tool_registry": [
    { "id": "breastPage", "label": "乳癌藥物", "aliases": ["藥物", "乳癌藥物", "健保藥物", "給付"] }
  ],
  "client": {
    "app": "OncoBreast Calculator",
    "version": "v1.9"
  }
}
```

Expected response:

```json
{
  "reply": "已開啟乳癌藥物查詢。HER2-directed therapy 需依 early/metastatic、治療線別、事前審查與健保條件確認。",
  "tool_id": "",
  "patient_patch": {},
  "citations": [{ "source": "nhi_drug_coverage.db", "id": "drug:123", "title": "Trastuzumab" }],
  "called_tools": ["drug-search", "formulation-lookup"]
}
```

`tool_id` is optional. If supplied and valid, the frontend opens that tool only for explicit open/call/show commands. For ordinary questions, return a direct answer and leave `tool_id` empty.

For free-text extraction, return candidate fields in `patient_patch`; the frontend shows a confirmation button before writing them into Patient Context:

```json
{
  "reply": "我抓到 T2N1M0、ER/PR 陽性、HER2 陽性與 Ki-67 20%，請人工確認後套用。",
  "tool_id": "",
  "patient_patch": {
    "cT": "T2",
    "cN": "N1",
    "cM": "M0",
    "er": "+",
    "pr": "+",
    "her2": "+",
    "ki67": "20"
  },
  "citations": []
}
```

## Browser Configuration For External Agent

For localhost demo, no browser configuration is required. The app automatically calls:

```http
POST /api/agent
```

To override the endpoint during development, configure the browser:

```js
localStorage.setItem("nhi_dashboard_agent_api_config", JSON.stringify({
  enabled: true,
  endpoint: "/api/agent",
  headers: { "x-contact-email": "team@example.org" }
}));
```

Production recommendation: make `/api/agent` a Netlify Function or hospital backend endpoint. Keep API keys in server-side environment variables, not frontend code or localStorage.

Local Ollama settings:

```powershell
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "gemma4:31b-cloud"
python web_app.py --port 8080
```

## Public Netlify API

Available read-only endpoints:

```http
GET  /api/health
GET  /api/config
GET  /api/stats
GET  /api/drugs?category=oncology_breast
GET  /api/drug/:id
GET  /api/formulations?drug=trastuzumab
POST /api/calculate/risk-scores
POST /api/calculate/staging-score
```

Recommended public request headers:

```http
X-Contact-Email: team@example.org
X-Client-App: hospital-agent-dev
```

Example:

```bash
curl -X POST https://your-site.netlify.app/api/calculate/staging-score \
  -H "content-type: application/json" \
  -H "x-contact-email: team@example.org" \
  -H "x-client-app: hospital-agent-dev" \
  -d "{\"age\":55,\"size_mm\":20,\"grade\":2,\"nodes_pos\":1,\"cT\":\"T2\",\"cN\":\"N1\",\"cM\":\"M0\",\"er_hscore\":270,\"pr_hscore\":200,\"her2\":\"+\",\"ki67\":20}"
```

## Patient Context Bundle

The site can export a structured JSON snapshot:

```json
{
  "schema": "onco_breast_patient_context_bundle.v1",
  "patient_id": "",
  "encounter_id": "",
  "patient_context": {},
  "derived": {}
}
```

Use cases:

- Fill partial preoperative context, then import later after surgery.
- Import parsed pathology fields, then let a clinician confirm.
- Bridge to a future patient database or EMR integration through an authenticated backend.
- Generate a patient treatment plan summary.

Do not send identifiable patient information to public endpoints.

## Pathology Extraction Beta

The agent may accept plain text pathology reports through paste or `.txt/.md` upload. The current extractor is rule-based and experimental.

Recommended agent behavior:

1. Extract candidate fields.
2. Report uncertainty and missing required fields.
3. Ask the clinician to confirm before applying values.
4. Never treat extracted values as final without human review.

Useful target fields include:

- Age, menopausal status, laterality, symptoms, ECOG.
- Tumor size, invasive vs DCIS-only, grade/nuclear grade.
- cT/cN/cM and pT/pN/pM including neoadjuvant `y`.
- ER/PR percentage and intensity, HER2 IHC/ISH, Ki-67 value/range.
- LVI, PNI, SLN/LN counts, metastatic sites.
- Oncotype RS if available.

Known high-risk extraction cases:

- `HER2 IHC 2+` is not enough to classify HER2-positive. Use ISH/FISH: `2+ / ISH negative` maps to `her2_ihc=2+`, `her2_fish=-`, `her2=-`; `2+ / ISH positive` maps to `her2_fish=+`, `her2=+`.
- Preserve Ki-67 operators and ranges. Values like `<5`, `<14`, `5-14`, and `>=20` must not be collapsed to a single plain number.
- Axillary surgery is multi-select. If a record says `SLNB + TAD, converted to ALND`, keep all applicable procedures, for example `SLNB,TAD,ALND`.
- `ypT` or `ypN` implies neoadjuvant treatment context. Store the clean pT/pN value and set the post-NAC/y-prefix flag.
- `No residual invasive carcinoma, residual DCIS only` should normalize to `post_nac_response=DCIS only` and `pT=Tis`, not residual invasive disease.
- Arithmetic answers should state assumptions explicitly, especially month-to-day conversion, dose count, cycle count, NHI coverage, and self-pay scope.

## Clinical Guardrails

- Present guideline or reimbursement content as a pointer, not official final authorization.
- Prefer structured outputs with explicit assumptions.
- Separate anatomic AJCC stage from prognostic stage.
- For drug answers, state that indication depends on setting, line of therapy, biomarker status, prior therapy, payer rules, and institutional policy.
- For patient-facing outputs, avoid detailed guideline quotations and avoid unsupported promises about benefit or cost.
- For PHI workflows, call an authenticated hospital backend instead of public Netlify APIs.

## Suggested Agent Task Patterns

Drug query:

```json
{
  "intent": "drug_lookup",
  "tool_id": "breastPage",
  "required_context": ["disease_setting", "ER", "PR", "HER2", "N", "M", "prior_therapy"],
  "reply_style": "summarize candidate classes, then list missing filters"
}
```

Stage query:

```json
{
  "intent": "stage_calculation",
  "tool_id": "wsPage",
  "required_context": ["T", "N", "M", "grade", "ER", "PR", "HER2"],
  "reply_style": "give anatomic stage first; prognostic stage only if fields are complete"
}
```

Treatment plan summary:

```json
{
  "intent": "patient_treatment_plan",
  "required_context": ["stage", "subtype", "planned_regimen", "drug_names", "cycle_count", "NHI_self_pay_status", "missing_tests", "support_resources"],
  "reply_style": "patient-readable summary with assumptions and missing items"
}
```

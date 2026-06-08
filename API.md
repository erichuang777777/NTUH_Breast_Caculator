# API Deployment Notes

The app now has the same public read/calculation API shape in two runtimes:

- Netlify: `/api/*` is routed to `netlify/functions/api.js`.
- Local server: `python web_app.py` serves the same `/api/*` paths from SQLite.

Netlify is read-only. Admin writes still require the local Python server because
they update `nhi_drug_coverage.db`.

## Public Endpoints

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

The deployed frontend also includes an in-app guide at `/?page=api` with a
browser smoke test that calls every public endpoint.

Example calculation request:

```bash
curl -X POST https://your-site.netlify.app/api/calculate/staging-score \
  -H "content-type: application/json" \
  -d "{\"age\":55,\"size_mm\":20,\"grade\":2,\"nodes_pos\":0,\"cT\":\"T2\",\"cN\":\"N0\",\"cM\":\"M0\",\"er_hscore\":270,\"pr_hscore\":200,\"her2\":\"-\",\"ki67\":15}"
```

JavaScript agent example:

```js
const patientContext = {
  age: 55,
  size_mm: 20,
  grade: 2,
  nodes_pos: 0,
  cT: "T2",
  cN: "N0",
  cM: "M0",
  er_hscore: 270,
  pr_hscore: 200,
  her2: "-",
  ki67: 15
};

const res = await fetch("/api/calculate/risk-scores", {
  method: "POST",
  headers: {
    "content-type": "application/json",
    "x-contact-email": "team@example.org",
    "x-client-app": "hospital-agent-dev"
  },
  body: JSON.stringify(patientContext)
});
const data = await res.json();
```

## Public API Policy

The Netlify API is public read-only support for demos, calculators, and trusted
frontend/agent integrations. Callers should send:

- `X-Contact-Email`: maintainer or service contact for abuse/debug follow-up.
- `X-Client-App`: human-readable caller name, for example `hospital-agent-dev`.

Do not put patient identifiers, PHI, or API secrets into public browser calls.
If a workflow needs patient database lookup, EMR write-back, admin data updates,
or strong access control, route it through an authenticated hospital backend.
The frontend can then consume the returned patient context bundle.

## External Copilot Endpoint

The dashboard AI Agent calls an agent gateway before falling back to local
rules.

Local demo:

- On `127.0.0.1` or `localhost`, the frontend automatically calls `/api/agent`.
- `web_app.py` proxies `/api/agent` to Ollama.
- Default model: `gemma4:31b-cloud`.

Optional browser override:

```js
localStorage.setItem("nhi_dashboard_agent_api_config", JSON.stringify({
  enabled: true,
  endpoint: "/api/agent",
  headers: { "x-contact-email": "team@example.org" }
}));
```

The system prompt belongs in the server-side gateway, not frontend code. The
frontend sends context and tool registry; the gateway owns model selection,
guardrails, secrets, source policy, logging, and rate limits.

Local Ollama override:

```powershell
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "gemma4:31b-cloud"
python web_app.py --port 8080
```

The frontend sends:

```json
{
  "message": "...",
  "patient_context": {},
  "derived": {},
  "report_text": "...",
  "tool_registry": []
}
```

The external API may return:

```json
{
  "reply": "已整理欄位",
  "tool_id": "",
  "patient_patch": {
    "cT": "T2",
    "cN": "N1",
    "cM": "M0",
    "er": "+",
    "pr": "+",
    "her2": "+"
  },
  "citations": []
}
```

`tool_id` is optional and should be returned only when the user explicitly asks
to open/call/show a tool. `patient_patch` is optional; the frontend shows a
confirmation button before writing fields into Patient Context.

Supported `tool_id` values include `wsPage`, `breastPage`,
`inpatientPage`, `icdPage`, `trialsPage`, `calcPage`, `ihc4Page`, `cts5Page`,
`pepiPage`, `supportResources`, and `apiPage`.

## GitHub Issue Reports

The in-app issue reporter opens a prefilled GitHub Issues URL. GitHub still
requires the user to sign in and the repository must have Issues enabled. A
static Netlify frontend cannot create issues anonymously without exposing a
token. If anonymous submission is required later, add a server-side Netlify
Function backed by a GitHub App or repository-scoped token and rate-limit that
function.

## Patient Context Bundle

The Workspace export button writes a structured JSON file:

```json
{
  "schema": "onco_breast_patient_context_bundle.v1",
  "patient_id": "...",
  "encounter_id": "...",
  "patient_context": {},
  "derived": {}
}
```

Netlify remains read-only. Importing this bundle into a patient database,
writing back to an EMR, or storing partially completed records should be handled
by a separate authenticated hospital backend.

## Patient Center Recording Service

The Netlify frontend does not store audio, transcribe recordings, or call LLMs
directly. Patient Center only records audio in the browser and, after explicit
user action, calls a separately configured recording service. Configure the base
URL in Patient Center, for example `http://localhost:8787/api`.

Required CORS behavior:

- Allow the deployed Netlify origin.
- Accept `POST` with `multipart/form-data` for audio upload.
- Return JSON for every endpoint.

Expected endpoints:

```text
GET  /health
POST /encounters
POST /encounters/{encounter_id}/audio
POST /encounters/{encounter_id}/process
GET  /encounters/{encounter_id}
```

Create an encounter:

```http
POST /encounters
Content-Type: application/json
```

```json
{
  "patient_context": {},
  "derived": {
    "anatomic_stage": "IIA",
    "subtype": "HR+/HER2-",
    "icd10": "C50.412",
    "ntuh_catastrophic_no": "...",
    "phase_label": "術後輔助治療"
  },
  "consent_confirmed": true,
  "client": {
    "app": "OncoBreast Calculator Patient Center",
    "version": "",
    "timezone": "Asia/Taipei"
  }
}
```

Response:

```json
{
  "encounter_id": "enc_20260608_001",
  "status": "created"
}
```

Upload audio:

```http
POST /encounters/enc_20260608_001/audio
Content-Type: multipart/form-data
```

Fields:

- `audio`: recorded browser audio, usually `audio/webm`
- `metadata`: JSON string with `filename`, `mime_type`, `size_bytes`, and
  `patient_context_included`

Start transcription and note generation:

```http
POST /encounters/enc_20260608_001/process
Content-Type: application/json
```

```json
{
  "outputs": ["transcript", "patient_summary", "soap", "plan"],
  "patient_context": {},
  "derived": {},
  "plan_requires_physician_confirmation": true
}
```

Get status/result:

```json
{
  "encounter_id": "enc_20260608_001",
  "status": "done",
  "transcript": "...",
  "summary": {
    "patient_summary": "...",
    "patient_questions": [],
    "family_questions": [],
    "doctor_explanations": []
  },
  "soap": "...",
  "plan": "..."
}
```

The `plan` field is an AI draft. The frontend displays it as a draft for
physician review; the recording service should not mark it as final clinical
documentation without a physician confirmation step.

## Refreshing Netlify API Data

After changing the SQLite database locally, refresh the static Netlify payloads:

```bash
python api_export.py
git add data/api
git commit -m "Update API data export"
git push origin master
```

## Agent Data Fix Workflow

For issue-driven data fixes, do not update SQLite directly. Create a JSON patch
under `data/patches/` and apply it with:

```bash
python tools/db_patch.py data/patches/issue-123-topic.json --dry-run
python tools/db_patch.py data/patches/issue-123-topic.json
python tools/check_api.py
```

`tools/db_patch.py` writes an audit line to `data/patches/applied_log.jsonl` and
reruns `api_export.py` after successful apply.

## PWA

The deployed frontend includes:

- `manifest.webmanifest`
- `sw.js`
- `offline.html`
- PNG icons under `icons/`

The service worker uses network-first for `/api/*` and cached shell fallback for
the app UI.

# Module Boundaries

This document defines the current replaceable boundaries for OncoBreast Calculator. The goal is to let each module be developed, tested, or swapped independently while sharing a common patient context.

## Boundary Rules

- Shared clinical state lives in the patient context bundle. Feature modules should read from this bundle and emit explicit patches or results.
- Modules should not silently mutate unrelated patient fields. Cross-module updates must go through patient context setters or structured import/export.
- Calculators should be deterministic. Agent text may explain or ask questions, but calculation output should come from calculator or lookup tools.
- Public Netlify/API endpoints are read-only unless routed through an authenticated hospital backend.
- Free-text extraction is beta. It should produce candidate patches for human confirmation, not final clinical truth.
- Cross-cancer modules should follow `docs/MULTI_CANCER_MODULE_CONTRACT.md` so disease-specific code can be swapped without rebuilding the shell.

## Disease Module Registry

Owner files:

- `assets/js/modules/disease-module-loader.js`: manifest registry, loading, and light validation.
- `assets/js/modules/disease/breast/manifest.json`: first concrete disease module manifest.
- `data/schemas/onco_disease_module_manifest.v1.schema.json`: manifest schema.

Replaceable contract:

- New cancers should add a manifest and register it through the loader.
- The core shell should use manifest field groups, tools, agent tools, and benchmark paths instead of hard-coding disease-specific module lists.
- Disease modules may define their own context schema, but should keep shared oncology fields under the core context contract.

## Patient Context

Owner files:

- `assets/js/modules/patient-context-adapter.js`: storage, import/create, patch application, bundle helper.
- `index.html`: workspace inputs and visible quick controls.
- `assets/js/legacy-app.js`: patient state, setters, sync, import/export, dashboard summaries.
- `docs/patient_context_bundle.md`: structured export contract.

Input:

- Manual workspace controls.
- JSON import.
- Agent/pathology extraction candidate patch.

Output:

- `onco_breast_patient_context_bundle.v1`.
- Shared context for staging, drug lookup, trial display, risk calculators, patient treatment plan, and agent payload.

Replaceable contract:

- Keep field names stable or version the bundle.
- New fields must define allowed values and normalization rules.
- Extraction output must be a patch, not direct UI mutation.

## Staging Module

Owner files:

- `assets/js/legacy-app.js`: quick TNM controls, AJCC summaries, stage calculator functions.
- `web_app.py` and `netlify/functions/api.js`: `/api/calculate/staging-score`.

Input:

- T, N, M, grade, ER, PR, HER2 when available.

Output:

- Anatomic stage first.
- Prognostic stage only when required fields are present and supported.
- Clear unsupported state for boundary combinations.

Replaceable contract:

- Do not infer unsupported AJCC combinations.
- Keep anatomic and prognostic stage as separate fields.
- If external AJCC logic is introduced, expose it behind the same endpoint.

## Drug And Formulation Modules

Owner files:

- `data/api/drugs.json`
- `data/formulations.json` if present in deployment data.
- `assets/js/modules/drug-cards.js`
- `assets/js/legacy-app.js`: breast drug UI and dashboard card summaries.
- `web_app.py` and `netlify/functions/api.js`: drug/formulation lookup endpoints.

Input:

- Disease area, ER/PR/HER2, stage/setting, line of therapy, mutation, regimen, trade/generic names.

Output:

- Candidate drugs, indication text, NHI price, self-pay status, prior authorization, and formulation cost assumptions.

Replaceable contract:

- Drug lookup is information retrieval, not final eligibility.
- Regimen aliases must map to drug names, for example KN522 -> pembrolizumab-containing regimen.
- Cost calculations must state dose/cycle/month assumptions.

## Risk Calculator Modules

Owner files:

- `assets/js/legacy-app.js`: PREDICT, IHC4, CTS5, PEPI, Gail, RCB UI/calculations.
- `web_app.py` and `netlify/functions/api.js`: `/api/calculate/risk-scores`.

Input:

- Shared patient context plus calculator-specific fields.

Output:

- Numeric score/result, missing fields, applicability notes.

Replaceable contract:

- Calculators must read shared context by default.
- If a calculator has extra local fields, they must be listed as module-specific inputs.
- Do not hide missing-field assumptions inside the score.

## Pathology Extraction Beta

Owner files:

- `web_app.py`: local agent gateway and patch sanitization.
- `netlify/functions/api.js`: Netlify agent/prompt mirror.
- `assets/js/legacy-app.js`: report paste/upload UI and candidate patch application.
- `data/agent_bench/bench_adversarial_2026-06-06.json`: adversarial extraction tests.

Input:

- Pasted text or uploaded `.txt/.md` report.

Output:

- Candidate `patient_patch`.
- Uncertainty/missing-field explanation.

Replaceable contract:

- Preserve ranges/operators such as `<5`, `<14`, `5-14`, `>=20`.
- Normalize HER2 IHC/ISH into separate schema fields.
- Keep multi-select surgery values such as `SLNB,TAD,ALND`.
- Detect `ypT`/`ypN` as post-NAC y-prefix.
- Map DCIS-only residual disease to `DCIS only` and pT `Tis` when applicable.

## Agent Gateway

Owner files:

- `assets/js/modules/agent-adapter.js`: gateway config, payload construction, POST call boundary.
- `assets/js/modules/agent-panel-state.js`: conversation history and context-meter state.
- `web_app.py`: local `/api/agent`, Ollama proxy, `AGENT_SYSTEM_PROMPT`.
- `netlify/functions/api.js`: Netlify API mirror and prompt.
- `docs/AGENT_SKILL.md`: external agent integration instructions.
- `data/agent_bench/`: benchmark corpus and run outputs.

Input:

- User message.
- Current patient context.
- Derived calculator results.
- Optional report text.
- Tool registry.

Output:

- Reply text.
- Tool ID used.
- Candidate patient patch.
- Citations/notes when available.

Replaceable contract:

- The agent may call tools, but deterministic results must come from the website/API tools.
- The agent must refuse or clearly mark out-of-scope answers outside the website data.
- Conversation reset should be separate from patient context reset unless explicitly requested.
- Benchmark results should record actual tool calls, not only expected tool calls.

## Benchmark Module

Owner files:

- `assets/js/modules/benchmark-loader.js`: corpus/result loading and result map merge.
- `assets/js/modules/benchmark-browser.js`: benchmark page state, filters, summary, and Q/A table rendering.
- `tools/agent_benchmark.py`
- `data/agent_bench/bench_v1.json`
- `data/agent_bench/bench_adversarial_2026-06-06.json`
- `index.html`: benchmark browser.

Input:

- Corpus JSON with question, context, expected checks, reference answer, and optional failure note.

Output:

- Result JSON with pass/fail, actual agent reply, actual called tools, patient patch, and validation checks.

Replaceable contract:

- Keep information retrieval, reasoning, extraction, out-of-scope, and adversarial categories separate.
- Treat validator wording failures separately from true clinical/data failures.
- Difficult cases should remain in the corpus even after prompt fixes.

## Support Resources

Owner files:

- `data/support_resources.json`
- `assets/js/legacy-app.js`: support card rendering.

Input:

- Patient context and resource category.

Output:

- Resource pointers for insurance, labor insurance, foundations, charity/support programs, and patient-facing next steps.

Replaceable contract:

- Resource information is a pointer and may expire.
- Do not present eligibility as final approval.
- Keep source URL/contact/update date for each resource.

## Internationalization

Owner files:

- `data/i18n_cache/*.json`
- `assets/js/legacy-app.js`: language toggle and translation application.

Input:

- Static site text and data translations.

Output:

- Layout-stable translated UI.

Replaceable contract:

- Translation must not change element layout contracts.
- Clinical labels should prefer semantically correct translation over polished marketing copy.
- Agent live replies are not currently translated by this module.

## Development Checklist For New Modules

Before adding or replacing a module:

1. Define input fields and allowed values.
2. Define output payload and missing-field behavior.
3. Decide whether it can mutate patient context; if yes, emit a patch.
4. Add or update API endpoint documentation if external agents need it.
5. Add benchmark cases for normal, missing-data, and adversarial behavior.
6. Add a dashboard summary only after the module can explain assumptions.

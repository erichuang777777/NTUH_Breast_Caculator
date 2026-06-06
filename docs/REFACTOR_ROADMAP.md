# Refactor Roadmap

This roadmap keeps the current static Netlify deployment model while gradually reducing `assets/js/legacy-app.js`.

## Current Direction

Use small browser globals instead of a bundler for now:

- Keep plain `<script>` loading.
- Put replaceable boundaries in `assets/js/modules/`.
- Preserve legacy global function names used by inline HTML handlers.
- Move pure data loading, payload building, and deterministic transforms before moving UI rendering.

## Completed First Steps

- `patient-context-adapter.js`: storage, create/import, patch application, bundle helper.
- `agent-adapter.js`: agent config, payload builder, API POST boundary.
- `benchmark-loader.js`: benchmark corpus/result loading and result map merge.
- `benchmark-browser.js`: benchmark page state, filters, summary, and Q/A table rendering.

## Recommended Next Extraction Order

### 1. Agent Panel Module

Move:

- Conversation history storage.
- Context token estimate.
- Agent panel rendering.
- Prompt buttons and file upload handling.

Keep in legacy for now:

- `dashboardPatientContext()`.
- Widget opening functions.
- Pathology rule parser until its schema is stable.

Acceptance checks:

- Conversation persists when entering/leaving tools.
- Enter sends message.
- Context meter updates.
- External `/api/agent` payload is unchanged.

### 2. Patient Context UI Module

Move:

- Context pill rendering.
- Core/Common/Module readiness summary.
- Preset buttons.
- Import/export/reset buttons.

Keep in legacy for now:

- `setPatientField()` until all calculators read through the same context adapter.
- Workspace quick chip handlers.

Acceptance checks:

- Quick mode and full mode still sync.
- Reset clears patient info and agent history only when requested.
- Structured export stays `onco_breast_patient_context_bundle.v1`.

### 3. Pathology Extraction Module

Move:

- `parseWorkspacePathologyReport()`.
- Marker extraction helpers.
- HER2/Ki-67 normalization.
- SLNB/TAD/ALND multi-select extraction.
- ypTNM and DCIS-only normalization.

Acceptance checks:

- Adversarial extraction cases stay in benchmark.
- Candidate patch is shown before applying.
- No direct mutation of `_patient` from extractor.

### 4. Calculator Adapter Layer

Move:

- Shared input mapping from patient context to calculators.
- Missing-field detection.
- Result payload normalization.

Keep calculator formulas close to their current code until there are tests for each formula.

Acceptance checks:

- PREDICT, IHC4, CTS5, PEPI, RCB all read shared context.
- Calculator-specific local fields are documented.
- API `/api/calculate/*` and frontend calculations return compatible fields.

### 5. Drug And Formulation Service Module

Move:

- Drug match scoring.
- Alias expansion.
- Regimen-to-drug mapping.
- Formulation price composition helpers.

Acceptance checks:

- Pembrolizumab/KN522, Perjeta/Pertuzumab, Phesgo remain distinct.
- Drug search, dashboard cards, and agent answers use the same lookup path.
- Cost answers list assumptions.

## Refactor Guardrails

- Do not convert to ES modules or a bundler until Netlify/static deployment is stable with the current globals.
- Do not split formula code before adding tests around expected outputs.
- Do not move UI rendering and state mutation in the same patch unless the module is tiny.
- Do not introduce a second patient state object. All modules must read from the shared patient context adapter or receive an explicit patient object.
- Keep all new modules free of clinical side effects: they should return payloads, patches, or HTML, not silently write unrelated fields.

## Useful Tests To Add

- Browser smoke test for all top-level pages: home, workspace, API, benchmark, dashboard mode.
- Patient context patch tests: unknown fields ignored, empty values ignored, axillary surgery normalized.
- Agent payload tests: tool registry, patient context, derived stage, report text.
- Pathology extraction adversarial tests: HER2 2+/ISH-, Ki-67 `<5`, ypTNM, DCIS only, SLNB+TAD+ALND.
- Benchmark browser tests: 300 main + 14 adversarial cases load and failed notes appear.

# Multi-Cancer Module Contract

This contract defines how current OncoBreast modules should be generalized so other cancers can reuse the same workspace, agent, benchmark, API, and data import/export patterns.

The goal is not to force all cancers into a breast cancer schema. The goal is to separate:

- Shared cross-cancer infrastructure.
- Shared oncology concepts.
- Disease-specific context fields.
- Disease-specific calculators, drug matchers, evidence blocks, and patient summaries.

## Design Principle

Every cancer module should be a replaceable disease package:

```text
core shell
  -> patient context core
  -> disease module manifest
  -> disease context extension
  -> calculators
  -> drug/regimen matcher
  -> evidence blocks
  -> support resources
  -> benchmark corpus
```

The website shell should not need to know breast-specific details. It should ask the active disease module for field definitions, derived results, cards, and agent tools.

## Shared Core

These modules should remain cancer-agnostic:

| Module | Responsibility |
|---|---|
| Patient context adapter | Storage, import/export, patch application, bundle versioning. |
| Agent adapter | Payload construction, external gateway call, tool registry. |
| Benchmark loader/browser | Load corpus/results and render Q/A validation records. |
| API guide | Document read-only endpoints and integration policy. |
| Support resources shell | Display resource pointers without disease-specific eligibility promises. |
| i18n shell | Translate UI labels and static data without changing layout. |

## Oncology Core Context

These fields are reusable across many solid tumors:

```json
{
  "patient_id": "",
  "encounter_id": "",
  "age": "",
  "sex": "",
  "height": "",
  "weight": "",
  "scr": "",
  "ecog": "",
  "dm": "",
  "htn": "",
  "cad": "",
  "diagnosis_date": "",
  "disease_status": "",
  "treatment_setting": "",
  "prior_treatment": "",
  "metastatic_sites": []
}
```

Recommended shared enums:

- `treatment_setting`: `initial_workup`, `neoadjuvant`, `adjuvant`, `definitive`, `maintenance`, `locoregional_recurrence`, `metastatic`, `palliative`, `surveillance`.
- `disease_status`: `new_diagnosis`, `post_op`, `residual_disease`, `recurrent`, `metastatic`, `unknown`.
- `metastatic_sites`: `bone`, `liver`, `brain`, `lung`, `peritoneum`, `distant_ln`, `other`.

Breast-specific aliases such as `phase` can remain during migration, but new modules should prefer `treatment_setting`.

## Disease Context Extension

Each cancer defines its own extension under a disease key.

Example:

```json
{
  "schema": "onco_patient_context_bundle.v1",
  "disease": "breast",
  "patient_context": {
    "core": {
      "age": "49",
      "sex": "F",
      "ecog": "0",
      "treatment_setting": "initial_workup"
    },
    "disease": {
      "breast": {
        "side": "L",
        "cT": "T2",
        "cN": "N1",
        "cM": "M0",
        "er": "+",
        "pr": "+",
        "her2": "-",
        "ki67": "20"
      }
    }
  }
}
```

During migration, OncoBreast still supports the flat `patient_context` v1. Future disease modules should support the nested `core + disease` shape to avoid duplicated field names across cancers.

## Disease Module Manifest

Every disease module should provide a manifest:

```json
{
  "schema": "onco_disease_module_manifest.v1",
  "id": "breast",
  "label": "Breast Cancer",
  "context_schema": "data/schemas/onco_breast_patient_context_bundle.v1.schema.json",
  "field_groups": [
    {
      "id": "staging",
      "label": "Staging",
      "fields": ["cT", "cN", "cM", "pT", "pN"]
    }
  ],
  "tools": [
    {
      "id": "staging",
      "label": "AJCC staging",
      "input_fields": ["cT", "cN", "cM"],
      "output_fields": ["anatomic_stage", "stageability_note"]
    }
  ],
  "agent_tools": [
    {
      "id": "breast_drug_lookup",
      "label": "Breast drug lookup",
      "aliases": ["breast drug", "HER2", "TNBC", "ER+"]
    }
  ],
  "benchmark_corpus": "data/agent_bench/bench_v1.json"
}
```

Schema:

`data/schemas/onco_disease_module_manifest.v1.schema.json`

First concrete module:

`assets/js/modules/disease/breast/manifest.json`

Runtime loader:

`assets/js/modules/disease-module-loader.js`

The breast manifest is the template for other cancers. New cancer modules should copy the manifest shape and replace only disease-specific fields, tools, data sources, and benchmark corpus.

## Required Disease Module Interfaces

### 1. Field Definitions

Function shape:

```js
getFieldDefinitions() -> {
  core: FieldDefinition[],
  disease: FieldDefinition[]
}
```

Field definition:

```json
{
  "key": "her2",
  "label": "HER2",
  "type": "enum",
  "values": ["+", "-", ""],
  "source_category": "pathology_special_stain",
  "required_for": ["drug_lookup", "prognostic_stage"],
  "normalization": "HER2 IHC/ISH summary from pathology report; do not infer 2+ as positive without ISH."
}
```

Every disease module should classify fields by source category. This prevents pathology special stains from being treated like routine laboratory values.

Recommended source categories:

| Category | Meaning |
|---|---|
| `clinical_core` | Demographics, ECOG, comorbidity, visit context. |
| `clinical_staging` | Clinician-entered or imaging-derived cTNM and metastatic sites. |
| `pathology_morphology` | H&E / morphology pathology findings, such as invasive size, grade, LVI/PNI, margin. |
| `pathology_special_stain` | IHC/special stains in pathology report, such as ER, PR, Ki-67. |
| `pathology_ish` | ISH/FISH/reflex pathology tests, such as HER2 ISH/FISH. |
| `molecular_genomics` | Molecular/genomic reports, such as BRCA, PIK3CA, ESR1, Oncotype RS, CIViC variants. |
| `operative_note` | Surgical procedure source, such as BCS/SM and SLNB/TAD/ALND. |
| `treatment_admin` | Regimen, cycle, administration, prior therapy, or payer/admin context. |

### 2. Normalize Patch

Function shape:

```js
normalizePatch(patch, currentContext) -> {
  patch: {},
  warnings: [],
  conflicts: []
}
```

Rules:

- Unknown fields should be ignored or returned as warnings.
- Do not silently overwrite confirmed values with lower-confidence extracted values.
- Preserve operators and ranges when clinically meaningful.
- Multi-select fields should keep all selected values.

### 3. Derive Results

Function shape:

```js
derive(context) -> {
  stage: {},
  subtype: "",
  missing_fields: [],
  scores: {},
  warnings: []
}
```

Rules:

- Deterministic calculators only.
- Unsupported combinations should return `stageability_note`, not a guessed stage.
- Derived fields are recomputed locally and should not be trusted from imported payloads.

### 4. Render Dashboard Cards

Function shape:

```js
getDashboardCards(context, derived) -> CardDefinition[]
```

Card definition:

```json
{
  "id": "breast_drugs",
  "title": "Breast drugs",
  "status": "green",
  "summary": ["HER2-", "ER+", "candidate endocrine options"],
  "tool_id": "drug_lookup"
}
```

Rules:

- Cards summarize, not store state.
- A card should declare which context fields it needs.
- Cards should not mutate patient context directly.

### 5. Drug And Regimen Matcher

Function shape:

```js
matchDrugs(context) -> {
  candidates: [],
  missing_fields: [],
  assumptions: [],
  source_version: ""
}
```

Rules:

- Information retrieval only.
- Do not provide final eligibility.
- Cost output must state dose, cycle, BSA/weight, NHI/self-pay assumptions.

### 6. Evidence Blocks

Function shape:

```js
getEvidenceBlocks(context, derived) -> EvidenceBlock[]
```

Rules:

- Store citations as structured pointers.
- Do not copy long guideline text.
- Separate local/institutional evidence from public references.

### 7. Agent Tool Registry

Function shape:

```js
getAgentTools() -> AgentTool[]
```

Agent tool:

```json
{
  "id": "staging",
  "label": "AJCC staging",
  "aliases": ["stage", "TNM", "第幾期"],
  "required_context": ["cT", "cN", "cM"],
  "boundary": "Use deterministic staging tool; do not infer unsupported combinations."
}
```

### 8. Benchmark Corpus

Each disease module should provide:

- Basic information retrieval questions.
- Missing-field questions.
- Boundary/staging questions.
- Drug/regimen/cost questions.
- Field extraction adversarial questions.
- Out-of-scope refusal questions.

Benchmark records must include actual called tools in run outputs.

## Suggested Repository Layout

Current transitional layout:

```text
assets/js/modules/
  disease-module-loader.js
  patient-context-adapter.js
  agent-adapter.js
  benchmark-loader.js
  benchmark-browser.js
  disease/
    breast/
      manifest.json
      fields.js
      derive.js
      cards.js
      drug-matcher.js
      evidence.js
      agent-tools.js
      benchmark.json
```

Future backend/API layout:

```text
disease_modules/
  breast/
  lung/
  colorectal/
data/schemas/
  onco_disease_module_manifest.v1.schema.json
  onco_patient_context_bundle.v1.schema.json
```

## Migration From Current Breast Implementation

Current flat breast fields remain supported:

```json
{
  "patient_context": {
    "cT": "T2",
    "cN": "N1",
    "cM": "M0",
    "er": "+",
    "pr": "+",
    "her2": "-"
  }
}
```

New modules should prefer:

```json
{
  "patient_context": {
    "core": {
      "age": "49",
      "ecog": "0",
      "treatment_setting": "initial_workup"
    },
    "disease": {
      "breast": {
        "cT": "T2",
        "cN": "N1",
        "cM": "M0",
        "er": "+",
        "pr": "+",
        "her2": "-"
      }
    }
  }
}
```

## What Other Developers Should Build

For a new cancer module, implement only:

1. Disease field schema.
2. Patch normalization.
3. Derive/staging functions.
4. Dashboard cards.
5. Drug/regimen matcher.
6. Evidence block provider.
7. Agent tool registry.
8. Benchmark corpus.

Do not rebuild:

- Patient context storage.
- Agent gateway.
- Benchmark browser.
- Import/export shell.
- API access policy.
- i18n shell.
- Support resource shell.

## Acceptance Checklist

A disease module is ready for integration when:

- It has a manifest that validates against `onco_disease_module_manifest.v1`.
- It can import a single cross-sectional context bundle.
- It can render dashboard cards without editing core shell code.
- It exposes deterministic derived results.
- It exposes agent tools with boundaries and required context.
- It has benchmark cases and run results.
- It does not require PHI on public Netlify deployment.

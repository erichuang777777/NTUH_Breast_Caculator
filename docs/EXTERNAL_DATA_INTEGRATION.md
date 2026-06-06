# External Data Integration Contract

This document defines how outside systems should provide one cross-sectional breast cancer patient snapshot to OncoBreast Calculator.

The target use case is a single clinical time frame, not longitudinal CRM tracking. External systems can create a JSON bundle, import it into the website, and let the website recompute staging, drug filters, risk calculators, benchmark/agent context, and patient-facing summaries.

## Contract Summary

Use this schema:

`onco_breast_patient_context_bundle.v1`

Schema file:

`data/schemas/onco_breast_patient_context_bundle.v1.schema.json`

Current import behavior:

- The website imports only `patient_context`.
- `derived` is ignored on import and recomputed locally.
- Unknown fields inside `patient_context` are ignored by the current patient context patch adapter unless they are later added to `PATIENT_DEFAULTS`.
- Empty string means unknown/not entered.
- Candidate extraction values should be marked as `draft` or `requires_confirmation` in metadata; the clinician should confirm before using them.

## Minimal Valid Bundle

```json
{
  "schema": "onco_breast_patient_context_bundle.v1",
  "generated_at": "2026-06-06T09:00:00+08:00",
  "source_app": "hospital-pathology-adapter",
  "patient_id": "demo-001",
  "encounter_id": "2026-06-06-outpatient",
  "time_frame": {
    "type": "single_cross_section",
    "anchor_date": "2026-06-06",
    "clinical_setting": "initial_workup"
  },
  "patient_context": {
    "age": "49",
    "side": "L",
    "size": "25",
    "grade": "3",
    "cT": "T2",
    "cN": "N1",
    "cM": "M0",
    "er": "+",
    "pr": "+",
    "her2": "-",
    "ki67": "20"
  }
}
```

## Recommended Rich Bundle

```json
{
  "schema": "onco_breast_patient_context_bundle.v1",
  "generated_at": "2026-06-06T09:00:00+08:00",
  "source_app": "emr-single-timeframe-exporter",
  "source_version": "0.1.0",
  "patient_id": "demo-001",
  "encounter_id": "2026-06-06-surgery-pathology",
  "time_frame": {
    "type": "single_cross_section",
    "anchor_date": "2026-06-06",
    "clinical_setting": "post_neoadjuvant_surgery",
    "data_cutoff": "2026-06-06T09:00:00+08:00"
  },
  "patient_context": {
    "age": "49",
    "menopause": "post",
    "side": "L",
    "symptoms": "yes",
    "ecog": "0",
    "dm": "",
    "htn": "",
    "cad": "",
    "size": "18",
    "tumor_kind": "invasive",
    "grade": "3",
    "cT": "T2",
    "cN": "N1",
    "cM": "M0",
    "pT": "T1c",
    "pN": "N1mi",
    "post_nac_prefix": "yes",
    "er": "+",
    "pr": "+",
    "her2": "-",
    "her2_ihc": "2+",
    "her2_fish": "-",
    "ki67": "5-14",
    "oncotype_rs": "",
    "brca": "",
    "pdl1": "",
    "pik3ca": "",
    "esr1": "",
    "civic_variant": "",
    "sln_pos": "1",
    "sln_total": "3",
    "aln_pos": "0",
    "aln_total": "12",
    "nodes_pos": "1",
    "nodes_total": "15",
    "pni": "absent",
    "lvi": "present",
    "margin_involved": "no",
    "breast_surgery": "BCS",
    "axillary_surgery": "SLNB,TAD,ALND",
    "post_nac_response": "residual ca",
    "height": "165",
    "weight": "60",
    "scr": "0.8"
  },
  "source_evidence": {
    "pT": {
      "source_type": "pathology_report",
      "source_id": "path-20260606-001",
      "text": "ypT1c ypN1mi",
      "confidence": 0.93,
      "status": "requires_confirmation"
    },
    "axillary_surgery": {
      "source_type": "operative_note",
      "source_id": "op-20260606-001",
      "text": "SLNB + TAD, frozen positive, converted to ALND",
      "confidence": 0.88,
      "status": "requires_confirmation"
    }
  }
}
```

## Field Dictionary

### Identity And Time Frame

| Field | Required | Meaning |
|---|---:|---|
| `schema` | yes | Must be `onco_breast_patient_context_bundle.v1`. |
| `generated_at` | recommended | ISO datetime when the bundle was generated. |
| `source_app` | recommended | External adapter or system name. |
| `source_version` | optional | External adapter version. |
| `patient_id` | optional | Local pseudonymous ID or EMR ID if used inside an authenticated hospital environment. Avoid public PHI. |
| `encounter_id` | optional | Visit/admission/report identifier. |
| `time_frame.type` | recommended | Use `single_cross_section`. |
| `time_frame.anchor_date` | recommended | Clinical date this snapshot represents. |
| `time_frame.clinical_setting` | recommended | `initial_workup`, `neoadjuvant`, `post_neoadjuvant_surgery`, `adjuvant`, `locoregional_recurrence`, `metastatic`, or local text. |

### Core Patient Context

All values should be strings unless explicitly documented otherwise. Empty string means unknown.

| Field | Values / Format | Notes |
|---|---|---|
| `age` | number string | Age at diagnosis or current snapshot age. |
| `sex` | `F`, `M`, empty | Mostly optional for breast workflow. |
| `height`, `weight`, `scr` | number string | Used for BSA/CrCl and regimen dose context. |
| `menopause` | `pre`, `post`, empty | Website labels display as 未停經/已停經. |
| `side` | `L`, `R`, `B`, empty | Left/right/bilateral. |
| `quadrant` | `UO`, `UI`, `LO`, `LI`, `central`, `overlapping`, empty | Used for ICD/catastrophic illness helper. |
| `symptoms` | `yes`, `no`, empty | Symptomatic detection for PREDICT-like inputs. |
| `ecog`, `dm`, `htn`, `cad` | local strings or `yes`/empty | Cross-sectional comorbidity context. |

### TNM And Disease Extent

| Field | Values / Format | Notes |
|---|---|---|
| `cT`, `pT` | `Tx`, `Tis`, `T1mi`, `T1a`, `T1b`, `T1c`, `T1`, `T2`, `T3`, `T4`, empty | Prefer specific substage if known. |
| `cN`, `pN` | `Nx`, `N0`, `N0(i+)`, `N1mi`, `N1`, `N1a`, `N1b`, `N1c`, `N2`, `N2a`, `N2b`, `N3`, `N3a`, `N3b`, `N3c`, empty | Use pN for surgical pathology. |
| `cM`, `pM` | `M0`, `M1`, empty | Current UI uses M as clinical/pathologic equivalent; pM can be omitted. |
| `post_nac_prefix` | `yes`, empty | Required when report uses `ypT` or `ypN`. |
| `mets_bone`, `mets_liver`, `mets_brain`, `mets_lung` | `yes`, empty | Optional M1 site flags. |

### Pathology Morphology

| Field | Values / Format | Notes |
|---|---|---|
| `size` | mm number string | Invasive tumor size in mm from pathology or imaging-derived staging context. |
| `tumor_kind` | `invasive`, `dcis`, empty | `dcis` represents DCIS only. |
| `grade` | `1`, `2`, `3`, empty | Invasive histologic grade; for Tis this may represent nuclear grade. |

### Pathology Special Stains / IHC / ISH

These are pathology report values. They are not general laboratory exam values and should not be mapped from a routine lab table.

| Field | Values / Format | Required source | Notes |
|---|---|---|---|
| `er` | `+`, `-`, empty | Pathology special stain / IHC | Summary ER receptor status. Keep ER percentage/intensity in source evidence if available. |
| `pr` | `+`, `-`, empty | Pathology special stain / IHC | Summary PR receptor status. Keep PR percentage/intensity in source evidence if available. |
| `her2` | `+`, `-`, empty | Pathology IHC plus ISH/FISH when needed | Summary HER2 status. Do not infer HER2+ from IHC `2+` alone. |
| `her2_ihc` | `0+`, `1+`, `2+`, `3+`, empty | Pathology IHC | HER2 IHC score. |
| `her2_fish` | `+`, `-`, empty | Pathology ISH/FISH | Required to resolve IHC 2+. `2+/ISH-` maps to `her2=-`; `2+/ISH+` maps to `her2=+`. |
| `ki67` | number/range string | Pathology special stain / IHC | Preserve `<5`, `<14`, `5-14`, `20`, `>=20`. |

### Molecular / Genomic Tests

| Field | Values / Format | Required source | Notes |
|---|---|---|---|
| `oncotype_rs` | number string or empty | Optional; many patients will not have this. |
| `brca`, `pdl1`, `tp53`, `esr1`, `pik3ca`, `civic_variant` | local strings or empty | Molecular/genomic report, companion diagnostic report, or curated variant source. |

## Data Source Categories

External systems should categorize values by source, not only by field name.

| Category | Use for | Examples |
|---|---|---|
| `clinical_core` | Demographics, comorbidities, ECOG, clinical visit context | age, ECOG, DM/HTN/CAD |
| `clinical_staging` | Clinician-entered or imaging-derived cTNM | cT/cN/cM, metastatic sites |
| `pathology_morphology` | H&E / morphology pathology report | invasive size, histologic grade, DCIS only, LVI/PNI, margin |
| `pathology_special_stain` | IHC / special stain results in pathology report | ER, PR, Ki-67 |
| `pathology_ish` | ISH/FISH or equivalent pathology reflex test | HER2 ISH/FISH |
| `molecular_genomics` | Molecular or genomic tests | BRCA, PIK3CA, ESR1, Oncotype RS, CIViC variant |
| `operative_note` | Surgical procedure record | BCS/SM, SLNB/TAD/ALND |
| `treatment_admin` | Treatment/regimen/admin context | selected regimen, cycles, prior therapy |

### Surgery And Pathology

| Field | Values / Format | Notes |
|---|---|---|
| `breast_surgery` | `BCS`, `SM`, empty | Breast conserving surgery or simple/total mastectomy style marker. |
| `axillary_surgery` | comma-separated `SLNB`, `TAD`, `ALND` | Multi-select; example `SLNB,TAD,ALND`. |
| `reconstruction_surgery` | local string or empty | Optional. |
| `sln_pos`, `sln_total`, `aln_pos`, `aln_total` | integer string | Keep numerator/denominator. |
| `nodes_pos`, `nodes_total` | integer string | Can be total of SLN+ALN; website can recompute if split counts exist. |
| `pni`, `lvi` | `present`, `absent`, empty | PNI/LVI status. |
| `margin_involved` | `yes`, `no`, `close`, empty | Surgical margin summary. |
| `post_nac_response` | `pCR`, `DCIS only`, `residual ca`, empty | `no residual invasive carcinoma, residual DCIS only` should map to `DCIS only` and pT `Tis`. |

### Risk/Calculator Local Inputs

These can be included but are not required for an external cross-sectional import.

| Field | Values / Format |
|---|---|
| `rcb_d1`, `rcb_d2`, `rcb_finv`, `rcb_ln`, `rcb_dmet` | RCB calculator inputs. |
| `gail_menarche`, `gail_birth`, `gail_relatives`, `gail_biopsy`, `gail_atypia`, `gail_race` | Gail model local inputs. |

## Normalization Rules For External Developers

1. HER2:
   - `IHC 3+` -> `her2="+"`, `her2_ihc="3+"`.
   - `IHC 2+ and ISH/FISH positive/amplified` -> `her2="+"`, `her2_ihc="2+"`, `her2_fish="+"`.
   - `IHC 2+ and ISH/FISH negative/not amplified` -> `her2="-"`, `her2_ihc="2+"`, `her2_fish="-"`.
   - `IHC 1+` or `0+` -> `her2="-"`, `her2_ihc="1+"` or `0+`.
2. Ki-67:
   - Preserve operators and ranges. Do not convert `<5` to `5`.
3. ypTNM:
   - Store clean pT/pN values without the `y` prefix, and set `post_nac_prefix="yes"`.
4. Axillary surgery:
   - Keep all procedures performed. Do not collapse `SLNB + TAD converted to ALND` into only `ALND`.
5. DCIS-only residual disease:
   - `no residual invasive carcinoma, residual DCIS only` -> `post_nac_response="DCIS only"` and `pT="Tis"` when pT is not otherwise specified.
6. Node counts:
   - `positive <= total`.
   - If SLN and ALN split counts are known, provide both split and total fields.

## Source Evidence

External systems should include `source_evidence` when values are machine extracted.

`source_evidence` is not imported into patient fields today, but it is useful for auditing and future UI review.

```json
{
  "source_evidence": {
    "ki67": {
      "source_type": "pathology_special_stain",
      "source_id": "path-001",
      "text": "Ki-67 labeling index: <5%",
      "confidence": 0.91,
      "status": "requires_confirmation"
    }
  }
}
```

Recommended `status` values:

- `confirmed`: reviewed by clinician or trusted structured source.
- `requires_confirmation`: machine extracted or uncertain.
- `conflicting`: multiple sources disagree.

## Import Modes

Current website UI:

- Manual JSON import: user selects a `.json` file.
- Supported payloads:
  - Full `onco_breast_patient_context_bundle.v1`.
  - Object with `patient_context`.
  - Legacy raw `_patient` object.

Recommended external workflow:

1. Generate bundle from EMR/pathology/surgery system.
2. Validate against JSON schema.
3. Let user import into OncoBreast Calculator.
4. Website recomputes derived fields.
5. User reviews and confirms values.
6. User exports structured bundle or patient treatment plan.

Future API workflow:

- `POST /api/context/validate`: validate bundle and return missing/conflict notes.
- `POST /api/context/derive`: derive stage/subtype/scores without storing patient data.
- Authenticated hospital backend only: store draft or write back to EMR.

## Privacy And Security Boundary

- Public Netlify deployment should not receive identifiable patient data.
- PHI workflows should run behind an authenticated hospital backend.
- Use pseudonymous `patient_id` for public demo/testing.
- Do not send free-text pathology reports containing name, ID number, birthday, address, phone, or medical record number to public endpoints.

## Versioning

Breaking changes must create a new schema name:

- Current: `onco_breast_patient_context_bundle.v1`
- Next breaking version: `onco_breast_patient_context_bundle.v2`

Compatible additions:

- New optional fields.
- New metadata under `source_evidence`.
- Additional local calculator inputs.

Breaking changes:

- Renaming fields.
- Changing values for receptor/TNM/surgery fields.
- Changing meaning of empty string.

# Agent Maintenance Guide

This repository is maintained through GitHub issues plus scripted database
patches. The production Netlify site is read-only; SQLite is the source of truth
for drug/price data.

## Ground Rules

- Do not edit `nhi_drug_coverage.db` manually with ad hoc SQL unless the user
  explicitly asks for emergency repair.
- Use `tools/db_patch.py` with a JSON patch file for drug price, drug metadata,
  formulation price, coverage rule, and app config changes.
- Every DB-changing commit must include the patch file under `data/patches/`.
- After DB changes, always run `python api_export.py` and include updated
  `data/api/*.json` in the commit.
- For official NHI price refreshes, use `python update_official_prices.py
  --dry-run` first. A real run exports `data/api/*.json` and validates drug
  data semantics automatically.
- Do not add local private files, PDF/Word source documents, `.omc/`,
  `NCCN_Breast_KG/`, or other untracked bulk folders unless the user explicitly
  requests it.
- Do not reintroduce NCCN content into the public app. NCCN will return later as
  a separately reviewed plugin.

## Standard Issue Workflow

1. Read the issue and identify its type: `drug_price_fix`, `coverage_rule_fix`,
   `formulation_price_fix`, `app_config_update`, calculator bug, or UI bug.
2. For data fixes, create a patch JSON in `data/patches/`, preferably named
   `issue-<number>-<short-topic>.json`.
3. Dry-run the patch:

   ```bash
   python tools/db_patch.py data/patches/issue-123-topic.json --dry-run
   ```

4. Apply it:

   ```bash
   python tools/db_patch.py data/patches/issue-123-topic.json
   ```

5. Verify:

   ```bash
   python tools/check_api.py
   python -m py_compile web_app.py api_export.py api_calculators.py tools/db_patch.py tools/check_api.py tools/validate_drug_data.py update_official_prices.py
   ```

6. Inspect `git diff --stat` and commit the DB, patch file, and exported API
   JSON together.

## Patch File Format

See `data/patches/examples/drug-price-fix.example.json`.

Supported operation types:

- `drug_update`: update fields in `drugs`.
- `coverage_rule_update`: update fields in `coverage_rules`.
- `formulation_update`: update fields in `drug_formulations`.
- `app_config_update`: update keys in `app_config`.

Each operation should include `reason` and `source` when available. The script
records before/after values in `data/patches/applied_log.jsonl`.

## Required Checks Before Final Response

- `python tools/check_api.py`
- `python -m py_compile web_app.py api_export.py api_calculators.py tools/db_patch.py tools/check_api.py tools/validate_drug_data.py update_official_prices.py`
- For frontend changes: extract and parse inline JS from `index.html` with Node.

Report the commit hash and whether untracked local files were intentionally
left untouched.

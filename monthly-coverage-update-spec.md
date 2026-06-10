# Monthly Coverage Update Spec

## Goal

Run a monthly GitHub Action to detect changes in the official NHI drug coverage
rules PDF and flag any breast-drug rule drift.

The check is rule-based: it searches the PDF by local drug names, brand names,
and stored rule identifiers, then compares the matched page hashes against a
committed baseline.

## Schedule

- Monthly on the 27th at 15:25 UTC
- Equivalent to 23:25 Asia/Taipei

## Workflow steps

1. Download the latest "最新版藥品給付規定內容(整份帶走)" PDF from the NHI
   official page.
2. Extract page text.
3. Build a per-drug page index from local breast-drug data.
4. Compare the current page hashes with the committed baseline snapshot.
5. Run `python tools/check_api.py` as a safety smoke test.

## Failure handling

If page hashes or page assignments change, the workflow should fail and prompt
manual review. After review, regenerate the snapshot and apply the corresponding
database patch if the rules changed.

## Maintenance note

This workflow does not automatically rewrite the database. It is a drift
detection and review trigger.

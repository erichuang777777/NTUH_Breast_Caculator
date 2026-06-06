# Adversarial Agent Benchmark Notes - 2026-06-06

Corpus: `data/agent_bench/bench_adversarial_2026-06-06.json`

Result: `data/agent_bench/bench_adversarial_results_2026-06-06.json`

Run summary: 14 total, 8 passed, 6 failed by validator. Of the 6 failures, 5 are clinically/usefully meaningful extraction or schema failures and 1 is a strict validator wording issue.

## Meaningful Failures

### adv-003 - HER2 equivocal normalization

Question: 病理寫 ER 0%、PR 0%、HER2 IHC 2+ but ISH negative、Ki-67 5-14%。請先抽取 patient_patch，並回答這不是 HER2 陽性；不要把 2+ 直接當 HER2+。

Expected patch: `her2_ihc: "2+"`, `her2_fish: "-"`, `her2: "-"`

Actual patch: `her2_ihc: "2+"`, `her2_fish: "negative"`, `her2: "-"`

Failure: Agent understood the clinical meaning, but returned a non-schema value for `her2_fish`. The tool layer should normalize `negative` to `-`.

### adv-011 - Ki-67 less-than value

Question: 請抽取欄位：ER weak positive 1%、PR 0%、HER2 IHC 2+，FISH amplified/positive，Ki-67 <5%。請用 patient_patch 回傳乾淨 schema。

Expected patch: `ki67: "<5"`

Actual patch: `ki67: "5"`

Failure: Agent lost the inequality operator. This matters because Ki-67 categories such as `<5%`, `<14%`, `5-14%`, and `>=20%` should not be collapsed to a plain number.

### adv-012 - Multiple axillary operations

Question: 手術紀錄：neoadjuvant chemotherapy 後接受 SLNB + TAD，frozen section positive，same operation converted to ALND。請抽取腋下手術與 y prefix。

Expected patch: `axillary_surgery: "SLNB,TAD,ALND"`, `post_nac_prefix: "yes"`

Actual patch: `axillary_surgery: "ALND"`

Failure: Agent kept only the final axillary operation and dropped SLNB/TAD. For operative records, the field must support multiple selected procedures.

### adv-013 - ypTNM y-prefix extraction

Question: 手術病理：ypT1c ypN1mi，SLN 1/3 micrometastasis，ALN 0/12，PNI absent，LVI present，margin uninvolved。請抽取 pTNM、淋巴結總數與 PNI/LVI/margin。

Expected patch includes: `post_nac_prefix: "yes"`, `pT: "T1c"`, `pN: "N1mi"`

Actual patch omitted: `post_nac_prefix`

Failure: Agent extracted pT/pN and lymph node counts correctly, but missed that `ypT` / `ypN` implies post-NAC y-prefix.

### adv-014 - DCIS-only residual disease

Question: 病理報告寫：no residual invasive carcinoma, residual DCIS only, nodes negative 0/2。請抽取 post-NAC response 與 pT/pN；不要把 DCIS only 寫成 residual invasive cancer。

Expected patch: `post_nac_response: "DCIS only"`, `pT: "Tis"`, `pN: "N0"`, `nodes_pos: "0"`, `nodes_total: "2"`

Actual patch: `post_nac_response: "residual DCIS only"`, `pN: "N0"`

Failure: Agent captured the concept but did not normalize the value, missed pT `Tis`, and did not emit node count fields.

## Borderline Validator Failure

### adv-004 - Zoladex LA + Femara 30-month cost

Question: Zoladex LA 每三個月一次，加 Femara/Lovizol 自費每天一顆，使用 30 個月總藥費多少？請只用 formulation 資料，且明確用 30.44 天/月換算 30 個月，列出 10.8mg Zoladex LA、Femara/Lovizol、總額與計算式。

Agent answer calculated:

- Zoladex LA: `(30 個月 / 3) * 10,800 = 108,000`
- Femara/Lovizol: `30 * 30.44 * 44 = 40,192.8`
- Total: `148,192.8`

Failure reason: Validator required the wording `10 劑` or `10 次`. The arithmetic was correct, so this should be treated as a benchmark wording issue unless explicit dose count text is required.

## Prompt / Tooling Fix Targets

1. Normalize field values after extraction: `positive/negative/amplified/not amplified` should map to schema values such as `+` and `-`.
2. Preserve inequality and range operators for biomarkers: `<5`, `<14`, `5-14`, `>=20`.
3. Treat axillary surgery as a multi-select field. Do not collapse `SLNB + TAD -> ALND` into only `ALND`.
4. Detect `ypT` / `ypN` as `post_nac_prefix: "yes"`.
5. Normalize DCIS-only residual disease to `post_nac_response: "DCIS only"` and `pT: "Tis"` when no invasive residual carcinoma is present.
6. For arithmetic benchmark questions, separate exact-value validation from wording validation.

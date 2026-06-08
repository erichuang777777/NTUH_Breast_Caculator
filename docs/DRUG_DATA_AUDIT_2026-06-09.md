# Drug Data Audit 2026-06-09

Read-only subagent audit of breast oncology drug data in `data/api/drugs.json`,
`data/api/formulations.json`, and `nhi_drug_coverage.db`.

Status: `Olaparib` / `Lynparza` was fixed in
`data/patches/fix-olaparib-breast-coverage.json`. The remaining rows below are
not yet fixed.

| Drug id | Generic name | Suspected bad fields | Evidence from local data | Likely correction direction | Severity |
|---:|---|---|---|---|---|
| 1732 | Ceritinib | `specialty_id`, indication, tags | Breast specialty row, but indication is ALK+ advanced NSCLC only. | Remove from `oncology_breast` or reclassify to lung/other oncology. | High |
| 1733 | Cetuximab | `specialty_id`, indication, `clinical_tags` | Indication is colorectal/head-neck cancer; tags say `her2: both`, `er_pr: both`. | Remove from breast; clear breast receptor tags. | High |
| 1740 | Erlotinib | `specialty_id`, indication | Indication is EGFR-mutated lung adenocarcinoma/NSCLC only. | Remove from breast or reclassify. | High |
| 1750 | Lenvatinib | `specialty_id`, indication | Indication text is HCC/sorafenib sequence, no breast text. | Remove from breast. | High |
| 1760 | Ramucirumab | `specialty_id`, indication | Indication is AFP-high HCC after sorafenib. | Remove from breast. | High |
| 1765 | Sorafenib | `specialty_id`, indication, `clinical_tags` | RCC/HCC/thyroid/glioblastoma text; tags say `her2: both`, `er_pr: both`. | Remove from breast; clear receptor tags. | High |
| 1730 | Bevacizumab | indication, conditions, tags, duplicate alias | Generic row has colorectal/glioblastoma/ovarian/cervical text and `brca: true`; separate Avastin row 1729 has breast summary. | Keep one breast Bevacizumab/Avastin row with breast indication; move non-breast rule elsewhere. | High |
| 1752 | Niraparib | indication, conditions, tags, formulation gap | Breast row mostly ovarian/FIGO PARP text; breast section names olaparib/talazoparib, not niraparib. No formulation row. | Remove from breast unless a verified breast rule exists; otherwise reclassify gyn PARP data. | High |
| 1766 | Talazoparib | indication, conditions, tags, formulation gap | Row starts with ovarian PARP maintenance and prostate text; breast section is buried. Tags combine `er_pr: positive` and `tnbc: true`; no formulation row. | Replace with breast-only talazoparib rule and correct receptor/HER2 tags; add formulation if used. | High |
| 1756 | Palbociclib | `trade_names`, price, indication | `trade_names` is `ribociclib`; formulation says Palbociclib/Ibrance 125mg cap NHI 3665, drug row says 3520. | Set trade to Ibrance; sync price; separate palbociclib-specific rule text from ribociclib text. | High |
| 1761 | Ribociclib | `trade_names`, price, indication | `trade_names` is lowercase `ribociclib`; formulation says Kisqali 200mg tab NHI 1254, drug row says 2500. | Set trade to Kisqali; sync price; avoid copied palbociclib/fulvestrant sections if not applicable. | High |
| 1739 / 1769 | Enhertu / Trastuzumab deruxtecan | duplicate aliases, price/coverage, tags | Drug rows say NHI price 95263/100mg vial; formulation says `nhi_price: null`, `nhi_covered: 0`, NTUH 29771. Tags only `her2: positive` despite HER2-low indication text. | Reconcile covered/self-pay status and price source; represent HER2-positive and HER2-low contexts; keep one canonical drug row. | High |
| 1773 | Phesgo | price/coverage semantics | Drug row has `nhi_price: 76241` but indication/conditions say健保未給付/自費; formulations have `nhi_price: null`, `nhi_covered: 0`, NTUH loading/maintenance prices. | Store this as self-pay/NTUH price, not NHI price; preserve loading vs maintenance. | High |
| 1742 | Exemestane | copied indication/conditions | Conditions include max daily dose `2.5mg`, clearly from letrozole/anastrozole, while Exemestane dose is 25mg/day. | Remove copied AI blocks and keep exemestane-specific conditions. | High |
| 1724 / 1759 | Alpelisib / Piqray | duplicate aliases, price/formulation | Drug row: 1800 `150mg/tab`, dose 300mg/day; formulation row: `250mg daily (200+50mg)` and NHI 34104/box. | Decide whether price is per tab or package; align formulation/dose; keep one canonical row. | Medium-High |
| 1749 / 1771 | Lapatinib / Tykerb | duplicate aliases, price | Drug rows say 73/250mg tab; formulation says 351/250mg tab. | Reconcile price source; keep canonical generic + trade alias. | Medium-High |
| 1747 / 1768 | Herceptin / Trastuzumab | duplicate aliases | Two breast rows for same product/generic; one coverage rule is empty while generic row has full rule. | Merge into canonical Trastuzumab row with Herceptin as trade name. | Medium |
| 1748 / 1770 | Kadcyla / Trastuzumab emtansine | duplicate aliases | Exact duplicate clinical data under brand and generic. | Keep one canonical row; preserve both trade/generic search terms. | Medium |
| 1757 / 1758 | Perjeta / Pertuzumab | duplicate aliases | Exact duplicate rows. | Keep generic Pertuzumab with Perjeta trade alias. | Medium |
| 1721 / 1741 | Afinitor / Everolimus | duplicate aliases, copied non-breast conditions | Same row duplicated; indication/conditions include RCC, NET, TSC, with breast only as one section. | Keep Everolimus/Afinitor canonical row; trim/split breast-specific conditions. | Medium |
| 1725 / 1727 | Anastrozole / Arimidex | duplicate aliases | Exact duplicate brand/generic rows. | Merge into Anastrozole with Arimidex as trade name. | Medium |
| 1764 | Sacituzumab govitecan | `clinical_tags`, line simplification | Indication includes TNBC and HR+/HER2- disease; tags only `tnbc: true`, `her2: negative`. | Add HR+/ERPR-positive context or split rule contexts; verify line metadata for each indication. | Medium |
| 1774 | Pembrolizumab | `stage`, indication scope | Indication is early TNBC KN522; stage also includes `advanced,metastatic`, while text says metastatic TNBC must be separately confirmed. | Limit structured stage/tags to verified covered indication, or split early vs metastatic contexts. | Medium |
| formulation only | Abemaciclib / Verzenio | missing drug row | Present in `formulations.json`, absent from `drugs.json`. | Add/restore breast drug coverage row or mark formulation-only intentionally. | Medium |
| formulation only | Tucatinib / Tukysa | missing drug row, possible price anomaly | Present only in formulations; `nhi_price: 240`, `ntuh_price: 28800` for 150mg tab. | Add drug row if covered; verify whether 240 is per-tab and 28800 is package/course. | Medium |
| formulation only | Neratinib / Nerlynx | missing drug row | Present in formulations, absent from drugs. | Add drug coverage row or mark formulation-only. | Medium |
| formulation only | Atezolizumab / Tecentriq | missing drug row | Present in formulations/immunotherapy, absent from breast drug coverage. | Add breast indication if intended, or remove from breast formulations. | Medium |

## Systemic Weaknesses

- `api_export.py` exports joined `coverage_rules` without semantic validation, so copied or off-specialty rules become public API fields.
- `tools/check_api.py` checks row counts and endpoint availability, but not breast-domain consistency, duplicate alias pairs, orphan formulations, receptor/tag contradictions, or price agreement.
- The data model allows brand names as separate `generic_name` rows, creating duplicates and polluted search results.
- `drug_formulations` and `drugs` are not reconciled by a canonical drug key, so prices and coverage can drift independently.


# TODO — current backlog

> Updated after commit `66f00cf` and the follow-up Dashboard cleanup.
> Main Dashboard mode is implemented in `index.html`; this file now tracks only remaining work.

---

## Done

- [x] Workspace Dashboard mode toggle (`toggleDashboardMode`)
- [x] Dashboard/Form mode persistence in `localStorage`
- [x] Responsive Dashboard two-column layout
- [x] Dashboard result grid and result-card component
- [x] Dashboard cards for AJCC, CTS5, PREDICT, NPI, Magee, IHC4, subtype, ICD-10, catastrophic illness, BSA/CrCl
- [x] Dashboard cards for PEPI, H-score, RCB, Gail
- [x] Pure calculator helpers for CTS5, PEPI, NPI, Magee, IHC4, H-score, RCB, Gail, and PREDICT Dashboard use
- [x] Workspace summary no longer depends on Dashboard DOM ids for subtype / ICD
- [x] Workspace `setPatientField()` refreshes Dashboard immediately
- [x] JSON export/import for Workspace
- [x] Integrated Workspace print summary
- [x] Broad Dark Mode CSS coverage for new Dashboard/result elements
- [x] Experimental outpatient explanation summary module (`patientJourney`, 開發中)

---

## Next Priority

### 1. Browser smoke test

Run the app locally and verify:

- [ ] Workspace opens without console errors
- [ ] Patient Journey module opens from landing page when Beta features are enabled
- [ ] Patient Journey refreshes from current Workspace data
- [ ] Form mode / Dashboard mode toggle works
- [ ] Dashboard mode persists after refresh
- [ ] Editing Workspace fields updates all cards
- [ ] Missing-data cards show useful "需 ..." messages
- [ ] Clicking calculator cards opens the matching calculator tab
- [ ] `產生整合摘要` shows correct subtype and ICD-10
- [ ] `匯出 JSON` / `匯入 JSON` still work
- [ ] Ctrl+D Dark Mode still works

### 2. Responsive audit

Test these viewport sizes:

- [ ] iPhone SE: 375 x 667
- [ ] iPhone 14 Pro: 393 x 852
- [ ] Android compact: 360 x 640
- [ ] iPad: 768 x 1024
- [ ] iPad Pro: 1024 x 1366

Watch for:

- [ ] Workspace input grid too cramped
- [ ] Dashboard cards overflowing or becoming too narrow
- [ ] Calculator tab row wrapping poorly
- [ ] Issue modal outside viewport
- [ ] Settings panel outside viewport
- [ ] AJCC biomarker section horizontal overflow
- [ ] Trials list readability on mobile
- [ ] Surgery self-pay table line-height / wrapping

### 3. Dark Mode visual audit

Manually inspect:

- [ ] Issue Report modal
- [ ] Settings panel
- [ ] AJCC v9 lookup result panel
- [ ] PREDICT success banner
- [ ] All 9 calculator tabs
- [ ] Workspace Dashboard cards
- [ ] Module badges
- [ ] Standalone validation harness (`tests/predict_validation_auto.html`)

### 4. Dashboard clinical data gaps

Some Dashboard cards are present but cannot fully calculate from current Workspace fields:

- H-score needs 0/1+/2+/3+ staining percentages.
- RCB needs tumor bed dimensions, invasive carcinoma %, positive LN count, and largest LN metastasis.
- Gail currently uses simplified defaults for missing reproductive/family-history inputs.
- PEPI uses current Workspace pathology as a near-term approximation; true PEPI needs post-neoadjuvant endocrine pathology.

Potential next implementation:

- [ ] Add optional Dashboard-only advanced pathology inputs, or
- [ ] Add "Load from calculator detail tab" workflow, or
- [ ] Keep these cards as explicit missing-data/approximation cards.

### 5. Patient-centered explanation module

Current scope: a lightweight, experimental explanation layer for NP/physician use while facing patients. It summarizes existing Workspace data and does not make treatment recommendations.

- [x] Owner decision: module title is `門診說明摘要`
- [x] Owner decision: keep landing-page card during experiment; mature version should likely become a Workspace subview
- [x] Owner decision: keep `patientJourney` disabled by default while it is marked 開發中
- [x] Owner decision: mixed wording, operated by NP/physician but understandable to patients
- [x] Owner decision: journey stages are diagnosis/staging, neoadjuvant, surgery, adjuvant, metastatic/follow-up
- [x] Owner decision: soften catastrophic illness wording; avoid "可能不符合" in this patient-facing explanation module
- [x] Owner decision: keep simplified model outputs (PREDICT/CTS5/etc.) out of this module for now
- [ ] Review wording with NP/physician workflow: concise, patient-facing, non-decisional
- [ ] Add print-specific layout for a one-page patient explanation sheet
- [ ] Add visual treatment journey refinements after real clinic feedback
- [ ] Decide whether this remains a landing-page module or becomes a Workspace subview
- [ ] Keep future Share Decision Making separate until options/preferences/documentation are ready

---

## Later Backlog

- [ ] PREDICT v4.0 upgrade investigation, including radiotherapy support
- [ ] MSK nomograms: SLN and Non-SLN models if coefficients can be sourced
- [ ] Modularize `index.html` according to `ARCHITECTURE.md`
- [ ] Configure Netlify branch deploy previews
- [ ] Keyboard shortcuts: Esc, 1-9, `/`, `?`
- [ ] Print/PDF layout polish for integrated case summary

---

## Verification Commands

```powershell
git diff --check
python -m pytest tests
```

Full `python -m pytest` currently also collects untracked `NCCN_Breast_KG/tests`, which expect a separate `src` package and fail collection unless that project is configured separately.

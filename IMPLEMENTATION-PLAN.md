# Implementation Plan — Clinical Accuracy Remediation

**Driver:** `FINAL-clinical-accuracy-audit-and-solutions.md`
**Contracts:** `bone_age_product_starter_pack/` (case input, per-bone annotation, report output, licensed loader, validation protocol)
**Working style:** one item at a time, end-to-end (code → test → verify → commit) on a feature branch. No push/PR unless asked.
**Decisions locked with product owner (2026-07-12):** resources = schemas/contracts only (no licensed values, no films, no validation cohort yet — build to the contracts, leave licensed values loadable-but-empty) · QRISK3 = keep + validate · start = safe code fixes first · delivery = feature branch + tests.

---

## Principles (how a senior dev runs this)

1. **Never guess clinical data.** Every data-gated item ships the *loader, gate, schema, and test* now; the values stay empty and the feature stays disabled until lawful data is entered — matching the codebase's existing discipline.
2. **One reversible commit per item**, each with its own test, each leaving the suite green.
3. **Correctness before capability.** Fix wrong numbers first (they actively mislead), then build new capability.
4. **Gate, don't caveat.** Unvalidated/uncertain outputs abstain, not footnote.
5. **Align to the starter-pack contracts** so today's work is tomorrow's licensed-mode work.

---

## Phase 0 — Setup ✅ (this session)
- Feature branch `fix/clinical-accuracy-remediation` off `main` (carries existing uncommitted work forward).
- Establish green test baseline (venv pytest).
- Record baseline in this plan.

## Phase 1 — Safe self-contained correctness fixes (no external data)
> These are wrong-number / mislabel bugs that actively mislead today. Highest priority.

- **1.1 — Pin `rcpchgrowth`** (GC-7). Upper-bound the dependency to the validated 4.5.0 so chart output can't drift on an upgrade. *Test:* installed version assertion. **Risk: minimal.**
- **1.2 — Fix the `(P75−P25)/2` SD bug** (F-2). Backend: extend `/api/growth/reference-stats` to return true `L,M,S`. Frontend (`index.html:487,1512,1514`): compute z from the real distribution (or divide IQR by 1.349, not 2) so adult-height percentiles stop being exaggerated ~1.48×. *Test:* z-score parity vs backend LMS on golden ages.
- **1.3 — Split "Predicted Adult Height" from "Mid-Parental Target"** (F-1, `index.html:1497`). Three distinct rows: genetic target (+channel), skeletal prediction (disabled until licensed table, with interval), and their difference. Prediction never falls back to mid-parental. *Test:* frontend logic unit (via existing frontend test harness) — target ≠ prediction.
- **1.4 — Unify growth display vs scoring inversion** (GC-3/4). Backend `blend.py`: make `unified_z_for_value` the exact numeric inverse of `unified_value_at_z` in the pure-IAP region too (extend the existing `brentq` pattern), so a point on a drawn centile gets exactly that centile. *Test:* full-grid forward→inverse consistency within tolerance.
- **1.5 — Surface & gate the WHO↔IAP composite** (GC-2/3). `validation.py`: report per-centile max boundary value-jump and treat > tolerance as a gating failure; label the 3–5 y span "product-derived WHO/IAP composite" in the API `reference` string + PDF legend. *Test:* discontinuity metric present and bounded.

## Phase 2 — Data-integrity foundation
- **2.1 — Growth CSV provenance + checksum + source-verification test** (GC-1). Add `PROVENANCE.md`, a checksum manifest, and `tests/growth/test_iap_source.py` hard-coding the published IAP 2015 values and asserting every CSV cell. *(Published values: I fetch from the paper via literature tools, you confirm.)*
- **2.2 — `reference_cases` gate for TW3-C** (S-BA-2 pt1). Extend `tw3_tables.json` + `tables.py` so the provisional curve can only clear its "provisional" flag once it reproduces entered reference films within tolerance. Values empty until you supply films.

## Phase 3 — Bone-age accuracy & reporting (align to report_output_schema.json)
- **3.1 — Detailed 20-bone report** (S-BA-4). Compose from existing `/score` + `letters-score` (RUS/carpal/TWII′20 kept separate). Per-bone: name, code, stage, points, %-of-max, confidence, manual override, accepted flag → matches `report_output_schema.json` `per_bone_results[]`.
- **3.2 — Image-quality + OOD gate** (S-BA-6). `backend/ai/image_qa.py` called before inference; emits `case_input_schema.json` `quality_flags`; hard-fail ⇒ abstain ("manual assessment required"), per validation_protocol §4. *No silent normal report after a quality failure.*
- **3.3 — Conformal uncertainty** (S-BA-5). Split-conformal band on the val set → `prediction_interval_months` in the report schema; replace ±MAE. *(Needs the `.onnx` + val images present — verify in Phase 3.)*
- **3.4 — TW3-C self-calibration harness** (S-BA-2 pt2). Offline job: pair approved ages + RUS scores from the feedback flywheel (reuse consensus/adjudication), fit monotone PCHIP, gate on N/spread/beat-incumbent. Scaffolded now; activates as feedback accrues.

## Phase 4 — Licensed tables + validation infrastructure
- **4.1 — Wire `licensed_reference_loader.json` contract** into the letters loader; provenance-required + checksum + reference-case gate before scoring enables.
- **4.2 — Frozen golden-set + `backend/ai/evaluate.py`** computing validation_protocol §5 metrics (MAE, median AE, RMSE, bias 95% CI, Bland–Altman, % within ±3/6/9/12 mo, subgroup breakdowns) against §6 engineering gates. Release-gate models on it.

## Phase 5 — QRISK3 hardening (keep + validate)
- **5.1** — Relocate to `backend/cvd/qrisk3.py`; `tests/cvd/test_qrisk3_golden.py` parity vs official ClinRisk vectors (both sexes, ethnicity, smoking, interactions, boundaries, survivor, clamping, missing-data); enforce eligibility server-side (`available:false` outside 25–84 / missing required inputs); return `imputed_fields`; visibly separate the adult module in the UI.

## Phase 6 — Cross-cutting
- **6.1** — Provenance/version/checksum + uncertainty stamped on every result and PDF export.
- **6.2** — Height-velocity module (`backend/growth/velocity.py`) from serial visits (exact elapsed days, min-interval, technique-change flag); distinct from cross-sectional slope.

---

## Progress log
- **Phase 0:** ✅ branch `fix/clinical-accuracy-remediation` created; baseline **39 passed**; checkpoint commit `31b869a`.
- **Item 1.1** (pin `rcpchgrowth`): ✅ done — commit `b47f5c9`, +2 tests green.
- **Item 1.2** (SD bug F-2): ✅ done — commit `78187ed`. PAH percentile now inverts the real LMS distribution (exact at published centiles); `spreadFromSeries` uses IQR→SD 1.349. +6 parity tests; frontend + growth suite **47 passed**; live app zero console errors.
- **Item 1.3** (split PAH vs mid-parental target, F-1): ✅ done — commit `9ede9f5`. Target, calibration-gated skeletal prediction, and their difference are now distinct; prediction never borrows the target. Verified live (boy 178/165 → target 178.0 cm @ 57.9th centile, prediction card = "calibration required"). +5 source-guard tests.
- **Item 1.4** (unify growth display vs scoring inversion, GC-3/4): _next_.

# Plan 5 — Validation & Release-Gate Infrastructure

**Status:** Ready to implement (infra now; external run data-gated) · **Owner:** (assign) · **Created:** 2026-07-13
**Branch target:** dedicated `feat/validation-release-gates`
**Why this is written before Plan 4:** it is the **dependency** the gates in [PLAN-2](PLAN-2-self-learning-flywheel.md) (WI-7 release harness) and [PLAN-3](PLAN-3-screening-model-accuracy.md) (WI-8) both call. Those plans *invoke* an evaluator and a gate; **this plan builds them.** Until it exists, "beat the incumbent, no subgroup regression, calibrated, signed off" is a sentence, not a check.

> **How to use this document.** Self-contained implementation source. Read §2 first. The honest split that governs this whole plan: the **infrastructure, the pre-registered protocol, and the internal gates are buildable now**; the **external Indian clinical validation *run* is data-gated** (you have no cohort yet). So we build the machine and the acceptance criteria now, and the cohort plugs in later — the same "loader/gate/schema/test now, values entered lawfully later" discipline the rest of the repo already follows.

---

## 1. Purpose (why this plan)

Right now the product can measure a single number (`val_mae_months: 8.6`) and a conformal coverage — but it cannot answer the questions that decide whether a model is safe to ship or a claim is honest: *Does it hold up on a test set it has never touched? Is it worse for one sex or age band? Is the uncertainty actually calibrated? Does a new model beat the current one without regressing any subgroup?* Those are the questions `validation_protocol.md §5–6` and the master audit `§3.4 / §6 / §7` were written around, and none of them are computable today.

This plan builds the **evaluation + gate layer**: a frozen test-set registry with a leak guard, a metric evaluator (whole-hand age *and* per-bone staging) with subgroup stratification, encoded engineering gates, a release-gate engine that returns a PASS/FAIL verdict with reasons, and a validation-report generator that is the backbone of any future regulatory submission. It is what turns "we think it's accurate" into "here is the locked test, the subgroup table, the calibration curve, and the gate result."

Two honesty rules run through it:
- **A passing *internal* test is not a clinical accuracy claim.** External Indian performance (WI-8's run) is required before any such claim — this plan makes that a gate, not a footnote.
- **Acceptance criteria are pre-registered** (fixed before results are seen), so validation cannot be retrofitted to whatever number came out.

---

## 2. Current state — gap analysis

**Exists and is reusable:**

| Capability | Where | State |
|---|---|---|
| Split-conformal calibration + empirical coverage check | `backend/ai/conformal.py`, `calibrate_conformal.py` | ✅ (marginal only) |
| Patient-level split with in-export leak refusal | `export_dataset.py::_assert_no_patient_overlap` | ✅ (within one export) |
| Live AI-vs-human MAE + trend + method/domain/confidence breakdown | `feedback/stats` | ✅ (monitoring, not validation) |
| Multi-rater consensus + agreement (Po) | `backend/tw3/consensus.py` | ✅ (inter-reader building block) |
| Generic validation protocol (metrics, gates, subgroups, reporting rules) | `bone_age_product_starter_pack/validation_protocol.md` | ✅ reference |
| Curve reference-case validation (TW3-C) | `scoring.validate_curve` | ✅ (engine, not model) |
| Growth transition validation | `backend/growth/validation.py` | ✅ (growth-only) |

**Missing — everything this plan builds:**

1. **No frozen test-set registry, and no *cross-artifact* leak guard.** The conformal code uses the training **val** split (used for model selection) as its calibration set — that is a *tuning* set, not a **locked test** set (`validation_protocol.md §3` distinguishes train / tune / internal-test / external-test). There is no registry of test patients, and no assertion that a test patient never appears in training/tuning/feedback/calibration. → **WI-1**
2. **No metric evaluator.** No MAE/median/RMSE/signed-bias-with-CI/Bland–Altman/percent-within-bands/calibration/abstention computation. `backend/ai/evaluate.py` does not exist. → **WI-2**
3. **No subgroup stratification.** No per-sex / age-band / domain / site / diagnosis breakdown with worst-case flags. → **WI-3**
4. **No per-bone staging metrics.** No exact-stage accuracy, within-1, weighted kappa, confusion matrices, ordinal distance, model-reader agreement. → **WI-4**
5. **No encoded gates.** `validation_protocol.md §6` thresholds live only in prose. → **WI-5**
6. **No release-gate engine.** Nothing compares candidate vs incumbent and returns a verdict. → **WI-6**
7. **No validation report.** No machine + human artifact. → **WI-7**
8. **No pre-registered protocol instance** with fixed acceptance criteria for *this* product. → **WI-8**

---

## 3. Target architecture

```
     ┌──────────────────────────── FROZEN TEST REGISTRY (WI-1) ────────────────────────────┐
     │ locked_test.json: patient_ids + image_hashes + checksum · NEVER in train/tune/feedback │
     │ leak guard: assert(test ∩ (train ∪ val ∪ feedback ∪ calib) = ∅) — refuses otherwise    │
     └───────────────────────────────────────┬───────────────────────────────────────────────┘
                                              │ predictions on the locked test
                                              ▼
     ┌───────────────────── EVALUATOR (backend/ai/evaluate.py) ─────────────────────────────┐
     │ whole-hand age (WI-2):  MAE · medianAE · RMSE · signed bias +95%CI · Bland–Altman     │
     │                         · % within ±3/6/9/12mo · conformal coverage · abstention rate │
     │ per-bone staging (WI-4):exact-acc · within-1 · weighted-κ · confusion · ordinal dist  │
     │                         · macro/micro · model-reader agreement · confidence calib     │
     │ subgroups (WI-3):       × sex × age-band × image-domain × site/scanner × diagnosis     │
     └───────────────────────────────────────┬───────────────────────────────────────────────┘
                                              ▼
     ┌──────────────────── ENGINEERING GATES (WI-5, versioned thresholds) ───────────────────┐
     │ MAE ≤6mo · no subgroup MAE >9mo · ≥90% within ±12mo · overall κ ≥0.80 ·                │
     │ no bone κ <0.70 without review · zero-release on image-gate-fail · 100% clinician review│
     └───────────────────────────────────────┬───────────────────────────────────────────────┘
                                              ▼
     ┌──────────────── RELEASE-GATE ENGINE (WI-6) — called by Plan2 WI-7 / Plan3 WI-8 ────────┐
     │ verdict = beat_incumbent ∧ no_subgroup_regression ∧ calibrated ∧ all_gates_pass         │
     │ returns PASS/FAIL + per-check reasons + the report; sign-off/persistence = Plan 2       │
     └───────────────────────────────────────┬───────────────────────────────────────────────┘
                                              ▼
     ┌──────────────── VALIDATION REPORT (WI-7): JSON + human HTML/PDF ───────────────────────┐
     │ metrics · subgroup tables · Bland–Altman · calibration curve · confusion matrices ·     │
     │ gate results · provenance (model/table/data versions + checksums) — regulatory backbone │
     └────────────────────────────────────────────────────────────────────────────────────────┘
                     ▲                                                          ▲
   PRE-REGISTERED PROTOCOL (WI-8): cohort, readers, subgroups, metrics,   internal test now;
   gates — acceptance criteria FIXED before results are seen.            EXTERNAL Indian run data-gated.
```

**Invariants:**
- The locked test set is touched **only** by evaluation — never training, tuning, calibration, or feedback (enforced by the leak guard, tested).
- Acceptance criteria are pre-registered and versioned; a gate threshold change is a reviewed, logged event, not an inline tweak.
- Internal pass ≠ clinical claim; the external-cohort gate stays red until a real Indian validation run exists.
- Every report stamps model/table/data versions + checksums so a result is reproducible and auditable.

---

## 4. Artifacts & data model

- **`backend/ai/validation/locked_test.json`** — `{ "dataset": "...", "patient_ids": [...], "image_hashes": [...], "checksum": "sha256…", "frozen_at": "...", "source": "internal-rsna | external-india" }`. The single source of truth for what is off-limits to training. *(WI-1)*
- **`backend/ai/validation/gates.json`** — versioned engineering-gate thresholds (from `validation_protocol.md §6`), with a `protocol_version`. *(WI-5)*
- **`ValidationReport` (JSON schema)** — metrics + subgroups + gate results + provenance; the machine artifact behind the human report. *(WI-7)*
- **Pre-registered protocol doc** `backend/ai/validation/PROTOCOL.md` — the concrete, versioned acceptance criteria. *(WI-8)*
- Reuses Plan 2's `ModelRelease` row for persistence (this plan returns the verdict + report; Plan 2 stores it and captures sign-off).

---

## 5. Work items

Each item = one reversible, tested commit; suite stays green. Evaluator/gate code is **pure** (no I/O, no model calls) so it is unit-testable on synthetic arrays without a GPU or a model file.

### WI-1 — Frozen test-set registry + cross-artifact leak guard  *(foundation)*
- **Why:** every downstream number is meaningless if the test set leaked into training. Today only *within-export* patient overlap is checked; there is no locked test registry and no check against training/feedback/calibration.
- **How:** create `locked_test.json` (patients + image hashes + checksum). Add `backend/ai/validation/leak_guard.py`: `assert_disjoint(test, {train, val, feedback, calibration})` by patient **and** image hash; raises and refuses to evaluate on any overlap. Carve a **locked internal RSNA test** distinct from the conformal val split (so calibration and testing use different data).
- **Files:** `backend/ai/validation/locked_test.json`, `backend/ai/validation/leak_guard.py`, tests.
- **Tests:** a planted overlap (same patient or hash in test and train) raises; a clean split passes; checksum detects tampering.
- **Acceptance:** evaluation refuses to run on a leaked test set.

### WI-2 — Whole-hand age metric evaluator  *(core)*
- **Why:** the metrics `validation_protocol.md §5` requires, none of which exist.
- **How:** `backend/ai/evaluate.py::evaluate_age(preds, targets, intervals=None)` → MAE, median AE, RMSE, signed bias + **bootstrap 95% CI**, Bland–Altman mean-diff + limits of agreement, % within ±3/6/9/12 mo, conformal **empirical coverage vs target**, and abstention rate. Pure numpy; deterministic.
- **Files:** `backend/ai/evaluate.py`, `tests/bone_age/test_evaluate_age.py`.
- **Tests:** known synthetic residuals produce hand-verified MAE/RMSE/bias/CI/coverage; empty/degenerate inputs handled.
- **Acceptance:** all §5 whole-hand metrics computed and unit-verified.

### WI-3 — Subgroup stratification engine  *(core)*
- **Why:** an acceptable average can hide an unacceptable subgroup — the master audit's central bias concern (`BA-03`).
- **How:** `evaluate.py::evaluate_by_subgroup(records, by=[...])` runs WI-2 over sex, age band (`validation_protocol.md §3` bands), image domain, site/scanner, diagnosis group; returns per-cell metrics + a **worst-subgroup flag** and clinically-important worst cases. Small cells labelled "insufficient n."
- **Files:** `backend/ai/evaluate.py`, tests.
- **Acceptance:** per-subgroup table with worst-case flags; underpowered cells are marked, not silently passed.

### WI-4 — Per-bone staging metric evaluator  *(for Plan 4)*
- **Why:** the auto-stager (Plan 4) needs staging metrics `validation_protocol.md §5` + master audit `§3.4`: exact-stage accuracy, within-one, **quadratic-weighted kappa**, per-bone confusion matrix, ordinal stage distance, macro/micro accuracy, model-reader agreement, confidence calibration, abstention rate.
- **How:** `backend/ai/evaluate.py::evaluate_staging(pred_stages, ref_stages, per_bone=True)`; consumes consensus reference labels from `consensus.py`. Carpals evaluated + gated separately.
- **Files:** `backend/ai/evaluate.py`, tests (synthetic confusion cases with hand-computed kappa).
- **Acceptance:** per-bone staging metrics computed; kappa matches hand calculation; carpals separable.

### WI-5 — Encoded engineering gates  *(core)*
- **Why:** turn `validation_protocol.md §6` prose into machine-checkable pass/fail with the measured value beside each threshold.
- **How:** `backend/ai/validation/gates.py` reads versioned `gates.json` and evaluates: MAE ≤ 6 mo (locked test); no sex/age/site subgroup MAE > 9 mo; ≥ 90% within ±12 mo; overall staging κ ≥ 0.80; no bone κ < 0.70 without mandatory-review flag; zero-release when the image-quality gate failed; 100% clinician review in pilot. Each returns `{gate, threshold, measured, passed}`.
- **Files:** `backend/ai/validation/gates.py`, `gates.json`, tests.
- **Acceptance:** each gate green/red with its number; thresholds are versioned, not inline.

### WI-6 — Release-gate engine  *(the callable Plan 2/3 depend on)*
- **Why:** the single entry point that decides whether a candidate may ship.
- **How:** `backend/ai/validation/release_gate.py::evaluate_candidate(candidate_preds, incumbent_preds, test_registry)` → runs leak guard (WI-1) → evaluator (WI-2/3/4) → gates (WI-5) → computes **beat-incumbent** (by a pre-registered margin) and **no-subgroup-regression** and **calibration-ok**; returns a `Verdict{passed, reasons[], report}`. Persistence + human sign-off = Plan 2's `ModelRelease`/`release.py`; this returns the verdict and report only.
- **Files:** `backend/ai/validation/release_gate.py`, tests (a candidate that regresses one subgroup FAILS; one that clearly wins PASSES).
- **Acceptance:** Plan 2 WI-7 and Plan 3 WI-8 call this and get a reasoned PASS/FAIL; no candidate ships on a subgroup regression.

### WI-7 — Validation report generator  *(regulatory backbone)*
- **Why:** the auditable artifact `validation_protocol.md §5` + master audit `§7` describe.
- **How:** `backend/ai/validation/report.py` emits a `ValidationReport` JSON + a human HTML/PDF: headline metrics, subgroup tables, Bland–Altman, calibration curve, per-bone confusion matrices, every gate result, and full provenance (model version, table version + checksum, dataset manifest checksum, protocol version). Reuse the growth PDF/HTML approach (`backend/growth/qa_report*`).
- **Files:** `backend/ai/validation/report.py`, template, tests.
- **Acceptance:** a run produces a self-describing report a reviewer could act on; provenance is complete.

### WI-8 — Pre-registered validation protocol instance  *(data-gated run; doc now)*
- **Why:** master audit `P0.4` — a pre-registered, multi-centre Indian external validation set with **acceptance criteria fixed before results**. Pre-registration is what makes the eventual claim credible.
- **How:** author `backend/ai/validation/PROTOCOL.md` from `validation_protocol.md`: exact cohort definition (normal + GHD + constitutional delay + precocious puberty + hypothyroid + Turner + chronic disease + treated/untreated follow-up, per §7), ≥2 blinded readers + adjudication + repeat reads, the subgroups, the metrics, the gates (WI-5), and the freeze procedure (WI-1). Version it; changes are logged. The **run** waits on the cohort; the criteria are locked now.
- **Files:** `backend/ai/validation/PROTOCOL.md`.
- **Acceptance:** a versioned protocol with pre-registered acceptance criteria exists; the external run is clearly marked data-gated.

---

## 6. Sequencing

```
WI-1 (frozen test + leak guard) ─▶ WI-2 (age metrics) ─▶ WI-3 (subgroups) ─▶ WI-5 (gates) ─▶ WI-6 (release engine)
                                                                                                 │
                                          WI-4 (per-bone staging metrics) ──────────────────────┤ (needed by Plan 4)
                                                                                                 ▼
                                                              WI-7 (validation report) ─▶ WI-8 (pre-registered protocol)
```
Recommended order: **WI-1 → WI-2 → WI-3 → WI-5 → WI-6 → WI-4 → WI-7 → WI-8.** WI-6 (release engine) as early as possible — it unblocks the gates that Plans 2 and 3 are already written to call. WI-4 alongside Plan 4. WI-8 authored now, executed when a cohort exists.

---

## 7. Test & verification plan

- **Unit:** pure evaluator/gate math verified on synthetic arrays with hand-computed expected values (MAE, RMSE, bias CI, coverage, kappa). Keep existing suite green.
- **Integration:** a synthetic candidate-vs-incumbent run through `release_gate` — one clean win (PASS), one subgroup regression (FAIL), one leaked test (REFUSES).
- **Negative controls (stay red-when-broken):** leaked test → refuse; subgroup MAE > 9 mo → gate fails; conformal empirical coverage below target → calibration gate fails; missing provenance → report incomplete.
- **No browser step** (this plan has no interactive surface beyond the generated report); verification is the report artifact + green tests.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Test-set leakage inflates every metric | Frozen registry + cross-artifact leak guard (WI-1), tested. |
| Good average hides a bad subgroup | Mandatory subgroup gates + worst-case flags (WI-3, WI-5). |
| Acceptance criteria retrofitted to results | Pre-registered, versioned protocol + gates (WI-8, WI-5). |
| Internal pass mistaken for clinical validity | External-cohort gate stays red until a real Indian run; report says so explicitly. |
| Underpowered subgroups over-interpreted | "insufficient n" labelling; no pass on underpowered cells. |
| Calibration drift unnoticed | Empirical-coverage gate in every run (WI-2). |
| Thresholds silently loosened | Versioned `gates.json`; changes logged/reviewed. |

---

## 9. Definition of Done

- [ ] A frozen locked-test registry exists; evaluation refuses on any train/tune/feedback/calibration leak (WI-1).
- [ ] Whole-hand age metrics (MAE, median, RMSE, signed bias + 95% CI, Bland–Altman, % within bands, coverage, abstention) computed + unit-verified (WI-2).
- [ ] Metrics stratified by sex, age band, domain, site, diagnosis with worst-case flags (WI-3).
- [ ] Per-bone staging metrics (exact, within-1, weighted κ, confusion, ordinal distance, agreement, calibration) computed, carpals separable (WI-4).
- [ ] Engineering gates encoded + versioned; each returns threshold vs measured (WI-5).
- [ ] Release-gate engine returns a reasoned PASS/FAIL that Plans 2 & 3 call; no ship on subgroup regression (WI-6).
- [ ] A self-describing validation report (JSON + human) with full provenance is generated (WI-7).
- [ ] A pre-registered, versioned protocol with fixed acceptance criteria exists; external run marked data-gated (WI-8).
- [ ] Full suite green.

---

## 10. Open decisions to confirm

1. **Locked internal test source:** carve it from the RSNA holdout now (distinct from the conformal val split), or wait for the external cohort? (Recommend: carve an internal RSNA locked test now for the release engine; keep external separate.)
2. **Beat-incumbent margin:** how much better must a candidate be on the locked test to justify replacing a validated model (e.g. ≥ 0.3 mo MAE and no subgroup regression)?
3. **Gate thresholds:** adopt `validation_protocol.md §6` as-is, or tighten toward the RSNA ~4.2 mo frontier?
4. **External cohort logistics:** site(s), reader panel, adjudication, and consent for the WI-8 run — who and when.
5. **Report format:** HTML only, or HTML + PDF export (reusing the growth QA report stack)?
6. **Diagnosis subgroups:** which pathology groups (`§7` list) are realistically obtainable for stratified reporting.

---

*This plan builds the machine that judges accuracy and governs releases. It does not itself improve any model (Plans 3/4) or enter licensed data (Plan 1); it is the gate they must pass and the evidence a claim rests on. The external Indian validation run is data-gated; its infrastructure and pre-registered criteria are delivered here.*

# Plan 2 — Human-Gated Self-Learning Flywheel

**Status:** Ready to implement · **Owner:** (assign) · **Created:** 2026-07-13
**Branch target:** dedicated `feat/self-learning-flywheel`
**Positioning (locked):** clinician-assist / decision support. The model **never** updates itself live. "Self-learning" here means: clinician corrections and confirmed stages become **labelled evidence**, are **de-noised by multi-rater consensus**, and periodically retrain a model **offline** that must **re-pass validation and human sign-off** before it ships. This is the only design that is safe and clearance-compatible.
**Strategic reason this plan matters now:** you have **no per-bone annotators and no external cohort**. This flywheel is the mechanism that *manufactures the per-bone labelled dataset* as a by-product of normal clinical work — it is the only realistic path to unblocking **Plan 4** (auto per-bone staging). Build the data engine first; the AI that consumes it comes later.

> **How to use this document.** Self-contained implementation source: what to build, how, why, with exact files, tests, and acceptance. Read §3 first — most of the loop's *skeleton* already exists (feedback log, consensus, dataset exporter, coverage endpoint). This plan closes it into a governed loop and builds the two missing load-bearing pieces (localization capture; gated retrain release). External evidence for the monitoring layer comes from [REFERENCE-cpp-skeletal-maturation-study.md](REFERENCE-cpp-skeletal-maturation-study.md).

---

## 1. Purpose (why this plan, why now)

A clinical model that "learns" by silently mutating itself in production is unsafe, un-auditable, and un-clearable. The correct and defensible pattern — and the one this codebase already leans toward — is a **flywheel**: every time a clinician confirms or corrects a result, that becomes *evidence*, not a live weight update. Evidence accumulates, is de-noised by having several experts read the same film, and periodically feeds an **offline** retraining run whose output is treated like any other release candidate: it must beat the incumbent on a **locked** test set, show no subgroup regression, be well-calibrated, and be **signed off by a human** before it is deployed.

Two things make this urgent for *your* situation specifically:
1. **You lack per-bone labelled data and annotators.** The flywheel is how you create that data without hiring a labelling team — it harvests the doctor's normal grading + box-confirmation as training labels. Without it, Plan 4 (auto-staging) can never start.
2. **You lack a validation cohort.** The flywheel's monitoring layer is how you watch accuracy honestly over time (AI-vs-human error, drift) and — using external references like the CPP study — sanity-check that your accumulating data is *plausible*, even before a formal cohort exists.

The invariant that must never break: **a correction is evidence, never a patient result.** The reported bone age changes only when a clinician re-approves it; a model version changes only through the gated release in §WI-7.

---

## 2. Scope

### In scope
- **Attribution:** rater identity on confirmed stages so multi-reader consensus can be computed from real assessments (not only the feedback log).
- **Capture engine:** localization-confirm UI (auto-boxes → doctor adjusts → persisted) — the piece that actually produces per-bone crops; per-bone grade capture with AI-suggestion scaffolding.
- **De-noising:** persisted **adjudication queue** + reviewer workflow built on the existing pure `consensus.py`.
- **Visibility:** a **coverage dashboard** (per-bone×stage readiness) and a **monitoring/drift surface** (AI-vs-human error, subgroup breakdowns, domain drift, plausibility priors from the CPP reference).
- **Governance:** audit events for every flywheel action; de-identification/consent gate before crops leave the box; the "corrections never change the patient result" guarantee surfaced.
- **Gated learning:** offline **retrain → release harness** (freeze → train → evaluate on locked test → beat-incumbent + no subgroup regression + calibration + human sign-off → versioned deploy). **Label-quality activation gates** that decide when a bone's AI suggestion may even be shown.

### Out of scope (cross-referenced)
- **The auto-staging / localizer models themselves** = **Plan 4**. This plan produces their training data and their release gate, and leaves `ai_suggested_stage` / `ai_stage_probabilities` present-but-null for Plan 4 to fill.
- **The metric evaluator** (MAE, Bland–Altman, subgroup, calibration on a locked golden set) = **Plan 5**. WI-7 *invokes* that evaluator; it does not re-implement it (a thin interim evaluator is allowed until Plan 5 lands).
- **Licensed TW3 scoring activation** = **Plan 1**.
- **Screening-model full-RSNA retrain** = **Plan 3** (this plan's release harness is reused by it).

---

## 3. Current state — precise gap analysis

**Already built — reuse, do not rebuild:**

| Capability | Where | State |
|---|---|---|
| Correction intake as evidence (never a result) | `BoneAgeFeedback` model, `POST /api/bone-age/feedback` | ✅ |
| AI-vs-human error + trend + method/domain/confidence breakdowns + per-image consensus/adjudication flag | `GET /api/bone-age/feedback/stats` | ✅ |
| Pure multi-rater per-bone consensus (majority, adjudication, Po agreement) | `backend/tw3/consensus.py` | ✅ |
| Group same-film reads into consensus | `consensus.build_film_consensus` | ✅ |
| Patient-level, leak-refusing dataset export (crops, coverage.csv, consensus.json, versioned manifest+checksum) | `backend/tw3/pipeline/export_dataset.py` | ✅ |
| Live coverage matrix endpoint + support bands (candidate ≥50 / limited ≥25 / experimental ≥10) | `export_dataset.coverage_report` | ✅ |
| Per-bone record fields for the loop (`localisation_box`, `ai_suggested_stage`, `ai_stage_probabilities`, `confirmed_stage`, `stage_confidence`, `doctor_modified_ai_result`, `modification_reason`) | `BoneAssessment` | ✅ schema present |
| Audit table | `AuditEvent` | ✅ present, under-used |
| Training scripts (stager/localizer/screening), conformal calibration | `backend/ai/train_*.py`, `calibrate_conformal.py` | ✅ |

**The real gaps this plan closes:**

1. **No rater identity on confirmed stages.** `BoneAgeFeedback` has `rater_id`, but `BoneAssessment`/`TW3Assessment` do not record *who* confirmed a stage — so consensus can only run on the feedback log, not on the clinical assessments that produce crops. → **WI-1**
2. **Localization is not wired → crops = 0.** `export_dataset` produces crops *only where a `localisation_box` exists*, and `LOCALIZE.md §5` confirms the box UI isn't built. **This is the bottleneck**: no boxes ⇒ no crops ⇒ no per-bone training data ⇒ Plan 4 can never start. → **WI-2**
3. **AI-suggestion capture loop incomplete.** The fields exist but nothing populates `doctor_modified_ai_result` / `modification_reason` / `stage_confidence` on save, and no `AuditEvent` is emitted per confirmation. → **WI-3**
4. **Consensus is pure logic with no persisted queue or reviewer workflow.** `consensus.py`'s own docstring defers "rater identity in the schema, an adjudication queue/UI." → **WI-4**
5. **No clinician-facing coverage or monitoring dashboards.** The endpoints exist; the surfaces don't. → **WI-5, WI-6**
6. **No formal offline retrain → gated release.** `RETRAIN.md`/`STAGE.md` describe steps but there is no code that *enforces* freeze → locked-test → beat-incumbent → sign-off → versioned deploy, and no incumbent-vs-candidate comparator. → **WI-7**
7. **No label-quality interlock** deciding when a bone's AI suggestion may be shown (support + consensus + calibration). → **WI-8**
8. **Governance gaps:** de-id/consent status isn't gated before export; most flywheel actions don't audit. → **WI-9**

---

## 4. Target architecture — the closed loop

```
        ┌──────────────────────── CLINICAL USE (unchanged safety) ───────────────────────┐
        │  upload film → acceptability gate (built) → [Plan4 AI boxes+stages, when ready] │
        │  → doctor confirms/corrects each bone stage (+ optional box nudge)              │
        └───────────────┬───────────────────────────────────────────────┬────────────────┘
                        │ patient's reported age = clinician-approved     │ every action → AuditEvent (WI-9)
                        ▼ (Plan 1 engine)                                 ▼
          ┌─────────────────────────────┐          ┌──────────────────────────────────────┐
          │ EVIDENCE (never a result)   │          │ CAPTURE                               │
          │  BoneAgeFeedback (corrections)│        │  BoneAssessment.confirmed_stage +      │
          │  + rater_id                  │◀────────│  localisation_box (WI-2) + rater (WI-1)│
          └──────────────┬──────────────┘          └───────────────┬──────────────────────┘
                         │                                          │
                         ▼                                          ▼
        ┌────────────────────────────┐            ┌───────────────────────────────────────┐
        │ MONITOR (WI-6)             │            │ DE-NOISE (WI-4)                        │
        │  AI-vs-human MAE + trend   │            │  same film, ≥2 raters → consensus.py   │
        │  subgroup + domain drift   │            │  → majority label OR adjudication queue │
        │  CPP plausibility priors ◀─┼── REFERENCE │  → senior read resolves (audited)      │
        │  (external, soft, §5 ref)  │  report     └───────────────┬───────────────────────┘
        └────────────────────────────┘                            │ consensus labels
                         │                                         ▼
        ┌────────────────┴───────────┐            ┌───────────────────────────────────────┐
        │ COVERAGE (WI-5)            │            │ EXPORT (built: export_dataset.py)      │
        │  per-bone×stage readiness  │───────────▶│  patient-level splits, crops, manifest │
        │  support bands to "candidate"│          │  + de-id/consent gate (WI-9)           │
        └────────────────────────────┘            └───────────────┬───────────────────────┘
                                                                  │ frozen dataset (manifest+checksum)
                                                                  ▼
        ┌───────────────────────── OFFLINE, GATED (WI-7) — never live ──────────────────────┐
        │ train (train split) → tune (val) → evaluate candidate on LOCKED test (Plan 5)      │
        │ gate: beat incumbent ∧ no subgroup regression ∧ calibrated ∧ HUMAN SIGN-OFF        │
        │ pass → bump model_version, write model card, deploy · fail → stays a candidate     │
        └───────────────────────────────────────────────┬──────────────────────────────────┘
                                                         │ new model version (audited)
                                                         └────────▶ back into clinical use as SUGGESTIONS
                                                                    gated per-bone by label quality (WI-8)
```

**Invariants (must not weaken):**
- No online/auto weight updates. Model changes only through WI-7.
- A correction never mutates a patient's reported age (enforced by `BoneAgeFeedback` being separate from `TW3Assessment`).
- Patient-level splits only — no child in two splits (already enforced; keep the leak-refusal test).
- Consensus never invents a stage; disagreement → adjudication, never silent averaging.
- External references (CPP study) are **soft plausibility signals**, never release gates (population differs).

---

## 5. Data-model additions

Additive migrations only (bump `DB_SCHEMA_VERSION`; the app records it via `ensure_schema_version`).

- **`BoneAssessment`**: `rater_id: str|None` (who confirmed this bone), so assessment-derived consensus works. *(WI-1)*
- **`TW3Assessment`**: `reader_id: str|None` and `read_round: int` (independent-read number for the same film), enabling multi-reader grouping. *(WI-1)*
- **New `AdjudicationItem`**: `id, radiograph_id, stage_system, bone_code, votes(json), status(open|resolved), resolved_stage, resolved_by, resolved_at, reason`. Populated from `build_film_consensus` adjudication output. *(WI-4)*
- **`Radiograph`**: reuse existing `anonymisation_status`; add `consent_status: str|None` (unknown|consented|research_ok|withheld). Export excludes anything not cleared. *(WI-9)*
- **New `ModelRelease`**: `id, model_kind(screening|localizer|stager), version, dataset_manifest_checksum, metrics(json), incumbent_version, beat_incumbent(bool), signed_off_by, signed_off_at, status(candidate|deployed|rejected), model_card_path`. The audit record of every gated release. *(WI-7)*
- **Optional `SecondaryMaturity`** (WI-10): `radiograph_id, method(smi|cvmi), stage, reader_id` — captured cross-checks, displayed separately, never averaged.

---

## 6. Work items

Each item = one reversible, tested commit; suite stays green.

### WI-1 — Rater identity on assessments  *(foundation)*
- **Why:** consensus/adjudication needs to know *who* read each film; today only the feedback log has `rater_id`.
- **How:** add `BoneAssessment.rater_id`, `TW3Assessment.reader_id` + `read_round`; migration + schema-version bump; populate from the authenticated/entered reader on save; emit `AuditEvent(event_type="stage_confirmed")`.
- **Files:** `backend/models.py`, `backend/db.py` (migration), assessment save path (`backend/assessment_service.py`), tests.
- **Tests:** two independent reads of one film store distinct `reader_id`/`read_round`; consensus can group them.
- **Acceptance:** assessment-derived consensus runs on real reads, not just feedback.

### WI-2 — Localization-confirm UI + persistence  *(critical — the data engine)*
- **Why:** no boxes ⇒ no crops ⇒ no per-bone dataset ⇒ Plan 4 blocked. This is the single highest-leverage item in the plan.
- **How:** on a saved radiograph, call `localize.predict_boxes(image)` when a localizer model exists (honest `None` degradation when it doesn't — doctor draws boxes manually). Render 13 (later 20) draggable boxes over the film; doctor adjusts; `POST` persists each `BoneAssessment.localisation_box` (JSON `[x0,y0,x1,y1]`) + `localisation_confidence`. The existing exporter turns these into crops automatically.
- **Files:** `backend/ai/localize.py` (wire `predict_boxes`), new `POST /api/bone-age/boxes`, `frontend/index.html` (box editor), tests.
- **Tests:** boxes persist + round-trip; `export_dataset` now produces crops (crops > 0) from stored boxes; no localizer model ⇒ manual boxes still persist.
- **Acceptance:** a graded film with confirmed boxes yields crops in the exported dataset; coverage `n_with_image` rises.

### WI-3 — Per-bone capture with AI-suggestion scaffolding  *(high)*
- **Why:** close the correction loop and record *what the AI said vs what the doctor set*, so future AI accuracy is measurable per bone.
- **How:** on stage save, populate `doctor_stage`, `confirmed_stage`, `stage_confidence`, and — when an AI suggestion was shown — `ai_suggested_stage`, `ai_stage_probabilities`, `doctor_modified_ai_result`, `modification_reason`. Emit `AuditEvent`. Fields stay null until Plan 4's stager exists.
- **Files:** `backend/assessment_service.py`, `backend/api_bone_age.py`, tests.
- **Tests:** a modified suggestion sets `doctor_modified_ai_result=True` + reason; export carries `confirmed_stage` only.
- **Acceptance:** per-bone AI-vs-doctor deltas are recoverable from the DB.

### WI-4 — Persisted adjudication queue + reviewer workflow  *(high)*
- **Why:** turn `consensus.py`'s pure output into an actionable senior-review loop; de-noise labels before training (single-rater labels carry 25–40% noise — see `consensus.py`).
- **How:** new `AdjudicationItem`; a job maps `build_film_consensus` adjudication bones → open items; `GET /api/bone-age/adjudication` lists them; `POST …/resolve` records `resolved_stage` + `resolved_by` (audited). Resolved consensus labels take precedence in export.
- **Files:** `backend/models.py`, new `backend/api_adjudication.py`, `frontend/index.html` (review list), tests.
- **Tests:** a 1-1-1 tie creates an open item; resolution closes it + audits; resolved label appears in `consensus.json`.
- **Acceptance:** disputed bones are queued, resolved by a senior reader, and never silently averaged.

### WI-5 — Coverage dashboard (UI)  *(medium)*
- **Why:** make "how close are we to enough data to train bone X?" visible so collection is targeted.
- **How:** render `coverage_report()` as a per-bone×stage heatmap (rows = 20 bones, cols = stages), coloured by support band, with per-bone "N more distinct patients to reach candidate (≥50)". Split by sex.
- **Files:** new `GET` already exists (`coverage_report`); add a frontend panel; test the endpoint shape.
- **Acceptance:** a PM/clinician can see exactly which bone×stage cells are empty/experimental/candidate.

### WI-6 — Monitoring & drift surface (+ CPP plausibility priors)  *(medium)*
- **Why:** "daily learning" honestly means *watch the gap*, not mutate the model. Add drift and external-plausibility context.
- **How:** build a dashboard over `feedback/stats` (AI-vs-human MAE trend, subgroup + domain breakdowns already computed). Add: (a) **input-domain drift** — share of low-trust images over time; (b) **distribution drift** alert when the confirmed bone-age distribution shifts beyond a band; (c) a **plausibility-priors panel** comparing the accumulated CPP-indication distribution + bone-age−chronological-age gap against the external CPP cohort in [the reference report](REFERENCE-cpp-skeletal-maturation-study.md) — clearly labelled *external / population-to-confirm*, **soft signal only**.
- **Files:** `backend/api_bone_age.py` (extend stats), `frontend/index.html` (dashboard), a small `backend/monitoring/priors.py` holding the CPP reference bands with a source-to-confirm note, tests.
- **Acceptance:** the dashboard shows the trend + a plausibility panel that never gates a release and always shows its external caveat.

### WI-7 — Offline retrain → gated release harness  *(critical)*
- **Why:** the safety core. Guarantees a "learned" model is a *release candidate*, not a live mutation.
- **How:** `backend/ai/release.py` orchestrates: (1) freeze dataset via `export_dataset` (record `manifest.checksum`); (2) train on `train`, tune on `val`; (3) evaluate the candidate on the **locked `test`** split using Plan 5's evaluator (thin interim MAE/subgroup evaluator until Plan 5 lands); (4) **gate**: `beat_incumbent ∧ no prespecified subgroup regression ∧ calibration ok`; (5) require **human sign-off**; (6) on pass, write a `ModelRelease` row + model card, bump `model_version`, deploy; on fail, keep it a candidate. **No path auto-promotes.**
- **Files:** `backend/ai/release.py`, `backend/models.py` (`ModelRelease`), CLI, tests (with a synthetic candidate that *fails* the gate and one that passes).
- **Acceptance:** a candidate that does not beat the incumbent cannot deploy; every deploy has a signed `ModelRelease` + model card.

### WI-8 — Label-quality activation gates for AI suggestions  *(high — interlock to Plan 4)*
- **Why:** a bone's AI suggestion may be shown only when the data behind it is trustworthy (encodes `STAGE.md`'s discipline).
- **How:** `suggestions_allowed(bone, sex)` = coverage support ≥ threshold per stage across distinct patients **AND** consensus agreement ≥ threshold **AND** validated confidence calibration. Below threshold ⇒ "manual" (no suggestion). Carpals gated independently (harder).
- **Files:** `backend/ai/stage_classifier.py` (gate hook), `backend/tw3/pipeline/export_dataset.py` (reuse support bands), tests.
- **Acceptance:** a bone below support/agreement shows "manual"; only qualified bones surface a suggestion (once Plan 4 provides one).

### WI-9 — Governance: consent/de-id gate + audit everywhere  *(medium)*
- **Why:** crops are patient imaging; export must exclude anything not cleared, and every flywheel action must be auditable.
- **How:** add `Radiograph.consent_status`; `export_dataset` skips non-cleared films (manifest logs the exclusion count). Emit `AuditEvent` for correction, box-confirm, adjudication-resolve, and model promotion. Surface "corrections never change the patient's result" in the feedback UI.
- **Files:** `backend/models.py`, `export_dataset.py`, action handlers, tests.
- **Acceptance:** a non-consented film never reaches the dataset; all four action types produce audit rows.

### WI-10 — Optional secondary maturity cross-check (SMI ≫ CVMI)  *(optional)*
- **Why:** the CPP reference shows SMI discriminates and correlates moderately; CVMI is weak. If the clinic records these, capture SMI as a separate cross-check.
- **How:** `SecondaryMaturity` capture; display beside TW3 as an independent signal; **never averaged**; CVMI de-prioritized/labelled weak.
- **Files:** `backend/models.py`, small API + UI, test.
- **Acceptance:** SMI stage is recorded and shown separately; no code path merges it into the TW3 age.

---

## 7. Sequencing

```
WI-1 (rater id) ─▶ WI-2 (localization capture) ─▶ WI-3 (per-bone capture)
                         │                              │
                         ▼                              ▼
                   WI-4 (adjudication) ─▶ WI-5 (coverage UI)
                                              │
        WI-6 (monitoring + CPP priors) ───────┤
                                              ▼
                                   WI-8 (activation gates) ─▶ WI-7 (gated release harness)
                                              │
                                   WI-9 (governance) ── land alongside WI-2/WI-4
                                   WI-10 (SMI cross-check) ── optional, any time
```
Recommended order: **WI-1 → WI-2 → WI-3 → WI-9 → WI-4 → WI-5 → WI-6 → WI-8 → WI-7 → WI-10.** WI-2 first among features — it unblocks all downstream data. WI-7 last — it consumes everything and needs Plan 5's evaluator (interim evaluator until then).

---

## 8. Test & verification plan

- **Unit:** each WI ships pytest (extend `tests/bone_age/`). Keep `test_feedback.py` + exporter tests green.
- **Loop integration:** seed 2 raters × same film with one disagreement → adjudication item opens → resolve → export shows resolved consensus label + a crop (once WI-2 boxes exist).
- **Negative controls (stay red-when-broken):** patient appears in two splits ⇒ export refuses (existing); a candidate model that doesn't beat incumbent ⇒ WI-7 refuses deploy; a non-consented film ⇒ excluded from export; a correction ⇒ patient's reported age unchanged.
- **Browser verification:** upload a film, confirm boxes, grade bones as two raters, see the adjudication queue populate and the coverage heatmap increment. Never use real patient films on a shared host (README constraint).

---

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Silent model drift / over-trust | No online learning (WI-7 gate); monitoring surface (WI-6); model card per release. |
| Noisy single-rater labels | Multi-rater consensus + adjudication (WI-4); label-quality gate before suggestions (WI-8). |
| Data leakage across splits | Patient-level split leak-refusal (built) + retained test. |
| Feedback loop bias (model teaches itself its own errors) | Locked test set never drawn from routine feedback (validation_protocol §3); beat-incumbent gate. |
| Privacy / consent | Consent/de-id export gate (WI-9). |
| Over-reading the CPP priors as a target | Panel is soft, labelled external/population-to-confirm, never a release gate (§5 of the reference report). |
| Carpals harder than RUS | Gated independently (WI-8). |

---

## 10. Definition of Done

- [ ] Confirmed stages carry rater identity; assessment-derived consensus runs (WI-1).
- [ ] Doctor-confirmed boxes persist and the exporter produces real crops (WI-2).
- [ ] Per-bone AI-vs-doctor deltas are captured + audited (WI-3).
- [ ] Disputed bones enter a persisted adjudication queue, resolved by a senior reader, never averaged (WI-4).
- [ ] Coverage heatmap shows per-bone×stage readiness toward "candidate" (WI-5).
- [ ] Monitoring dashboard shows AI-vs-human trend + drift + a soft CPP plausibility panel with its external caveat (WI-6).
- [ ] Offline retrain harness deploys **only** a candidate that beats the incumbent, shows no subgroup regression, is calibrated, and is signed off — with a `ModelRelease` record + model card (WI-7).
- [ ] AI suggestions surface only for bones meeting support + consensus + calibration thresholds (WI-8).
- [ ] Non-consented films are excluded from export; all flywheel actions audit (WI-9).
- [ ] Full suite green; loop browser-verified end to end.

---

## 11. Open decisions to confirm

1. **Reader identity source:** is there per-user auth in the app, or is `reader_id` free-text entered per read? (affects WI-1 + audit trust.)
2. **Consensus thresholds:** minimum raters per film (default 2) and agreement threshold to accept a training label vs adjudicate.
3. **Retrain cadence + sign-off authority:** who signs off a `ModelRelease`, and what is the trigger (N new labels? scheduled?).
4. **Beat-incumbent margin + locked-test source:** how much better must a candidate be, and where does the locked test set come from (this couples to **Plan 5**).
5. **SMI/CVMI capture (WI-10):** does the clinic actually record these? If not, defer.
6. **Consent model:** what consent states exist for using de-identified crops in offline training?

---

*This plan builds the governed data + release machinery. It does not itself train the auto-staging models (Plan 4) or define the formal metric gates (Plan 5); it produces the data they need and the release gate they must pass.*

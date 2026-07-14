# Plan 0 — Master Integration & Delivery Sequence

**Status:** Awaiting go-ahead to implement · **Created:** 2026-07-14 · **Owner:** (assign)
**Branch:** continue on `fix/clinical-accuracy-remediation` (see §7 git strategy)
**Scope chosen by product owner (2026-07-14):**
- Finish line = **full clinical-product lifecycle**, including model training and external validation.
- Licensed TW3 data = **both** licensed book scans **and** clinic reference films will be supplied.
- Training = **GPU + datasets ready now** (RSNA images, BoNet/BAAR keypoints).

> **What this document is.** The single sequencing spine that ties Plans 1–5 into one end-to-end
> delivery, *tailored to the code that already exists in this repo*. It does not restate the five
> plans — it says, in order, what to do, why now, what asset it needs from you, and how we prove it
> works before moving on. Read §1 (verified current state) before anything: **most of Plans 1–5 is
> already built and tested but uncommitted**, so the primary risk is rebuilding what exists or
> leaving built modules unwired — the two things you explicitly said to avoid.

---

## 0. Governing principles (carried from `IMPLEMENTATION-PLAN.md`, made concrete here)

1. **Reuse, never rebuild.** Plans 1–5 are ~80% implemented on this branch (127 bone-age tests
   green). Every phase below starts by *verifying what exists* and only then closing the gap. No
   duplicate engine, no parallel pipeline.
2. **No dead code.** A module is "done" only when something in the *running* FastAPI app or a real
   CLI/offline job calls it, a test covers that path, and (if it has a surface) the frontend shows
   it. The orphan list in §1 is the definition of "not done yet."
3. **No fake or guessed clinical data.** Data-gated features ship loader + gate + schema + test now;
   real values are entered lawfully later and must pass the mechanical checks (§3). Six AI-generated
   TW3 tables already failed — reconstructed values are never accepted as authoritative.
4. **Gate, don't caveat.** Unvalidated/uncertain output abstains; it does not footnote a live number.
5. **One reversible commit per item**, each with its own test, each leaving the suite green;
   end-to-end (code → test → browser-verify where there's a surface → commit).
6. **Separation invariants that no phase may weaken:** RUS age and carpal age stay separate (never
   averaged); the whole-image screening number is a cross-check, never TW3; chronological age never
   influences staging; a correction is evidence, never a patient result; models change only through
   the release gate.

---

## 1. Verified current state (measured 2026-07-14, not assumed)

Full bone-age suite: **127 passed** once runtime deps are installed
(`fastapi sqlalchemy onnxruntime httpx python-multipart uvicorn`).

### Built AND wired into the running pipeline
| Plan | What works today | Key files |
|---|---|---|
| 1 | Letters engine (13 RUS + 7 carpal + TWII′20, separate scores/ages); 4 gates (calibrated ∧ reference-cases ∧ provenance ∧ checksum); checksum tamper-lock; dual-transcription tool; dynamic `/config` activation; licensed-tables editor UI; SOP; E2E synthetic-fixture activation test | `backend/tw3/letters_scoring.py`, `verify_transcription.py`, `letters_tables.json`, `report.py`, `api_bone_age.py`, `api_assessments.py` (`/letters-config`, `/letters-tables`), `frontend/index.html`, `LICENSED_TABLES_SOP.md` |
| 2 | `rater_id`/consent/`AdjudicationItem`/`ModelRelease` models; adjudication backend endpoints; **box-editor UI wired** (`/localize`, `/bones/{bone}/box`); coverage endpoint + panel; consensus; consent-gated dataset export | `backend/models.py`, `assessment_service.py`, `tw3/adjudication.py`, `tw3/consensus.py`, `tw3/pipeline/export_dataset.py`, `api_assessments.py` (`/coverage`) |
| 3 | Subgroup (Mondrian) conformal; conformal calibration; conformal interval in `/estimate`; image-quality abstention gate | `backend/ai/conformal.py`, `calibrate_conformal.py`, `boneage.py`, `imaging.py` |
| 5 | Age + staging evaluators; cross-artifact leak guard; encoded versioned gates; release-gate engine; validation-report generator; PROTOCOL.md; locked-test registry | `backend/ai/evaluate.py`, `ai/validation/{leak_guard,gates,release_gate,report}.py`, `gates.json`, `locked_test.json`, `PROTOCOL.md` |

### Built but NOT yet wired — the integration debt to clear (Phase A)
| Orphan | Purpose | Gap to close |
|---|---|---|
| `backend/ai/suggestion_gate.py` (`suggestions_allowed`, `activation_map`) | decide when a bone's AI suggestion may show | no caller; wire into the assessment/report path (yields "manual" until Plan 4 ships a model) |
| `backend/ai/release.py` (`decide_release`, `record_release`) | offline retrain → gated release | no CLI/endpoint; add an offline `python -m backend.ai.release` entrypoint + admin surface |
| `backend/monitoring/priors.py` (`expected_bands`, `plausibility_check`) | CPP plausibility priors | no endpoint, no dashboard; expose + render (soft/external-labelled) |
| adjudication queue | senior-review de-noising | backend wired, **no frontend UI** |
| `feedback/stats` | AI-vs-human drift monitoring | endpoint exists; frontend never calls it — no dashboard |
| `predict_stage` (`stage_classifier.py`) | per-bone AI staging | not wired (also needs a trained model — Phase E) |

### Blocked only on assets you will supply
- **Plan 1 activation:** real licensed TW3 point tables + score→age curves (scans) + 2–3 clinic reference films → Phase B.
- **Plan 3/4 training:** GPU + RSNA images + BoNet/BAAR keypoints → Phases D/E.
- **Plan 5 external run:** an Indian clinical validation cohort with ≥2 blinded readers → Phase F.

---

## 2. Cross-plan dependency graph (drives the phase order)

```
Plan 5 (evaluator + gates + release engine)  ─── is the gate Plans 2/3/4 all call
        │
        ├─► Plan 2 WI-7 release harness ──┐
        │                                 ├─► Plan 3 candidate promotion (screening retrain)
        │                                 └─► Plan 4 model promotion (localizer + stagers)
        │
Plan 2 flywheel (capture → consensus → export) ─── manufactures the per-bone data Plan 4 stager needs
        │
Plan 4 localizer (public data) ── startable independently ──► better boxes ──► faster Plan 2 capture
        │
Plan 1 (licensed tables) ── independent; activation gated on your scans+films ──► real RUS/carpal ages
        │                                                                            │
        └────────────────────────────────────── Plan 4 confirmed stages feed Plan 1 engine ◄─┘

Plan 5 WI-8 external validation ── the final gate; flips "internal pass" → "clinical claim allowed"
```

**Consequence for ordering:** finish the validation/gate spine and clear integration debt first
(Phase A + C), because every training/activation phase downstream *reports through it*. Plan 1
activation (Phase B) can run in parallel the moment your scans arrive. Training (D/E) needs the gate
live. External validation (F) is last and cohort-gated.

---

## 3. Anti-fabrication checks for licensed TW3 data (applied mechanically in Phase B)

Any candidate table — even transcribed from your real book — is rejected on any failure:

- **Sum-to-1000:** RUS max points (stage I; ulna stage H) sum to **exactly 1000** for boys and for
  girls. Carpal max sums to 1000 too. *(Necessary, not sufficient — see below.)*
- **Monotonicity:** within each bone, points are non-decreasing A→I. A more-mature stage can never
  score lower.
- **Reference-case reconciliation:** each clinic reference film's listed per-bone points sum to the
  stated total, and that total maps to the stated age on the score→age curve within tolerance
  (default ±0.3 yr).
- **Drift tell:** a real book has ONE value per cell. If re-transcription changes a cell, the source
  is being generated, not read — reject and re-check against the scan.

Sum-to-1000 passing proves nothing about individual cells (an AI once shaved DP5 to force the total,
creating an impossible girls-DP5 where I < H). The **dual-transcription diff + reference-film
reproduction** are what actually validate — that is why Phase B uses both.

---

## 4. The delivery sequence

Each phase lists: **goal · what it needs from you · work · proof of done.** Within a phase, every
item is its own tested commit.

### Phase A — Seal the foundation: commit what exists, wire every orphan *(in-repo, now; no assets)*
**Goal:** the branch's built work is committed, and no module is dead — everything is called by the
running app or a real offline job, with a test on that path.
**Needs from you:** nothing (a couple of small config confirmations, §6).

- **A0 — Baseline & checkpoint.** Pin the runtime dev deps (`fastapi/sqlalchemy/onnxruntime/httpx`)
  into `requirements-dev.txt` so the suite is reproducible; commit the existing tested Plan 1–5
  backend as focused, message-per-plan commits. Record the 127-green baseline.
- **A1 — Wire the release harness (Plan 2 WI-7).** Add `python -m backend.ai.release` offline CLI
  (freeze dataset via `export_dataset` → run `decide_release` → `record_release`) and a read-only
  admin endpoint listing `ModelRelease` rows. *Proof:* CLI run on a synthetic candidate produces a
  `candidate`/`rejected`/`deployed` row + model card; test asserts no auto-promotion.
- **A2 — Wire monitoring + CPP priors (Plan 2 WI-6).** Add `GET /api/bone-age/monitoring` returning
  `feedback/stats` trend + drift + `priors.plausibility_check` (labelled external/soft, never a
  gate); render a monitoring/drift dashboard panel in `index.html`. *Proof:* dashboard shows the
  AI-vs-human trend and a CPP plausibility panel with its external caveat; endpoint test.
- **A3 — Build the adjudication review UI (Plan 2 WI-4 frontend).** List open items from
  `/adjudication`, resolve via `/adjudication/{id}/resolve`; resolved label flows to export. *Proof:*
  a seeded 1-1-1 tie appears, resolves, closes, and shows in `consensus.json`; browser-verified.
- **A4 — Wire the suggestion gate (Plan 2 WI-8 / Plan 4 WI-5 hook).** Call
  `suggestion_gate.activation_map` in the assessment/report path so each bone is "suggestion-eligible"
  or "manual"; today every bone is "manual" (no stager yet) — that is the correct, tested behaviour,
  and Phase E flips bones on as models qualify. *Proof:* report marks bones manual with the gate
  reason; test pins "below-support ⇒ manual."
- **A5 — Confirm single release path.** Assert (test) that Plan 3/4 promotion can only go through
  `ai/validation/release_gate.evaluate_candidate` — no side path overwrites a shipped model.

**Phase A definition of done:** every module in §1's orphan table is called by a real path with a
test; monitoring + adjudication surfaces render; suite green; app browser-verified.

### Phase B — Activate Plan 1 with the real licensed tables *(asset-gated: your scans + films)*
**Goal:** TW3 scoring switches from annotation-only to real, clinician-confirmed RUS + carpal ages.
**Needs from you (before B starts):** the §6 Plan-1 confirmations, the licensed book **scans**, and
2–3 clinic **reference films** (sex, 13 RUS stages, reported bone age).

- **B0 — Confirm licence facts** (edition/ISBN/pages/owner) into the provenance block; decide
  RUS-only vs RUS+carpal, TWII′20 in/out, preferred curve, tolerance (§6).
- **B1 — Dual transcription.** Two independent transcribers enter the scanned tables into separate
  files; `verify_transcription.py A.json B.json` until the cell diff is empty (§3 drift rule).
- **B2 — Mechanical checks + reference films.** Run sum-to-1000, monotonicity, and reference-case
  reconciliation (§3). Enter the reference films as the reproduction ground truth.
- **B3 — Lock + activate.** `save_letter_tables` (structural validation) → compute + store checksum →
  fill `entered_by`/`verified_by`/`date`. `letters_status()` must return all four gates green.
- **B4 — Verify live.** `/config` flips scoring on; `/report` returns real separate RUS + carpal
  ages across 20 bones; export is stamped (method/edition/version/checksum/curve/uncertainty). Break
  one cell → checksum fails → scoring reverts (negative control).

**Phase B definition of done:** with your real tables + films entered, the four gates pass, live
ages appear and are separate, tampering reverts to disabled. **Honesty label stays "clinician-
supervised decision support; not yet externally validated for Indian children" until Phase F.**

### Phase C — Finalize the validation spine + first internal report *(in-repo, now)*
**Goal:** the release gate is *real* for Phases D/E — a locked internal test that never leaked, and a
first ValidationReport on the shipped 8.6 mo screening model.
**Needs from you:** confirm the locked-test source (recommend: carve an internal RSNA holdout now,
distinct from the conformal val split) and the beat-incumbent margin (§6).

- **C1 — Carve the locked internal test** into `locked_test.json`; wire `leak_guard.assert_disjoint`
  across train/val/feedback/calibration. *Proof:* planted overlap refuses; clean split passes.
- **C2 — Baseline validation report.** Run the evaluator + gates on the shipped ONNX → first
  `ValidationReport` (JSON + human HTML) with subgroup tables + provenance. *Proof:* report artifact
  exists and is reproducible; gate result recorded.

**Phase C definition of done:** a leaked test refuses; a real baseline validation report exists; the
release gate is callable end-to-end for the next phases.

### Phase D — Screening-model upgrade *(GPU; you run the training, I wire + gate)*
**Goal:** beat the 8.6 mo baseline honestly, with sharper subgroup-aware uncertainty, shipped only
through the gate. Inference stays CPU/ONNX.
**Needs from you:** GPU run execution (I supply exact runnable recipes); §6 latency budget + target
MAE.

- **D1 — Hand-crop preprocessing** shared by trainer and `boneage.preprocess` (identical in both) →
  Colab retrain → candidate ONNX + updated metadata/model card. *Proof:* crop deterministic in both
  paths; retrain beats 8.6 on the locked split or it is not a candidate.
- **D2 — Recalibrate subgroup conformal** on the candidate; per-bucket empirical coverage holds.
- **D3 — Benchmark + gate.** `benchmark.py` CPU p50/p95 within budget → run candidate through the
  Plan 5 release gate (beat incumbent ∧ no subgroup regression ∧ calibrated ∧ latency ∧ sign-off) →
  deploy via gate only; shipped ONNX never overwritten otherwise.
- **D4 — India recalibration layer** scaffolded inert (per-(sex×age-band) monotone map; never a
  universal offset); activates only when Indian labelled data + subgroup validation exist. *Proof:*
  inert + disclosed with no Indian data; synthetic bucketed map applies when enabled.

**Phase D definition of done:** a cropped/retuned candidate that beats 8.6 with held coverage and
within latency ships through the gate; otherwise the shipped model is untouched; India layer inert +
disclosed.

### Phase E — Auto per-bone pipeline (the capstone) *(GPU + Plan 2 data)*
**Goal:** AI auto-locates each bone and suggests its stage + confidence; the doctor confirms every
bone; Plan 1's engine turns confirmed stages into separate RUS + carpal ages. Never auto-final.
**Needs from you:** GPU runs; the BoNet keypoint release version (drives `LANDMARK_TO_BONE`);
sustained Plan 2 capture so per-bone coverage accrues.

- **E1 — Localizer (public data, startable immediately).** Set `LANDMARK_TO_BONE` in
  `baar_to_jsonl.py`; train on RSNA + BoNet keypoints → `localizer.onnx`; `predict_boxes` seeds the
  existing box editor; localizer eval gate (peak-error px, per-bone, by subgroup). *Proof:* auto-
  boxes appear and are doctor-adjustable; below-gate → low-confidence hints.
- **E2 — Per-bone stagers (data-gated on Plan 2).** As coverage reaches ~50/stage across distinct
  patients, `train_stager` one ordinal model per qualifying bone → calibrate probabilities → wire
  `predict_stage` as gated suggestions (via A4's `suggestion_gate`) → doctor confirms each → Plan 1
  engine. *Proof:* only gated bones show a calibrated suggestion; every stage requires explicit
  confirmation; overrides captured with reason.
- **E3 — Carpal extension (13 → 20).** 7 carpal keypoints + 7 carpal stagers, gated independently,
  only after RUS gates pass. Carpal age stays separate.

**Phase E definition of done:** a film flows auto-boxes → doctor-confirmed crops → gated stage
suggestions → doctor-confirmed 20-bone report with separate RUS/carpal ages + the screening cross-
check; no model auto-promotes; suite green; browser-verified.

### Phase F — External clinical validation *(cohort-gated; the honesty gate)*
**Goal:** turn "internal gate pass" into a defensible clinical claim for Indian children.
**Needs from you:** the pre-registered cohort (normal + the pathology groups in PROTOCOL.md), ≥2
blinded readers + adjudication, consent.

- **F1 — Execute PROTOCOL.md** on the cohort → generate the external `ValidationReport` → the
  external-cohort gate flips from red to green. Only then may any accuracy claim / positioning change
  beyond "clinician-supervised decision support."

**Phase F definition of done:** a pre-registered external validation report exists; claims are
bounded by its subgroup results; nothing is marketed beyond what it shows.

---

## 5. Verification discipline (every phase)

- **Unit/logic:** each item ships a pytest; keep `tests/bone_age/*` green (127 and rising).
- **Negative controls stay red-when-broken:** checksum tamper disables scoring; missing provenance
  disables scoring; a leaked test refuses evaluation; a candidate not beating incumbent or regressing
  a subgroup cannot deploy; a non-consented film never exports; a correction never changes a patient
  age; a stage suggestion never becomes confirmed without a doctor action.
- **Browser verification** (via the preview tools) for every surface change: Plan 1 activation,
  monitoring dashboard, adjudication UI, box editor, gated suggestions. **Never use real patient
  films on a shared host** (README constraint) — synthetic fixtures only.

---

## 6. Decisions I will confirm with you *before* the relevant phase (not blocking Phase A)

**Before Phase B (licensed tables):**
1. Which licensed **edition** (TW3 2001 RUS vs TW2) — fixes the primary curve (`twiii` vs `twii`).
2. **RUS-only or RUS + carpal** (is the carpal table licensed)?
3. **TWII′20** in or out (only if the licence covers it)?
4. Which **reference films** (3+ historically-reported, spanning the working age range) and what
   **tolerance** (default ±0.3 yr)?
5. **Preferred definitive curve** if both TWII and TWIII are entered (default TWIII).

**Before Phase C/D (screening + gate):**
6. **Locked internal test source** (recommend carving an RSNA holdout now).
7. **Beat-incumbent margin** (e.g. ≥0.3 mo MAE and no subgroup regression).
8. **CPU latency budget** (e.g. p95 ≤ 300 ms) and **target MAE** (stop at ≤6 mo product gate vs push
   toward the RSNA ~4.2 mo frontier).

**Before Phase E (per-bone AI):**
9. **BoNet keypoint release** version on hand (drives the landmark→bone mapping).
10. **Coverage threshold** to start training a bone (default ~50/stage across distinct patients) and
    the **staging gate** (overall κ ≥ 0.80, per-bone ≥ 0.70).
11. **Suggestion default:** off until each bone passes its gate (recommended) vs shown-as-hint with
    an "unvalidated" flag.

**Before Phase F (external validation):**
12. Cohort site(s), reader panel + adjudication, consent model, and which pathology subgroups are
    realistically obtainable.

---

## 7. Git strategy (recommendation)

Continue on `fix/clinical-accuracy-remediation`. First land Phase A0 as focused per-plan checkpoint
commits of the already-tested backend (it is green now and losing it would be worse than a large
commit), then proceed one-item-one-commit. Per-plan feature branches (as the individual plans
suggest) are optional; given the work already sits together and is cross-dependent, a single ordered
branch with clean commits is simpler to review. No push/PR unless you ask.

---

## 8. Honest ceiling (unchanged, restated so no phase overclaims)

- Real licensed tables + a few reproducing reference films make the engine **lawful and correct**;
  they do **not** by themselves establish external accuracy for Indian children — that is Phase F.
- Original TW3 is British-derived; Indian validation is required regardless of how clean the tables
  are.
- An internal gate pass is not a clinical claim. Every model ships as **assistive decision support
  with a human in the loop** until Phase F says otherwise.
```

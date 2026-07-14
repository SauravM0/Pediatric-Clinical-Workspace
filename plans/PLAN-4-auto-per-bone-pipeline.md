# Plan 4 — Automatic Per-Bone Pipeline (Localizer + Ordinal Stager)

**Status:** Localizer implementable now; stager data-gated on Plan 2 · **Owner:** (assign) · **Created:** 2026-07-13
**Branch target:** dedicated `feat/auto-per-bone`
**This is the capstone.** It delivers the user's core goal — *"analyze all 20 bones and give the right stage for each"* — in its clinically valid form: the AI **auto-locates each bone and suggests its maturity stage + confidence**, the doctor **confirms every bone**, and Plan 1's licensed engine turns the confirmed stages into a **RUS bone age and a separate carpal bone age**. It is never a per-bone "age," and never auto-final.
**Dependencies:** [PLAN-2](PLAN-2-self-learning-flywheel.md) (captures the training data + AI-suggestion fields + activation gate), [PLAN-5](PLAN-5-validation-and-release-gates.md) (staging evaluator + release gate), [PLAN-1](PLAN-1-licensed-tw3-tables.md) (licensed tables that turn confirmed stages into ages). Plan 3 (screening) runs in parallel as a separate cross-check.

> **How to use this document.** Self-contained implementation source. Read §3 first: both inference modules (`localize.py` PEA, `stage_classifier.py` PEARLS-RL) are **already written and tested** and degrade honestly to `None` when no model file exists; the data-model fields are already there. What's missing is **trained models** and **wiring**. Crucially, the **localizer trains on public data and can start immediately**; the **stager waits on Plan 2's accumulated per-bone labels** — that split drives the whole sequencing.

---

## 1. Purpose (why this plan)

Today the whole-image screening model gives one number (Plan 3), and the doctor stages all 20 bones by hand. The master audit's central capability gap (`BA-02`) is that there is **no validated automatic 20-bone assessment**. Plan 4 closes it — correctly. It builds the two AI stages the PEARLS architecture defines:

- **PEA (localizer):** find each bone's location from the hand X-ray → a ROI per bone, so the doctor confirms/nudges boxes instead of hunting.
- **RL ordinal stager:** read each bone's crop → suggest its maturity stage (A–I) with a probability distribution, respecting stage order (A < B < … < I).

The output is exactly the per-bone form you locked earlier: **stage + confidence + clinician confirmation**, feeding the method's *group* RUS/carpal scores — not 20 independent ages (which would be clinically invalid, `audit §3.3`). This is what makes "the AI checks all 20 bones" a true, defensible statement instead of an overclaim.

The value: it removes the slowest part of the manual workflow (staging 20 bones), it makes the assessment auditable (every ROI shows what was assessed), and — with the doctor confirming each bone — it stays firmly clinician-assist, not autonomous.

---

## 2. Scope

### In scope
- **Localizer (PEA):** train on public RSNA + BoNet keypoints, ship `localizer.onnx`, evaluate, and wire `predict_boxes` to **seed** the box editor.
- **Stager (PEARLS RL):** train per-bone ordinal classifiers on the **consensus-labelled crops Plan 2 produces**, gated by coverage + calibration; ship `stager/<bone>.onnx`.
- **Suggestion wiring:** fill `ai_suggested_stage` / `ai_stage_probabilities` / `stage_confidence` as **suggestions the doctor confirms** — never auto-final; gated by Plan 2's label-quality interlock (WI-8) so a suggestion appears only where the data supports it.
- **Confidence calibration** of stager probabilities (softmax ≠ calibrated, per `STAGE.md`).
- **End-to-end auto-TW3-as-suggestion** chain into Plan 1's licensed engine.
- **Carpal extension** (13 → 20) after the RUS localizer + stagers pass their gates.

### Out of scope (owned elsewhere)
- **Box-editor UI, per-bone grade capture, coverage dashboard, dataset export, consensus** = **Plan 2**. Plan 4 *provides the auto-boxes and stage suggestions* those surfaces display, and *consumes* the crops they produce.
- **Staging metric evaluator + release-gate engine** = **Plan 5** (WI-4/WI-6). Plan 4 *calls* them.
- **Licensed tables / score→age** = **Plan 1**.
- **Whole-image screening model** = **Plan 3** (separate cross-check).

---

## 3. Current state — gap analysis

**Exists and is reusable — do not rebuild:**

| Capability | Where | State |
|---|---|---|
| PEA localizer inference (heatmap→peak→ROI, per-bone box + confidence, honest `None`) | `backend/ai/localize.py` (`predict_boxes`, `decode`) | ✅ code done, **no model** |
| Ordinal stager inference (crop→top/second/probs/confidence, honest `None`) | `backend/ai/stage_classifier.py` (`predict_stage`, `available_bones`) | ✅ code done, **no models** |
| Localizer trainer + keypoint converter | `train_localizer.py`, `baar_to_jsonl.py` (self-test, `--inspect/--preview`) | ✅ |
| Ordinal stager trainer (one model/bone, skips <2 stages / <8 crops, prints val-acc + within-1) | `train_stager.py` | ✅ |
| Data-model fields for suggestions + boxes | `BoneAssessment.ai_suggested_stage`, `ai_stage_probabilities`, `stage_confidence`, `localisation_box`, `localisation_confidence` | ✅ present |
| Multi-rater consensus labels for training | `consensus.py`, exporter `consensus.json` | ✅ |

**Missing — what Plan 4 builds:**

1. **No trained localizer model.** `predict_boxes` returns `None`. Needs the BoNet keypoint mapping set + verified, then a Colab training run. **Not clinic-data-gated** (public RSNA + public keypoints). → **WI-1**
2. **`predict_boxes` is not wired** to seed the (Plan 2) box editor. → **WI-2**
3. **No localizer evaluation/gate.** → **WI-3**
4. **No trained stagers**, and they **cannot** be trained until Plan 2 has accumulated enough consensus-labelled crops (`STAGE.md`: ~50+ examples per bone×stage across distinct patients). → **WI-4**
5. **`predict_stage` is not wired** into the assessment as gated suggestions. → **WI-5**
6. **No stager calibration or evaluation/gate.** Softmax is not calibrated confidence. → **WI-6**
7. **No assembled end-to-end auto-TW3-as-suggestion path.** → **WI-7**
8. **Carpals (7) not localized or staged.** → **WI-8**

---

## 4. Target architecture

```
   FILM (accepted by the image gate, Plan 3/existing)
     │
     ▼  predict_boxes (PEA, WI-1/WI-2)                     ── auto-boxes are SUGGESTIONS ──
   13→20 ROI boxes + per-bone confidence ───────────▶ Plan 2 box editor: doctor nudges/confirms
     │                                                          │ confirmed boxes persisted (Plan 2 WI-2)
     ▼ crop each confirmed ROI                                  ▼
   per-bone crop ──▶ predict_stage (PEARLS RL, WI-4/WI-5) ──▶ ai_suggested_stage + probabilities
     │                    │ gated by Plan 2 WI-8 (support ∧ consensus ∧ calibration)
     │                    ▼ below gate → "manual" (no suggestion)
     ▼            doctor CONFIRMS every bone (never auto-final)  ── the clinical control point ──
   confirmed_stage per bone (+ modification reason if changed)
     │
     ▼  Plan 1 licensed engine (compute_letters)
   RUS score → RUS bone age   ·   carpal score → carpal bone age   (SEPARATE, never averaged)
     │
     ▼  structured 20-bone report (Plan 1 report.py) — every bone: ROI + stage + confidence + confirmed
        + screening cross-check (Plan 3) shown separately; material disagreement → re-review
     │
     ▼  evaluation + release (Plan 5 WI-4/WI-6 · Plan 2 WI-7): localizer + each stager must pass
        before its suggestion is enabled; models ship only through the gate, never auto-promoted
```

**Invariants:**
- **Doctor confirms every bone.** No stage is ever final from the AI alone. `ai_suggested_stage` ≠ `confirmed_stage`.
- A suggestion is **shown only where the data supports it** (Plan 2 WI-8 gate); otherwise the bone is "manual."
- Localizer boxes are **starting points the doctor adjusts**, not ground truth.
- Stager **confidence must be calibrated** before it's shown as a number (WI-6).
- RUS and carpal ages stay **separate**; the AI never produces a per-bone age.
- Carpals are gated **independently** and only after RUS is validated.
- Models change only through the Plan 5/Plan 2 release gate.

---

## 5. Work items

Each item = one reversible, tested commit; suite stays green. Training runs are offline (Colab) and produce candidates; Plan 5/Plan 2 gates promote them.

### WI-1 — Train + ship the localizer on public data  *(startable now — not clinic-data-gated)*
- **Why:** the one AI piece that needs **no** private labels — public RSNA images + public BoNet/BAAR keypoints. It unblocks auto-boxes and, later, cleaner crops for the stager.
- **How:** per `LOCALIZE.md`: download RSNA + BoNet keypoints; `baar_to_jsonl.py --inspect` to read the landmark indexing, set `LANDMARK_TO_BONE`, `--preview` to eyeball, `--out keypoints.jsonl`; `train_localizer --img-size 512 --epochs 60` on Colab; copy `localizer.onnx` + `localizer.json` back. Verify decode matches training.
- **Files:** `backend/ai/baar_to_jsonl.py` (set mapping), `backend/ai/models/localizer.{onnx,json}` (produced), tests (mapping self-test already exists).
- **Acceptance:** `predict_boxes` returns 13 plausible boxes on a held-out RSNA film with a reported peak-error (px) meeting the WI-3 target.

### WI-2 — Wire `predict_boxes` to seed the box editor  *(depends on Plan 2 WI-2)*
- **Why:** turn auto-localization into the doctor's starting overlay.
- **How:** on a saved radiograph, call `predict_boxes`; pass boxes + per-bone confidence to the Plan 2 box editor as the initial overlay; the doctor nudges/confirms; confirmed boxes persist to `BoneAssessment.localisation_box` + `localisation_confidence`. Honest degradation: no localizer → doctor draws boxes (Plan 2 already supports manual).
- **Files:** `backend/api_bone_age.py` (boxes endpoint calls `predict_boxes`), `frontend/index.html` (seed overlay), tests.
- **Acceptance:** uploading a film shows auto-boxes the doctor can adjust; confirmed boxes feed the exporter's crops.

### WI-3 — Localizer evaluation + gate  *(via Plan 5)*
- **Why:** enable auto-boxes only when localization is good enough; boxes remain doctor-confirmed regardless.
- **How:** evaluate detection completeness, per-bone landmark/ROI error, and peak-error (px), stratified by sex/age-band/domain (Plan 5 subgroup engine). Gate before auto-boxes are enabled by default (below gate → boxes are shown as low-confidence hints).
- **Files:** evaluation harness calling Plan 5 WI-3; a localizer-metrics test.
- **Acceptance:** a localizer below the error target does not become the default overlay; metrics are reported.

### WI-4 — Train the per-bone ordinal stagers  *(data-gated on Plan 2)*
- **Why:** the actual "read each bone's stage" AI — and the hardest, because it needs per-bone stage labels that no public dataset has.
- **How:** consume Plan 2's exported **consensus-labelled crops**; `train_stager --dataset dataset` (one ordinal cumulative-link model per bone; respects A<…<I; skips bones with <2 stages or <8 crops). Train a bone **only** when Plan 2's coverage shows ~50+ examples per stage across **distinct patients** (`STAGE.md`). Ship `stager/<bone>.onnx` + metrics per bone.
- **Files:** `backend/ai/train_stager.py` (exists), produced `stager/*.onnx`, tests.
- **Acceptance:** a bone that meets coverage trains and reports val-acc + within-1; bones below coverage are skipped (no undertrained model ships).

### WI-5 — Wire `predict_stage` as gated suggestions  *(depends on Plan 2 WI-3/WI-8)*
- **Why:** surface stage suggestions the doctor confirms — only where trustworthy.
- **How:** for each confirmed crop, call `predict_stage`; write `ai_suggested_stage`, `ai_stage_probabilities`, `stage_confidence`; show top + second + distribution as a **suggestion**. Gate visibility with Plan 2 WI-8 (`suggestions_allowed(bone, sex)` = support ∧ consensus ∧ calibration); below gate → "manual," no suggestion. A doctor override sets `doctor_modified_ai_result` + reason (Plan 2 WI-3). **Never auto-final.**
- **Files:** `backend/api_bone_age.py`, `backend/assessment_service.py`, `frontend/index.html`, tests.
- **Acceptance:** suggestions appear only for gated bones; every stage still requires explicit confirmation; overrides are captured.

### WI-6 — Stager calibration + evaluation + gate  *(via Plan 5)*
- **Why:** softmax/ordinal probability is not calibrated confidence (`STAGE.md`); an over-confident wrong suggestion is dangerous.
- **How:** fit + validate a probability calibration (temperature/Platt) on a held-out set; evaluate per-bone exact-stage accuracy, within-1, quadratic-weighted kappa, confusion matrix, ordinal distance, model-reader agreement, and calibration (Plan 5 WI-4). A bone's suggestion turns on only when its metrics clear the gate (`κ ≥ 0.80`, no bone `< 0.70` without mandatory review, per `validation_protocol.md §6`); carpals gated separately.
- **Files:** calibration util, evaluation calling Plan 5 WI-4/WI-6, tests.
- **Acceptance:** shown confidence is calibrated; only bones passing the staging gate surface suggestions.

### WI-7 — End-to-end auto-TW3-as-suggestion assembly  *(depends on Plan 1)*
- **Why:** connect the chain into a real, reviewable workflow.
- **How:** film → `predict_boxes` → doctor-confirmed crops → `predict_stage` (gated) → doctor confirms all 20 → Plan 1 `compute_letters` → RUS + carpal ages in the structured report; the Plan 3 screening number is shown as a **separate** cross-check, and material disagreement (AI vs doctor, or per-bone consensus dispute) routes to re-review. Every bone doctor-confirmed; nothing auto-final.
- **Files:** orchestration in `backend/api_bone_age.py` / `assessment_service.py`, `frontend/index.html`, integration tests.
- **Acceptance:** a full film flows from auto-boxes to a clinician-confirmed 20-bone report with separate RUS/carpal ages and a cross-check panel.

### WI-8 — Carpal extension (13 → 20)  *(after RUS gates pass)*
- **Why:** complete the 20-bone coverage; carpals are harder and later.
- **How:** add 7 carpal keypoints to the localizer and 7 carpal ordinal stagers, trained + gated **independently** of RUS, only after the RUS localizer and stagers pass their gates and carpal coverage is met.
- **Files:** `baar_to_jsonl.py` (carpal points), `train_localizer.py`/`train_stager.py` (20 bones), tests.
- **Acceptance:** carpal suggestions appear only after carpal-specific gates pass; carpal age stays separate from RUS.

---

## 6. Sequencing

```
WI-1 (localizer, PUBLIC data — start now) ─▶ WI-2 (seed box editor) ─▶ WI-3 (localizer gate)
                                                    │
                    ┌───────────── Plan 2 accumulates consensus crops ─────────────┐
                    ▼ (coverage ≥ threshold)                                        │
            WI-4 (train stagers) ─▶ WI-5 (gated suggestions) ─▶ WI-6 (calibration + gate)
                                                    │
                                                    ▼
                                       WI-7 (end-to-end auto-TW3) ─▶ WI-8 (carpals 13→20)
```
Recommended order: **WI-1 → WI-2 → WI-3**, then — as Plan 2's data accrues — **WI-4 → WI-5 → WI-6 → WI-7 → WI-8.** Start WI-1 immediately: it is the only AI piece not blocked on clinic data, and a working localizer makes Plan 2's capture faster (better auto-boxes), accelerating the very data the stager needs.

---

## 7. Test & verification plan

- **Unit:** keypoint-mapping self-test (`baar_to_jsonl --selftest`), decode/box math, stager preprocessing, gate wiring. Keep existing suite green.
- **Offline training (Colab):** localizer peak-error (px) on held-out RSNA; per-bone stager val-acc + within-1; a bone below coverage is skipped.
- **Negative controls (stay red-when-broken):** no localizer → manual boxes still work; a stage suggestion never becomes `confirmed_stage` without an explicit doctor action; a bone below the Plan 2 support/consensus/calibration gate shows "manual," not a number; an uncalibrated stager cannot surface confidence.
- **Browser verification:** upload a film → auto-boxes appear and are adjustable → for gated bones, stage suggestions appear with a distribution → doctor confirms/overrides → report shows separate RUS/carpal ages + the screening cross-check. Never use real patient films on a shared host.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| No per-bone data → stager can't train | Localizer proceeds on public data (WI-1); Plan 2 flywheel manufactures stager data; stager gated on coverage. |
| Automation bias (doctor rubber-stamps AI) | Doctor confirms every bone; suggestions gated; overrides captured with reason (Plan 2 WI-3). |
| Miscalibrated confidence → over-trust | Calibration + calibration gate before suggestions on (WI-6). |
| Domain shift RSNA→clinic localizer | Localizer evaluated by domain; boxes are doctor-adjustable; retrain via gate as clinic data accrues. |
| Carpals harder than RUS | Independent carpal gating, after RUS (WI-8). |
| Single-instance-per-bone localizer assumption | Doctor confirmation catches mislocation; per-bone confidence surfaced. |
| Suggestion mistaken for a per-bone "age" | Output is stage + confidence only; ages come from Plan 1 group scores; report wording enforces it. |
| Model auto-promotion | Ships only through Plan 5/Plan 2 release gate. |

---

## 9. Definition of Done

- [ ] Localizer trained on public data, shipped, and passing its error gate; `predict_boxes` seeds the box editor with adjustable boxes (WI-1/2/3).
- [ ] Per-bone ordinal stagers trained on Plan 2's consensus crops, only for bones meeting coverage (WI-4).
- [ ] `predict_stage` surfaces calibrated suggestions **only** for gated bones; every stage is doctor-confirmed; overrides captured (WI-5/6).
- [ ] End-to-end auto-TW3-as-suggestion produces a clinician-confirmed 20-bone report with **separate** RUS/carpal ages and a screening cross-check (WI-7).
- [ ] Carpals localized + staged behind independent gates, after RUS passes (WI-8).
- [ ] No model auto-promotes; all ship through the Plan 5/Plan 2 gate. Full suite green.

---

## 10. Open decisions to confirm

1. **Colab/Kaggle GPU** for WI-1/WI-4 training — confirmed available?
2. **BoNet keypoint release** on hand: which version (drives the `LANDMARK_TO_BONE` mapping in `baar_to_jsonl.py`)?
3. **Coverage threshold to start training a bone:** the `STAGE.md` default (~50/stage across distinct patients), or a different bar per bone difficulty?
4. **Localizer error target (px)** and **staging gate** (κ overall ≥ 0.80, per-bone ≥ 0.70) — adopt `validation_protocol.md §6` or adjust?
5. **Suggestion default:** off until each bone individually passes its gate (recommended), vs shown-as-hint earlier with a prominent "unvalidated" flag?
6. **Carpal timing:** attempt carpals as soon as RUS passes, or defer until RUS is externally validated (Plan 5 run)?

---

*This plan builds the automatic per-bone AI as clinician-confirmed suggestions. It does not enter licensed tables (Plan 1), build the capture UI / data engine / release persistence (Plan 2), or define the evaluator/gate (Plan 5) — it trains the models those plans need and consumes the machinery they provide. The localizer is startable now; the stager follows Plan 2's data.*

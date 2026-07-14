# Plan 3 — Screening-Model Accuracy, Calibration & Reproducibility Upgrade

**Status:** Ready to implement · **Owner:** (assign) · **Created:** 2026-07-13
**Branch target:** dedicated `feat/screening-model-upgrade`
**GPU:** needed **only at train time** (free Colab/Kaggle). Clinic inference stays **CPU / ONNX** — a hard constraint on every architecture choice here.
**Scope of this model (do not blur):** the whole-image, Greulich-Pyle-style **screening/triage** estimate — a *suggestion the doctor verifies*, shown as a **separate cross-check**, explicitly **NOT TW3**. Improving it makes the triage line better and the cross-check sharper; it does **not** change the primary clinician-confirmed TW3 report (that is Plan 1). Keep this framing in every UI string and report field.

> **How to use this document.** Self-contained implementation source. Read §2 first — the premise most people assume ("retrain on the full RSNA set for a big jump") is **already done**. The real levers now are cropping, calibration quality, reproducibility, and a *learned* India recalibration. Consumes the release gate from [PLAN-2](PLAN-2-self-learning-flywheel.md) (WI-7) and the metric evaluator from Plan 5; uses external context from [the CPP reference report](REFERENCE-cpp-skeletal-maturation-study.md).

---

## 1. Purpose (why this plan)

The screening model is the fast, whole-image number the app shows the moment a film is uploaded, before any manual TW3 grading. It is a *triage and cross-check* signal: it flags "this hand looks roughly 10 yr" so a discrepancy with chronological age is caught early, and it gives an independent sanity check against the doctor's TW3 read. Its accuracy therefore matters for *safety and workflow*, even though it is never the clinical result.

The value of improving it is real but bounded, and must be stated honestly: a better screening number **reduces missed discrepancies and false alarms at triage**, and a better-calibrated uncertainty **tells the clinician when to trust or ignore it**. It does not, and must not be claimed to, improve the TW3 bone age.

---

## 2. Current state — the premise has already moved

**What is actually shipped (verified from the repo, not from the docs):**

- `backend/ai/models/boneage_gp.onnx` **is committed** (MobileNetV3-Small, ~4.3 MB) — not gitignored. The metadata `boneage_gp.json` shows it was trained on the **full RSNA set**: `n_images: 12611`, `input_size: 224`, **`val_mae_months: 8.6`**, `n_val: 1891`, mode `ft` (fine-tune), Colab-trained.
- **Conformal intervals are calibrated and shipped**: split-conformal quantiles on the RSNA val split (seed 42, first 15%) — `{0.80: 13.9, 0.90: 18.6, 0.95: 22.1}` months — self-validated (recomputed MAE 8.6 == metadata). `boneage.predict_months` returns the 90% conformal interval, with a labelled `±MAE` fallback.
- **Training + calibration pipelines exist and are clean:** `train_boneage.py` (auto-detects CSV layout, deterministic 15% val split via `default_rng(42)`, MobileNetV3-Small backbone + sex-concatenated head, L1 loss, cosine LR, light hand-safe augmentation — no horizontal flip because hands are always left), and `calibrate_conformal.py` (reproduces the exact split, writes quantiles).
- **Honest population note is already in the output:** `boneage.predict_months` returns a `population_note` warning that GP runs ~0.5–0.7 yr delayed in Indian children and to treat the number as screening only.

**So the naive plan is void.** `RETRAIN.md` still claims "the shipped model saw only ~1,425 images → MAE ≈ 14 months" and frames "train on 9× data" as the lever — that is **stale**; the shipped model is already the full-RSNA 8.6 mo model. Fixing that doc is WI-1.

**Where the real headroom is.** The RSNA challenge's best test MAE was **~4.2 months** (`validation_protocol.md §6`); the product's provisional engineering gate is **≤ 6 months**. We are at 8.6. The gap to ~4–6 mo is closed not by more data but by:

1. **Hand-region cropping** before regression (background removal / registration — the single biggest lever the RSNA winners used).
2. **Sharper, subgroup-honest uncertainty** (the current ±18.6 mo @90% is wide and *uniform* across all cases).
3. **Architecture/input** improvements that stay within a CPU latency budget.
4. **A learned, subgroup-validated India recalibration** — never a universal offset (`MASTER audit BA-03`).
5. **Reproducibility + governance** so any new model is comparable and ships only through a gate.

---

## 3. Target architecture

```
        TRAIN TIME (Colab/Kaggle GPU, offline)                 INFERENCE (clinic, CPU/ONNX)
   ┌───────────────────────────────────────────┐        ┌──────────────────────────────────────┐
   │ RSNA images + labels                       │        │ upload → acceptability gate (built)    │
   │   │                                        │        │   │ accepted                           │
   │   ▼  hand-crop (WI-2)                       │        │   ▼  hand-crop (same code, WI-2)        │
   │ crop/register hand ROI                      │        │ crop/register hand ROI                 │
   │   │                                        │        │   │                                    │
   │   ▼  backbone + sex head (WI-5 upgrade?)    │        │   ▼  ONNX session (CPU)                 │
   │ train (seed-pinned recipe, WI-1)           │        │   ▼  TTA average (WI-4)                 │
   │   │  → candidate .onnx + metadata          │        │ point estimate (months)                │
   │   ▼                                        │        │   │                                    │
   │ calibrate conformal, PER SUBGROUP (WI-3)   │──────▶ │   ▼  subgroup-conditional interval (WI-3)│
   │   │  quantiles by sex × age-band            │        │ [lo, hi] @ coverage  +  abstain if wide │
   │   ▼                                        │        │   │                                    │
   │ India recalibration layer (WI-6, data-gated)│──────▶ │   ▼  learned recal (if active, WI-6)     │
   │   │                                        │        │ screening estimate + population caveat  │
   │   ▼  model card + latency benchmark (WI-8) │        │ (shown as SEPARATE cross-check, not TW3)│
   └───────────────┬───────────────────────────┘        └──────────────────────────────────────┘
                   │ candidate
                   ▼
        RELEASE GATE (Plan 2 WI-7): beat incumbent on LOCKED test ∧ no subgroup regression
        ∧ calibrated ∧ CPU-latency within budget ∧ human sign-off  → replace shipped ONNX
                   │ (fail → stays a candidate; shipped model untouched)
```

**Invariants:**
- Inference is CPU/ONNX only; every change is measured against a **CPU latency budget** (WI-8). A model that can't run on the clinic CPU is not a candidate, however accurate.
- The shipped ONNX is **never overwritten** except through the Plan 2 release gate.
- Preprocessing MUST be identical in train and inference (the existing `boneage.preprocess` ↔ trainer contract) — extend both together or neither.
- The screening estimate is labelled a cross-check, not TW3, everywhere.
- India adjustment is **learned + subgroup-validated**, never a fixed universal offset.

---

## 4. Work items

Each item = one reversible, tested commit; suite stays green. Training runs are offline (Colab) and produce a candidate; only WI-8/Plan-2 promote it.

### WI-1 — Correct stale docs + freeze a reproducible training recipe  *(foundation, no GPU)*
- **Why:** `RETRAIN.md` misdescribes the shipped model (claims 1,425 img / 14 mo; reality 12,611 / 8.6 mo), which will mislead the next trainer. And the recipe that produced 8.6 mo isn't captured as a versioned artifact, so results aren't reproducible or comparable.
- **How:** rewrite `RETRAIN.md` to the true baseline. Add `backend/ai/training_recipe.json` (arch, `input_size`, seed, split fraction, augmentation params, LR schedule, epochs, loss) and stamp its hash into model metadata. Extend metadata into a proper **model card** section (intended use, data, subgroup metrics placeholder, limitations, India caveat).
- **Files:** `backend/ai/RETRAIN.md`, `backend/ai/train_boneage.py` (emit recipe + card), `backend/ai/models/boneage_gp.json`.
- **Tests:** metadata carries recipe hash + card fields; recipe re-run reproduces the split indices deterministically.
- **Acceptance:** the shipped baseline is documented truthfully and reproducibly.

### WI-2 — Hand-region crop before regression  *(highest accuracy lever)*
- **Why:** whole-image regression wastes capacity on background/forearm/annotations; cropping/registering the hand ROI is what the strongest RSNA models did. Expected to move MAE most.
- **How:** add a coarse hand-bbox crop in a shared preprocessing step used by **both** trainer and `boneage.preprocess` (reuse the Plan 4 localizer's coarse hand box if available, else a lightweight saliency/threshold crop; honest fallback = full image). Retrain on Colab; report val-MAE delta vs 8.6.
- **Files:** `backend/ai/boneage.py` (preprocess), `backend/ai/train_boneage.py`, a shared `backend/ai/handcrop.py`, tests.
- **Tests:** crop is deterministic and identical in train vs inference paths; degrades gracefully to full image; a synthetic case crops the expected region.
- **Acceptance:** a Colab retrain with cropping beats 8.6 mo on the held-out split (target ≤ ~7 mo as a first step); if it doesn't, it doesn't ship.

### WI-3 — Subgroup-conditional (Mondrian) conformal intervals  *(honesty + usefulness, no GPU)*
- **Why:** the current ±18.6 mo @90% is **marginal** — the same width for a clear 6-yo film and an ambiguous pubertal one. Group-conditional conformal gives coverage *within* sex × age-band and sharpens intervals where the model is reliable.
- **How:** extend `conformal.calibrate` / `calibrate_conformal.py` to compute quantiles per `(sex × age-band)` bucket (fall back to the marginal quantile when a bucket is too small to guarantee coverage — the code already returns the widest supported residual in that case). `boneage.predict_months` selects the bucket's interval and reports which bucket + its empirical coverage. Buckets follow `validation_protocol.md §3` age bands.
- **Files:** `backend/ai/conformal.py`, `backend/ai/calibrate_conformal.py`, `backend/ai/boneage.py`, tests.
- **Tests:** per-bucket empirical coverage ≥ target on the val split; tiny buckets fall back safely; interval never negative/over 240 mo.
- **Acceptance:** intervals vary by subgroup, coverage holds per bucket, and the output states its bucket.

### WI-4 — Test-time augmentation + abstention  *(cheap gain + safety, CPU-budgeted)*
- **Why:** averaging a few small deterministic augmentations at inference reduces variance for a few hundred ms; an abstention rule stops the model volunteering a confident number on a borderline image.
- **How:** deterministic TTA (small rotations/zooms, no flip) averaged in `predict_months`, behind a config flag with a measured latency cost. Add an **abstention rule**: if the predicted (subgroup) interval width exceeds a threshold, or the image is flagged low-trust/OOD, the screening estimate abstains ("manual assessment") — reusing the existing acceptability gate wiring in `api_bone_age.estimate`.
- **Files:** `backend/ai/boneage.py`, `backend/api_bone_age.py`, tests.
- **Tests:** TTA is deterministic; abstention triggers above threshold and on low-trust domains; latency stays within the WI-8 budget.
- **Acceptance:** borderline/low-trust cases abstain; TTA improves or holds MAE within budget.

### WI-5 — Architecture / input-size upgrade experiment  *(GPU, gated)*
- **Why:** larger input (288) and/or a stronger-but-CPU-viable backbone can close more of the gap to ~4–6 mo — *only if* CPU latency stays acceptable.
- **How:** on Colab, sweep {224, 288} × {MobileNetV3-Small (incumbent), a slightly heavier CPU-friendly net}. Select a candidate **only** if it beats the incumbent on the locked split **and** passes the WI-8 CPU latency budget. Keep the sex-conditioned head and L1/Huber loss.
- **Files:** `backend/ai/train_boneage.py` (arch flag), model card, tests (arch flag wiring).
- **Acceptance:** at most one candidate advances, and only via the Plan 2 gate; the shipped model is untouched until then.

### WI-6 — Learned India recalibration layer  *(data-gated; NOT a universal offset)*
- **Why:** the model is RSNA (US); GP skeletal age runs biased in Indian children, but **bias varies by sex, age, and puberty** — a fixed offset is explicitly wrong (`MASTER audit BA-03`). The right tool is a small **post-hoc, monotone, per-(sex × age-band) recalibration** learned from Indian expert-read films and validated by subgroup.
- **How:** a `backend/ai/india_recal.py` post-map (isotonic/monotone per bucket), fit offline on Indian labelled data, shipped **only** when it beats the uncalibrated model on Indian subgroups via the Plan 2 gate. **Inactive until that data exists** (you currently lack an Indian cohort) — scaffolded now, activated later; the Plan 2 flywheel is the mechanism that could accumulate those labels. The output must disclose whether recalibration is active and on what data it was fit.
- **Files:** `backend/ai/india_recal.py`, `backend/ai/boneage.py` (apply if active), tests (synthetic per-bucket map; disabled by default).
- **Acceptance:** with no Indian data the layer is inert and disclosed as inactive; a synthetic bucketed map applies correctly when enabled; no code path applies a single universal offset.

### WI-7 — Aleatoric uncertainty head  *(optional/experimental)*
- **Why:** a mean-variance head (predict σ alongside age) gives a per-image confidence that complements the distribution-free conformal interval and improves the WI-4 abstention decision.
- **How:** optional second output trained with a Gaussian NLL; conformal remains the coverage guarantee, σ informs abstention/ranking. Off by default until validated.
- **Files:** `backend/ai/train_boneage.py`, `backend/ai/boneage.py`, tests.
- **Acceptance:** σ correlates with actual error on the val split; conformal coverage is unaffected.

### WI-8 — CPU latency budget + reproducibility + release integration  *(cross-cutting)*
- **Why:** guarantees a candidate is deployable and comparable, and that promotion goes through the gate.
- **How:** `backend/ai/benchmark.py` measures single-image CPU latency (p50/p95) for a candidate ONNX; a candidate must stay within a stated budget (decision below). Package the candidate + model card + metrics and hand to the **Plan 2 WI-7 release gate** (beat incumbent on locked test, no subgroup regression, calibrated, signed off). Never overwrite `boneage_gp.onnx` outside the gate.
- **Files:** `backend/ai/benchmark.py`, integration with Plan 2 `release.py`, tests.
- **Acceptance:** every candidate has a latency report + model card; promotion only via the gate.

---

## 5. Sequencing

```
WI-1 (recipe/doc) ─┬─▶ WI-3 (subgroup conformal) ─▶ WI-4 (TTA + abstain)
                   │                                     │
                   ▼                                     ▼
                 WI-2 (hand crop, GPU) ─▶ WI-5 (arch/input, GPU) ─▶ WI-8 (latency + release gate)
                                                             │
                                          WI-6 (India recal, data-gated) — scaffold now, activate later
                                          WI-7 (aleatoric head) — optional, any time
```
Recommended order: **WI-1 → WI-3 → WI-4 → WI-2 → WI-5 → WI-8 → WI-6 → WI-7.** WI-1/WI-3/WI-4 need **no GPU** and deliver reproducibility + honest, sharper uncertainty immediately. WI-2/WI-5 are the GPU accuracy work. WI-6 waits on Indian data.

---

## 6. Test & verification plan

- **Unit:** each WI ships pytest (extend `tests/bone_age/test_conformal.py` etc.). Keep the existing 43+ bone-age tests green.
- **Offline training runs (Colab):** report held-out MAE vs the 8.6 incumbent for WI-2/WI-5; a run that doesn't beat 8.6 is not a candidate.
- **Calibration validation:** per-subgroup empirical coverage on the val split meets targets (WI-3).
- **Negative controls (stay red-when-broken):** a candidate exceeding the CPU latency budget cannot ship; a candidate not beating the incumbent cannot ship; India recalibration is inert without Indian data; the shipped ONNX is never overwritten outside the gate.
- **Browser verification:** upload a film, confirm the screening estimate shows a subgroup-labelled interval, abstains on a low-trust image, and is clearly labelled "screening cross-check, not TW3." Never use real patient films on a shared host.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Overfitting to RSNA (US) → worse on Indian/clinical films | Learned subgroup recalibration (WI-6); keep the population caveat; Plan 5 external validation before any accuracy claim. |
| Heavier arch breaks CPU latency | Hard CPU latency budget + benchmark gate (WI-8); prefer efficient nets. |
| Subgroup conformal buckets too small → unstable/wide | Safe fallback to the marginal quantile (already in `conformal_quantile`); minimum bucket size. |
| Ensemble/TTA cost | Budgeted; TTA behind a flag; ensemble only if within latency. |
| Sharper interval read as higher accuracy | UI wording: interval is coverage, not correctness; abstention on wide intervals. |
| Screening number mistaken for TW3 | Persistent "cross-check, not TW3" labelling in output + report field naming. |
| Fixed India offset creeping back in | Explicitly prohibited; WI-6 is per-subgroup + validated; test asserts no universal-offset path. |

---

## 8. Definition of Done

- [ ] `RETRAIN.md` and metadata truthfully describe the shipped full-RSNA 8.6 mo baseline; a versioned training recipe + model card exist and reproduce the split (WI-1).
- [ ] Hand-crop preprocessing is shared by train + inference and a cropped retrain beats 8.6 mo (WI-2).
- [ ] Conformal intervals are subgroup-conditional with per-bucket coverage held; the output states its bucket (WI-3).
- [ ] TTA + an abstention rule are in place, within the CPU latency budget (WI-4).
- [ ] Any arch/input upgrade ships only after beating the incumbent and passing the latency + Plan 2 release gate (WI-5, WI-8).
- [ ] A learned, subgroup-validated India recalibration layer is scaffolded, disclosed, and inert until Indian data exists — with no universal-offset path (WI-6).
- [ ] Full suite green; screening flow browser-verified and clearly labelled non-TW3.

---

## 9. Open decisions to confirm

1. **CPU latency budget:** acceptable p95 per image on the clinic machine (e.g. ≤ 300 ms?) — this caps arch/input/TTA/ensemble choices.
2. **Colab/Kaggle GPU access:** confirmed available for the WI-2/WI-5 training runs? (you don't have an in-house GPU.)
3. **Target MAE:** stop at ≤ 6 mo (the product gate) or push toward the RSNA ~4.2 mo frontier?
4. **Ensembling:** acceptable given its inference cost, or single-model only?
5. **Any Indian expert-read films at all** (even a small set) to begin WI-6, or is it fully deferred until the Plan 2 flywheel accumulates them?
6. **Abstention threshold:** interval-width (and OOD) cutoff above which the screening estimate declines to show a number.

---

*This plan improves the screening/triage cross-check and its uncertainty. It does not change the clinician-confirmed TW3 bone age (Plan 1), train the per-bone models (Plan 4), or constitute external clinical validation (Plan 5); it reuses Plan 2's release gate and Plan 5's evaluator.*

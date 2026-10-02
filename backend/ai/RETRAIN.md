# Retrain / refine the bone-age screening model

> **Current baseline (corrected 2026-07-13).** The **shipped** model is already
> trained on the **full RSNA set** — see `backend/ai/models/boneage_gp.json`:
> `n_images: 12611`, `input_size: 224`, **`val_mae_months: 8.6`**, with conformal
> intervals calibrated. The old "~1,425 images → MAE ≈ 14 months" note was stale
> and has been removed. "Just add more data" is no longer the lever — that lever
> is spent.

The remaining accuracy headroom (toward the RSNA-achievable ~4–6 months) is in
**cropping, calibration, architecture/input, and a learned India recalibration**.
The reproducible
recipe that produced the shipped model is pinned in
`backend/ai/training_recipe.json`.

This is still a whole-image Greulich-Pyle **screening** estimate — **NOT TW3** — a
suggestion the doctor verifies, shown as a separate cross-check.

> The accurate clinical result stays the doctor-graded **20-bone TW3** report
> (Advanced → grading + Licensed TW3 tables). This model is only the rough triage.

## Retraining (still valid, e.g. after a data or recipe change)

## 1. Get the data (free)

Either source gives the same challenge data:

- **Kaggle** — `boneage-training-dataset` (images, named `<id>.png`) +
  `boneage-training-dataset.csv` (columns `id, boneage, male`).
  <https://www.kaggle.com/datasets/kmader/rsna-bone-age>
- **Stanford AIMI** (registration): <https://aimi.stanford.edu/rsna-bone-age>

Unzip so you have an images folder and the CSV. The trainer auto-detects the CSV
columns, so both the Kaggle layout (`id,boneage,male`) and the bundled layout
(`Image ID,male,Bone Age (months)`) work.

## 2. Train

CPU here is too slow for 12k images — **use a free Colab/Kaggle GPU** (the trainer
auto-detects CUDA). On the GPU machine, with the repo checked out:

```bash
python -m backend.ai.train_boneage \
    --data /path/to/boneage-training-dataset \
    --csv  /path/to/boneage-training-dataset.csv \
    --img-size 224 --epochs 30
```

- `--img-size 224` — bigger input = better accuracy (inference reads this size
  from the metadata, so 224 "just works" locally). 288 is even better if the GPU
  allows; 160 is the current shipped size.
- Env vars work too: `RSNA_DATA_DIR=... RSNA_CSV=... python -m backend.ai.train_boneage --img-size 224`.
- Quick pipeline check (seconds, on the bundled validation set):
  `python -m backend.ai.train_boneage --limit 200 --epochs 1`

The script prints the **held-out MAE** each epoch — that is the real accuracy.

## 3. Deploy

Training writes two files:

```
backend/ai/models/boneage_gp.onnx   # the model (gitignored)
backend/ai/models/boneage_gp.json    # metadata incl. val_mae_months + input_size
```

Copy both back into `backend/ai/models/` on the clinic machine and restart the
app. The UI's "AI rough screening" line and its `±~N mo` badge update from the new
metadata automatically. Nothing else changes; inference stays local CPU/ONNX.

## Notes
- `torch` / `torchvision` are **training-only** deps (root `requirements-ml.txt`, install into a separate environment);
  the clinic runtime only needs `onnxruntime`.
- Hands are always left, so the augmentation never flips horizontally (that would
  corrupt laterality).
- To go beyond whole-image accuracy you need **true auto-TW3** (per-bone stage
  classification → your TW3 tables). That needs stage-labelled crops, which the
  in-app annotation + dataset exporter are set up to collect.

## Measured and rejected without retraining (18 September 2026)

Everything below used the **shipped** model with v1 preprocessing. Method: the
trainer's 15% val split was reconstructed exactly (seed 42 over `train-labels.csv`
order — it reproduces the recorded val MAE, **8.59** vs 8.6) and split in half
by sex: half A to **fit**, half B to **select and calibrate**. The locked RSNA
validation set (1,425) was evaluated **at most once** per candidate, and not at
all for a candidate that failed on half B. The shipped baseline reproduces
exactly on it: **MAE 8.993**.

| Candidate | Val half B | Locked test | Decision |
|---|---|---|---|
| Shipped (identity) | 8.558 | 8.993 · 90% coverage 0.8954 | — |
| Per-sex linear recalibration | 8.555 | not run | no gain |
| Per-sex quadratic | 8.426 | not run | superseded |
| Per-sex cubic (best on B) | 8.412 | **8.856** · coverage 0.8828 | **rejected** |
| Monotone binned recalibration | 8.452 | not run | inferior |
| 5-view test-time augmentation (±6°, ×0.96/1.04, inside the training envelope) | **9.010** (worse) | not run | **rejected** |

Why the cubic was rejected despite a lower mean: −0.14 months (1.5%) is
clinically nothing, it made subgroups worse (boys 5–8 y 8.93 → 10.39; girls
12–15 y 8.60 → 9.33) and the re-calibrated 90% interval under-covered (0.883).
A change that improves the average by moving error onto particular children is
not an improvement.

**Coverage 0.8954 vs 0.90 is within noise** (SE ≈ 0.008 at n = 1,425). The
methodological flaw behind it is still real: the trainer picks the best of 25
epochs on the same split `calibrate_conformal` later uses, so the intervals are
calibrated on the selection set. **Next training run: carve a separate
calibration split (never used for epoch selection) and calibrate on that.**

**Conclusion:** the remaining error is in the model, not its output. The levers
are a retrain (higher resolution than 224 px, stronger backbone, a proper
calibration split — needs a GPU; this machine is CPU-only) or adopting digiBONE
(see `DIGIBONE.md`). Scripts: the study was run from throwaway scripts; the
numbers above are the record.

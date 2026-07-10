# Retrain the bone-age screening model on the full RSNA set

The shipped model saw only ~1,425 images → **MAE ≈ 14 months**. The full RSNA
training set is ~**12,611 images** (~9× more data), which is the dominant lever
for accuracy. Same architecture on the full set typically reaches **MAE ≈ 6–9
months**. It's still a whole-image Greulich-Pyle *screening* estimate — **not
TW3** — but far more useful as a triage number.

> The accurate clinical result stays the doctor-graded **20-bone TW3** report
> (Advanced → grading + Licensed TW3 tables). This model is only the rough triage.

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
- `torch` / `torchvision` are **training-only** deps (see `requirements-ml.txt`);
  the clinic runtime only needs `onnxruntime`.
- Hands are always left, so the augmentation never flips horizontally (that would
  corrupt laterality).
- To go beyond whole-image accuracy you need **true auto-TW3** (per-bone stage
  classification → your TW3 tables). That needs stage-labelled crops, which the
  in-app annotation + dataset exporter are set up to collect.

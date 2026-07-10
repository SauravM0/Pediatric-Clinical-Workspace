# Bone localizer (PEA) — data, training, deploy

Implements the **PEA module** of PEARLS (Zhang et al., 2023): predict one center
point per RUS bone from a hand X-ray, then crop a ROI around each. This is the
"auto-find the bones" step — it lets the doctor confirm/nudge crops instead of
hunting, and feeds crops to the future staging AI.

Unlike the staging model, **localization can be trained on fully public data** —
RSNA hand X-rays + keypoint annotations. No private labels, no scoring tables.

## 1. Data

- **Images**: RSNA Pediatric Bone Age hand X-rays (same source as the screening
  model). <https://www.kaggle.com/datasets/kmader/rsna-bone-age>
- **Keypoints**: the annotations the paper uses (ref [26]) — the **BAAR/BoNet**
  hand keypoint set for RSNA. <https://bcv-uniandes.github.io/baar-wp/> (and
  <https://github.com/BCV-Uniandes/Bonet>). These give per-image hand keypoints.

## 2. Convert keypoints → the trainer's format

The trainer reads **JSONL**, one line per image, points in ORIGINAL pixels, in
`RUS_BONES` order (`radius, ulna, mc1, mc3, mc5, pp1, pp3, pp5, mp3, mp5, dp1, dp3, dp5`):

```json
{"image": "1377.png", "points": [[x,y], [x,y], ... 13 pairs ...]}
```

Use `null` for any bone whose point is unknown (it's skipped in the loss).

**Use the converter `backend/ai/baar_to_jsonl.py`** — it parses the BoNet
annotations (COCO JSON / record list / CSV), maps each landmark to a RUS bone
centre, and writes the JSONL. The keypoint *index → bone* ordering depends on the
BoNet release, so it is **not guessed** — you set it once and verify visually:

```bash
# 1. see how the keypoints are indexed in YOUR download
python -m backend.ai.baar_to_jsonl --inspect --ann bonet_rsna.json
# 2. edit LANDMARK_TO_BONE at the top of baar_to_jsonl.py (index or (i,j) midpoint per bone)
# 3. eyeball the mapping on a few films
python -m backend.ai.baar_to_jsonl --preview 8 --ann bonet_rsna.json --images rsna/images
# 4. generate the training JSONL
python -m backend.ai.baar_to_jsonl --ann bonet_rsna.json --images rsna/images --out keypoints.jsonl
```

A partial mapping is fine (unmapped bones train from other images). Pure parse/map
logic is covered by `python -m backend.ai.baar_to_jsonl --selftest`.

## 3. Train (Colab/Kaggle GPU; auto-detects CUDA)

```bash
python -m backend.ai.train_localizer \
    --data /path/to/rsna/images \
    --ann  /path/to/keypoints.jsonl \
    --img-size 512 --epochs 60
```

- `--img-size 512` matches the paper (mAP 86.29%); smaller is faster/less accurate.
- Prints validation **peak error (heatmap px)** each epoch.
- Quick pipeline check (no real data needed):
  `python -c "from backend.ai.train_localizer import *; d,a=synth_dataset('/tmp/loc'); train(_load_ann(a), d, img_size=128, epochs=10, point_names=['a','b','c','d'])"`

## 4. Deploy

Training writes:

```
backend/ai/models/localizer.onnx    # the model
backend/ai/models/localizer.json     # metadata: input_size, stride, point_names, box_frac, peak-err
```

Copy both into `backend/ai/models/` on the clinic machine. `backend/ai/localize.py`
loads them for local CPU/ONNX inference (`predict_boxes(image)` → one box per bone).
If the files are absent it returns `None` (honest degradation).

## 5. What's next (after localization works)

- Wire `predict_boxes` into the app: upload film → show the 13 auto-boxes over the
  image → doctor drags to correct → crops saved to `BoneAssessment.localisation_box`
  (the dataset exporter already turns boxes into crops).
- Those doctor-confirmed crops are the training data for the **RL ordinal staging**
  model (PEARLS RL module) — the step that actually predicts each bone's stage.
- Carpals: add 7 more points once RUS localization is validated.

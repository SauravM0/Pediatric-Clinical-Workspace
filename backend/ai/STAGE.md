# Per-bone TW3 stage classifier (PEARLS RL module)

This is the AI that **reads each bone's maturity stage (A–I) from its crop** — the
step that would auto-fill the per-bone stages the doctor confirms. It uses an
**ordinal cumulative-link model** (respects A<B<…<I, per the PEARLS paper Eq. 8–9),
one model per bone.

It is the *last* AI piece and the hardest, because of the data it needs.

## The data it needs (the real bottleneck)

Crops **labelled with each bone's stage**. There is **no public dataset** with
per-bone TW3 stage labels (RSNA has only whole-image ages). The PEARLS authors had
**3 pediatricians hand-label 1,200 films**. In this app you collect the same data
as a by-product of normal work:

1. Attach a film, **auto-locate or draw the bone boxes** (box editor).
2. **Grade each bone** (you already do this).
3. **Export the dataset** — `python -m backend.tw3.pipeline.export_dataset --out dataset`.
   That writes `dataset/crops/…` + `dataset/annotations.jsonl` with
   `bone_code, confirmed_stage, crop_path` for every graded, boxed bone.

The **coverage dashboard** tells you when each bone×stage has enough examples.
Rule of thumb (from the directive): a bone becomes a *candidate* for AI once it has
~50+ examples per stage across distinct patients.

## Train (Colab/Kaggle GPU)

```bash
python -m backend.ai.train_stager --dataset dataset --img-size 128 --epochs 40
# or a few bones at a time:
python -m backend.ai.train_stager --dataset dataset --bones radius,ulna
```

- One model per bone; each prints `val acc` and `within-1` (adjacent-stage) accuracy.
- Bones with <2 stages or <8 crops are skipped automatically.
- Exports `backend/ai/models/stager/<bone>.onnx` (+ `.json` with the stage list + metrics).

## Deploy + use

Copy the `stager/` folder into `backend/ai/models/`. Then
`backend/ai/stage_classifier.predict_stage(crop, bone_code)` returns the top stage,
second stage, per-stage probabilities and a confidence. Wire it as **suggestions the
doctor confirms** — never auto-final.

## What earns the doctor's trust (do this before turning suggestions on)

1. **Gate suggestions**: only offer a stage where the bone has enough training
   support AND model confidence is above a *validated* threshold; else show
   "manual." (softmax/ordinal prob is not calibrated confidence — validate it.)
2. **Locked test set**: measure per-bone accuracy, weighted-κ, within-1 rate, and
   error>1-stage rate, split by sex / age band / image domain. Show these numbers.
3. **Doctor confirms every bone**; corrections are audited and feed the next round.
4. **Separate carpals** — evaluate + gate them independently (they're harder).

## Status
Code is complete and tested (synthetic). No model ships — it needs your labelled
crops first. The engine → scoring path (once your TW3 tables are entered) then turns
confirmed stages into the bone ages automatically.

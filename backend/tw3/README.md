# Automatic TW3-RUS Bone Age — engineering roadmap

Goal: upload a hand/wrist X-ray → automatic **TW3-RUS** bone age (+ height, QRISK3
downstream), with clinician confirmation, no manual atlas lookup or typing.

Design follows **PEARLS** (Zhang et al., *J Digit Imaging* 2023) — the automated
TW3-RUS system in `../../TW3 research/`. Three modules:

1. **PEA** — locate the 13 RUS bones (object/point detection).
2. **RL** — classify each bone's maturity **stage A..I** (ordinal regression).
3. **S** — stages → RUS score → bone age via the conversion tables. ✅ **Built** here
   (`scoring.py`, `tw3_tables.json`), deterministic and exact once tables are filled.

## Why the RSNA / Kaggle data does NOT train this

`kmader/rsna-bone-age` and the "Bone Age Validation Set" folder carry **one
Greulich–Pyle number per image (months)** and **no per-bone stages**. They can only
train GP whole-image regression — the wrong method, wrong labels, Western cohort.
PEARLS trained its stage module on a **stage-annotated** dataset. Automatic TW3
staging therefore requires images labelled with each bone's A..I stage.

## The data we actually need (unblocks PEA + RL)

Dr. Rathod's reports already contain the labels: 13 stages + RUS score + bone age.
Each report + its digital film = one training record. To build the training set,
export from PACS per case:

- **Digital image**: original **DICOM** (preferred) or lossless **PNG**, left hand/wrist,
  full field — *not* a phone photo of printed film.
- **Report fields**: sex, chronological age, the 13 RUS stages, RUS grade score,
  TWIII-RUS bone age (see `labels/seed_labels.json` for the exact schema, seeded with
  the two verified 2026 cases).

Rough scale (PEARLS-class accuracy): a few hundred stage-annotated films to fine-tune
per-bone stage classifiers on Indian children; more is better. Fewer is still useful
for calibration/validation.

## The conversion tables (for `tw3_tables.json`)

`stage_to_score[sex][bone][stage]` and `score_to_age[sex]` are the copyrighted
TWIII-RUS tables (TW3, 2001). They are **not bundled**. Paste the values your centre
is licensed for. `score_to_age.girls` is currently seeded only with the two anchors
derived from Dr. Rathod's reports (681→12.1, 713→12.4) — replace with the full curve.

## Data pipeline (built + tested)

Turns radiology reports into a validated TW3 training set and tells you what to
export from PACS. Reports go in `pipeline/sample_reports/*.txt` (transcribed or
OCR'd); run:

    python -m backend.tw3.pipeline.build_dataset --out backend/tw3/pipeline/manifest.json

It parses the 13 RUS stages per report, validates each record, and prints a
**stage-coverage grid**. On the two seed reports it correctly reads all bones but
shows only 18/117 (bone × stage) cells covered (stages F/G/H only) — proof that
same-age films can't train a classifier. Export films across a wide age range so the
empty cells fill; pair each report `.txt` with its DICOM/PNG via `image_ref`.

- `pipeline/report_parser.py` — free-text report → structured stages/scores/ages.
- `pipeline/dataset.py` — validation + coverage analysis.
- `pipeline/build_dataset.py` — CLI readiness report.
- `pipeline/image_prep.py` — DICOM/PNG → normalized array (needs `requirements-ml.txt`).

## Status

- `scoring.py` — deterministic stage→score→age; honest status when tables/stages
  are missing (never guesses). Self-test: `python -m backend.tw3.scoring`.
- `pipeline/` — reports → validated labels + coverage report. **Done + tested.**
- Next: PEA + RL models (needs a wide-age stage-annotated archive + a GPU, e.g.
  Colab). Until then the app uses clinician-confirmed staging (assisted, no atlas
  lookup), and `scoring.py` gives the exact bone age once the licensed tables load.

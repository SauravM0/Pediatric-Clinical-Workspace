# Obtaining the licensed TW3 tables

**Status: not obtained.** Unlike the other outstanding assets this one is not an
email — it is a book purchase, and it is the only way to make the deterministic
bone-age path real.

> Tanner JM, Healy MJR, Goldstein H, Cameron N.
> **Assessment of Skeletal Maturity and Prediction of Adult Height (TW3 Method).**
> 3rd edition. London: W.B. Saunders, 2001. ISBN 0-7020-2511-9.

## Why this is the highest-value purchase in the project

The bone age this product currently reports is **not TW3**. Its per-stage points
were transcribed from Table 1 of a deep-learning conference paper, and its
score→age curve was digitized off Figure 8 of that same paper — 10–11 anchors at
integer years, self-declared ±0.5 y. On this centre's own films it disagrees with
the historically reported original-TW3 RUS by roughly **0.9–1.25 years of bone
age**, which is the difference between reassurance and a growth-hormone work-up.

Every gate needed to receive the real values is already built and tested. The
book is the only missing input.

## What it unblocks

| Currently | With the licensed tables |
|---|---|
| TW3-C points from a conference paper | Real TW3 RUS points, all 13 bones |
| Score→age digitized from a figure, ±0.5y | The published conversion at native resolution |
| Carpal scoring absent entirely | Carpal (7 bones) as its own scored system |
| Per-bone valid letters unknown → A–I offered everywhere | Derived automatically from the entered points |
| No adult-height prediction from bone age | `pct_adult_height` → predicted adult height |
| UI must say "provisional, not Tanner TW3" | Can state the method plainly |

## What to buy, and what to avoid

Buy the **3rd edition (TW3, 2001)**. Specifically *not*:

- **TW2 (1975/1983)** — a different standard. Its skeletal ages run about a year
  higher in adolescence, and it *does* define a 20-bone score, which TW3 does
  not. Mixing them is the error this product already documents.
- **Greulich–Pyle atlas** — a different method entirely, and the basis of the
  separate AI screening path. Never interchangeable with TW3.

Copies circulate second-hand; the ISBN above is the one to match.

## Entering the values

`backend/tw3/LICENSED_TABLES_SOP.md` is the procedure. Summary:

1. Enter RUS and carpal points into `letters_tables.json` under
   `rus_stage_to_score` / `carpal_stage_to_score`, and the score→age anchors
   under `rus_score_to_age.twiii` / `carpal_score_to_age.twiii`.
2. Enter `pct_adult_height` (percentages, by **bone age**) to enable adult-height
   prediction. If the licensed copy also gives TW3's **regression** equations for
   adult height, prefer those — they are more accurate than the percentage form —
   and record which was used.
3. Fill `provenance`: book title, edition, ISBN, licensed owner, pages,
   who entered, who verified, date. **Scoring stays off until all are present** —
   licensed values must never drive results without a documented, legally-owned
   source.
4. Enter at least 3 of the clinic's own historically reported films under
   `reference_cases`. `validate_curve()` clears the provisional flag only when
   the entered tables reproduce those films within tolerance — activation is on
   local evidence, not on the transcription being declared finished.
5. Two people transcribe independently. `verify_transcription.py` compares them.

## Four gates, all already enforced

`letters_status()` reports each: **values entered · reference films reproduce ·
provenance documented · checksum locked.** Scoring turns on only when all four
pass, and a checksum mismatch disables scoring rather than 500-ing the app.

## What the book does *not* solve

It does not make TW3 valid for Indian children by itself. Published data
(Indian J Endocrinol Metab 2021, 851 children) show TW3 is best of three methods
overall but **worst in pubertal boys**. That is what the local validation cohort
is for — see `backend/ai/validation/carve_local_cohort.py`.

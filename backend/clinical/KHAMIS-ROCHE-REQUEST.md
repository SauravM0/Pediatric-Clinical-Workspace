# Entering the Khamis-Roche coefficients (M5.3)

**Status: not entered.** The loader, the shape gate and the ingestion tool are
built and tested. What is missing is four numbers per sex per half-year of age,
read from a published paper.

> Khamis HJ, Roche AF. **Predicting adult stature without using skeletal age:
> the Khamis-Roche method.** *Pediatrics* 1994;94(4):504-7.
> (See also the 1995 erratum, which corrects part of the published table.)

## Why bother, when the product already predicts adult height twice

Because the three answer different questions, and this is the only one that
needs no radiograph:

| | Needs | Answers |
|---|---|---|
| Mid-parental target | both parents' heights | where genetics point |
| **Khamis-Roche** | **height, weight, parents** | where this child is heading, **no X-ray** |
| TW3 % of adult height | a hand radiograph + licensed tables | where this child is heading, using actual skeletal maturity |

`prediction.adult_height_summary` returns all three, separately labelled. The
TW3 method is the most informative when a film exists; Khamis-Roche is the one
available at an ordinary clinic visit.

## The model

    adult height (cm) = intercept
                      + b_height    * current height (cm)
                      + b_weight    * current weight (kg)
                      + b_midparent * mid-parental height (cm)

Coefficients are published **per sex and per age**, validated over
**4.0–17.5 years**. Outside that range prediction is refused rather than
extrapolated (`KR_MIN_AGE_YEARS` / `KR_MAX_AGE_YEARS`).

**Check the units before entering anything.** The paper's tables are published
in imperial in some printings. A coefficient set entered in inches produces
confident, wrong, plausible-looking heights — which is exactly what the shape
gate below is for.

## Entering

Transcribe to CSV — one row per (sex, age):

```
sex,age,intercept,height,weight,midparent
boys,4.0,...,...,...,...
boys,4.5,...,...,...,...
```

Then:

```bash
python -m backend.clinical.ingest_khamis_roche coefficients.csv --compare second_transcription.csv
```

Report-only, and `--compare` diffs two independent transcriptions cell by cell.
As with the licensed TW3 percentages, there is no second published copy to
reconcile against — another human reading it is the only transcription check
available. When it passes:

```bash
python -m backend.clinical.ingest_khamis_roche coefficients.csv --install --entered-by "Dr A" --verified-by "Dr B" --source "Khamis & Roche 1994, Table 2"
```

The paper publishes one table per sex, so a single-sex file is normal:

```bash
python -m backend.clinical.ingest_khamis_roche boys.csv  --sex boys  --install
python -m backend.clinical.ingest_khamis_roche girls.csv --sex girls --install --merge
```

`--merge` keeps the already-installed sex. Prediction works for whichever sex is
entered and refuses the other with its own message — a half-entered table is a
normal intermediate state, not a fault.

`--status` prints whether prediction is live and, if not, exactly why.

## What the gate checks, and what it cannot

These are **regression coefficients**, not a distribution. The other four
ingestion tools in this project install L,M,S triplets or percentage tables,
where a wrong value is wrong at one age. These compose, so one transposed
column is confidently wrong at every age at once — and the result still looks
like a height.

So the gate is three things:

1. **Range.** Each coefficient inside structural bounds — wide enough for any
   real row, narrow enough to catch a dropped sign or an imperial table.
2. **Composition.** Each row applied to a reference child must yield a possible
   adult height. Coefficients can each be in range and still not compose.
3. **Dominance.** `b_midparent` must be smaller than `b_height`. The child's own
   stature is the dominant predictor in this model, so a row where the parents'
   outweighs it is almost certainly transposed.

Check 3 exists because check 2 is not sufficient, and that was measured rather
than assumed: swapping the height and mid-parent columns in a plausible table
leaves **every coefficient inside its bounds** and still predicts 191 cm — a
perfectly possible adult height. Composition alone accepted it.

What the gate cannot do is tell a correctly-shaped wrong number from the right
one. There is no second copy to reproduce and no incumbent to match, unlike
M1.4's WHO tables. That is what `--compare` and the recorded `entered_by` /
`verified_by` are for.

## Nothing is bundled

`khamis_roche_coefficients.json` is deliberately absent and a test asserts it is
never committed. These are published values a clinic enters from the paper, with
its own record of who entered and who checked them.

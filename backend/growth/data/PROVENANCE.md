# IAP 2015 growth CSV provenance & source verification (audit GC-1)

These six CSVs are the numeric backbone of the growth charts. They were
**transcribed from the published IAP 2015 (Khadilkar et al.) percentile tables**
by the application author. They are *not* an official machine-readable release —
so they must be (a) locked against silent change and (b) independently verified
cell-by-cell against the paper. This directory now enforces both.

## Files

| CSV | Measure | Columns | Source |
|-----|---------|---------|--------|
| `boy_height_cm_IAP_5_18.csv` / `girl_height_cm_IAP_5_18.csv` | Height (cm), 5–18y, 0.5y steps | p3 p10 p25 p50 p75 p90 p97 | Khadilkar V, et al. *Revised IAP Growth Charts for Height, Weight and BMI for 5- to 18-year-old Indian Children.* Indian Pediatr 2015;52(1):47-55 |
| `boy_weight_kg_IAP_5_18.csv` / `girl_weight_kg_IAP_5_18.csv` | Weight (kg), 5–18y, 0.5y steps | p3 p10 p25 p50 p75 p90 p97 | Indian Pediatr 2015;52(1):47-55 |
| `boy_bmi_IAP_5_18.csv` / `girl_bmi_IAP_5_18.csv` | BMI (kg/m²), 5–18y, 0.5y steps | p3 p5 p10 p25 p50 + adult-equivalent 23/27 cutoffs | Khadilkar VV & Khadilkar AV, Indian J Endocrinol Metab 2015;19(4):470-6 |

WHO 2006/2007 values (<5y and the >5y reference outside IAP coverage) come from
the `rcpchgrowth` package (version-pinned — see `requirements.txt`), not these CSVs.

## Guarantee 1 — drift lock (active)

`checksums.json` pins the *numeric content* of every CSV (SHA-256 over the parsed
numbers, so formatting/line-ending changes don't false-alarm, but any changed
value does). `tests/growth/test_iap_source.py::test_csv_checksums_match_manifest`
fails if any value changes without a reviewed manifest regenerate
(`python -m backend.growth.data_integrity`).

## Guarantee 2 — source verification against the paper (incremental)

The existing growth QA proves the *engine reproduces the CSVs* — it does **not**
prove the CSVs match the **paper**. That is the audit's top GC-1 gap.

`iap_2015_published_reference.json` is where a human verifier enters the
authoritative published values **read directly from the paper** (an independent
second source — never copied from the CSVs). Every entered cell is enforced
against the CSV by the source test, and the file cannot be marked `VERIFIED`
until all 1134 numeric cells are covered.

### How to complete verification (the pending human step)

1. Two people independently read the paper's tables.
2. Enter values into `iap_2015_published_reference.json` under
   `values[<csv filename>][<age>][<column>]`.
3. Run `pytest tests/growth/test_iap_source.py` — any mismatch between the paper
   value and the CSV fails loudly (a real transcription error caught).
4. When all cells are entered and green, set `"status": "VERIFIED"` and fill
   `provenance` (who entered, who verified, date).

Until then the CSVs are **transcribed but not independently source-verified** —
the app already labels the reference honestly and keeps every result under
clinician review.

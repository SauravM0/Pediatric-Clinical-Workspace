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

### Finding (2026-08-09): four height/weight columns are reconstructed, not sourced

This raises the priority of the verification step below from "good practice" to
"there is a known defect".

Fitting L,M,S per age against p3/p50/p97 and inverting every column back to the
z it implies gives the same result in all four height/weight CSVs, at all 27
ages, with a standard deviation across ages of ~0.006 in z:

| column | implied centile | implied z | nominal z |
|---|---|---|---|
| p3 | 3.0 | −1.88079 | anchor |
| p10 | 10.5 | −1.2529 | −1.28155 |
| p25 | **26.5** | −0.6270 | −0.67449 |
| p50 | 50.0 | 0.0 | anchor |
| p75 | **73.5** | +0.6273 | +0.67449 |
| p90 | 89.5 | +1.2544 | +1.28155 |
| p97 | 97.0 | +1.88079 | anchor |

The implied z values are the p3–p97 range divided into six equal steps
(±1.88079/3 = ±0.62693, ±1.88079×2/3 = ±1.25386). Reading the interior columns
at those values reproduces them to 0.057–0.095 units; reading them at their
nominal centile z misses by 0.27–0.77. So p10, p25, p75 and p90 appear to have
been **filled in by even z-spacing between p3 and p97** during transcription.
Only p3, p50 and p97 carry independent information.

Controls run before concluding this:

- The same probe applied to WHO — a genuine LMS reference, rounded to the same
  0.1 unit — recovers 25.00, 75.00, 10.00, 90.00 (worst error 0.07 centile).
- BMI is unaffected: its five columns imply 3.0/4.94/10.0/24.97/50.0. It came
  from a different paper and was evidently transcribed differently. So this is
  not "p25 is unreliable", it is these four files.
- An earlier hypothesis that p25/p75 were arithmetic means of their neighbours
  was measured and **rejected** (holds for most height cells, misses weight by
  up to 0.9 kg, and WHO fails it too).

**Clinical effect:** a child on the drawn 25th centile is at the 26.5th; on the
10th, the 10.5th. In value terms 0.27–0.48 cm and 0.30–0.77 kg. Small,
systematic, one-directional, and removed entirely by real L,M,S.

**Cause is inferred, not confirmed at source.** The paper states LMS was used and
that 3rd/10th/25th/50th/75th/90th/97th percentiles were generated, so the
published table should sit at nominal z — which points at reconstruction here
rather than at the publication. Settling it requires the verification below.

Code: `backend/growth/iap_table_consistency.py`. Live at
`GET /api/growth/validate` under `iap_table_consistency`. The M1.1 reproduction
gate and `validation.check_source_reproduction` both exclude these columns from
their verdicts and report them separately, because holding real L,M,S to a
reconstructed column would reject the real values.

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

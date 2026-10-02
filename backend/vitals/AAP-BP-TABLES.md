# Entering the AAP 2017 paediatric blood-pressure tables

**Status: not entered.** The loader, gate, install tool and classification are
built and tested (`aap_bp_reference.py`, `ingest_aap_bp.py`). Until the tables are
installed, a child under 13 gets **no BP category** — only the reason — rather
than an adult label, which is what the workspace used to show.

> Flynn JT, Kaelber DC, Baker-Smith CM, et al. **Clinical Practice Guideline for
> Screening and Management of High Blood Pressure in Children and Adolescents.**
> *Pediatrics* 2017;140(3):e20171904. **Table 4 (boys) and Table 5 (girls).**
> Open access on the AAP site / PubMed Central.

## What to transcribe

For each sex, ages **1–12** (13–17 optional, not used — from 13 the guideline uses
fixed 120/80, 130/80, 140/90 thresholds, already implemented), and each of the
seven **height-percentile columns** (5th, 10th, 25th, 50th, 75th, 90th, 95th):

| Column in the CSV | Row of the published table |
|---|---|
| `height_cm` | the **Height (cm)** row — not the inches row |
| `sbp_50`, `sbp_90`, `sbp_95`, `sbp_95_12` | systolic 50th, 90th, 95th, 95th + 12 mm Hg |
| `dbp_50`, `dbp_90`, `dbp_95`, `dbp_95_12` | diastolic, same four rows |

That is 168 rows. Start from the blank template, which already lists every
(sex, age, height percentile):

```
backend/vitals/data/aap2017_bp_tables.template.csv
```

**Two people transcribe independently**, into two separate copies. Do not let
the second person see the first copy.

## Installing

```bash
# 1. check, and compare the two transcriptions cell by cell
python -m backend.vitals.ingest_aap_bp first.csv --compare second.csv

# 2. when both are clean and identical
python -m backend.vitals.ingest_aap_bp first.csv --compare second.csv --install \
    --entered-by "Dr A" --verified-by "Dr B" \
    --source "Flynn et al. Pediatrics 2017;140(3):e20171904, Tables 4-5"

python -m backend.vitals.ingest_aap_bp --status
```

Install is refused unless: the data passes the gate, the two transcriptions
match exactly, and two **different** people are named. The installed file is
checksum-locked; editing it by hand afterwards switches the table off (it does
not silently start using the edit).

## What the gate checks — and what it cannot

It is the same function the app uses at run time (`table_problems`), and it
rejects, among others:

- a **slipped row** — every "95th + 12" cell must equal its 95th cell + 12, which
  the paper guarantees, so an off-by-one line is caught almost anywhere;
- **inches entered as centimetres**, and heights that do not grow with age;
- **centile rows out of order** (e.g. 90th and 95th swapped), diastolic ≥ systolic;
- any missing age or height column for ages 1–12.

It cannot tell a plausible wrong number from the right one. That is what the
second transcription and the named checker are for.

## How it is used once installed

- The row is the child's **completed years** (7.9 y uses the age-7 row).
- The column is chosen by the child's **height in cm**, interpolated between the
  table's height columns, and clamped to the 5th/95th column outside them — as
  the guideline instructs. It deliberately does **not** convert through the
  child's IAP/WHO centile: the table's columns are **CDC** centiles, a different
  quantity from an Indian child's IAP centile.
- Categories follow AAP 2017 Table 3, systolic and diastolic separately, the
  higher one reported: elevated from the 90th centile (or 120/80, whichever is
  lower), stage 1 from the 95th (or 130/80), stage 2 from the 95th + 12 (or 140/90).
- Under 1 year no category is given — the tables start at 1.
- Every result is labelled a **single reading**; hypertension is diagnosed only on
  repeated measurements (three visits in children).

## Nothing is bundled

The installed `aap2017_bp_tables.json` must not be committed; a test asserts it.

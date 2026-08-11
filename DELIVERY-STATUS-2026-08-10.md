# Delivery Status

**Date:** 10 August 2026
**Covers:** the three planning documents dated 26 July 2026 —
`ENGINEERING-REPORT`, `PRODUCT-IMPROVEMENT-MASTER-PLAN`,
`GROWTH-AND-BONE-AGE-DIAGNOSIS-AND-ROADMAP`
**Purpose:** what was built, what is waiting on data, and where those documents
are now wrong

Those three are dated analyses and are left as written. This is the running
status; where they state something since measured to be false, the correction is
in [Corrections](#corrections-to-the-planning-documents) below.

**Test suite: 739 passed, 32 skipped.** The 32 skips are the data-gated paths —
they activate themselves when their data lands.

---

## 1. Delivered and live

Nothing here needs anything from outside the repository.

| Milestone | What landed | Commit |
|---|---|---|
| **M0** Foundation hardening | append-on-change schema versioning, ORM↔migration drift test, canonical measure registry, fingerprint-keyed cache | `4f504bc` |
| **M1.2** Tail correction | LMS-shaped tails pinned to the drawn P3/P97, reportable-z bound (±5 SD) | `20d2a9d` |
| **M2** Longitudinal record | Encounter/Observation/PubertyAssessment, velocity, AST-enforced domain purity | `45869b2` |
| **M3** Bone-age integrity | curve-domain guard (no clamping an out-of-range score), truthful method labelling | `969a4ec` |
| **M4** Inference platform | model registry, preprocessing versioning, conformal-calibration binding | `757ada9` |
| **M4.3** digiBONE integration | model selection via `PCW_BONEAGE_MODEL`, labels derived from the active spec, ONNX converter with parity gate | `5a42c00` |
| **M5** Reasoning engine | 12 rules with `inputs_used`/`source`/`confidence`, referral triage | `2b3bb11` |
| **M6** Presentation re-platform | esbuild bundle (Babel retired), all 8 panels + shell + input column extracted, context slices, state grouping | `4eb1aa8` → `a2dab7d` |
| Security phase | scrypt auth, session cookies, RBAC, encryption at rest, DICOM de-identification, DPDP rights | `ca1973f` |
| Local cohort evaluation | `local_cohort_report` — subgroup MAE against the dual-read consensus, with the inter-reader floor beside it | `168ef51`, `79626e5` |

## 2. Built, waiting on data

Each has a loader, an activation gate, an ingestion CLI and tests that skip
until the data exists. **None of them can be completed by writing more code.**

| Asset | How to get it | Effort | Tool |
|---|---|---|---|
| **IAP 2015 L,M,S** | email Khadilkar / HCJMRI — the 2015 paper says the values and LMS macro are available from the authors | an email | `ingest_iap_lms` |
| **WHO 2006/2007 L,M,S** | download from WHO | an afternoon | `ingest_who_lms` |
| **Indian height-velocity centiles** | email Khadilkar (Indian Pediatr 2019;56:23-8) | an email | `ingest_velocity_reference` |
| **TW3 % of adult height** | buy the TW3 book (3rd ed., 2001) | a purchase | `ingest_adult_height` |
| **Khamis-Roche coefficients** | transcribe from Pediatrics 1994;94:504-7 | an hour, twice | `ingest_khamis_roche` |
| **Local dual-read cohort** | 200 films, ≥15 per sex×puberty stratum, two independent reads each | months of clinic work | `carve_local_cohort` |

Ranked by value per unit of effort, the order is: **IAP LMS → WHO LMS →
velocity → Khamis-Roche → TW3 book → cohort.**

Every gate refuses rather than approximates, and every one is
negative-controlled — the tests confirm each gate *fails* when fed a wrong file,
not merely that it passes when fed a right one.

### Two of these gates are stronger than the plans assumed

- **WHO (M1.4)** is gated on **equivalence with the incumbent**, not on
  reproducing a published table: `rcpchgrowth` is still installed, so it is a
  perfect oracle for its own behaviour. Removing the dependency is therefore
  deliberately a *second* step — drop it first and the oracle is gone.
- **Khamis-Roche (M5.3)** is a regression, not a distribution, so the gate also
  checks that each row **composes** into a possible adult height and that the
  child's own height coefficient outweighs the parents'.

## 3. Not attempted

| | Why |
|---|---|
| Removing `rcpchgrowth` from `requirements.txt` | The gate needs it as the oracle. Do it after the WHO tables pass. |
| GC-1 dual-person verification of the IAP CSVs | A human reading task, and now a known-defect fix rather than routine QA — see correction 6. |
| digiBONE weights, conversion, re-calibration | Needs the weights and a machine with torch. |

---

## Corrections to the planning documents

Each of these was measured after the documents were written.

**1. TW3 RUS maturity ages.** The diagnosis quotes 18.2 y (boys) / 16.5 y
(girls). Those are **TW2**. TW3 RUS reaches maturity at **16.5 y / 15.0 y**.
Corrected in the code and docstrings.

**2. The weight-tail defect is bias, not truncation.** The reports describe the
tail as truncated. It is not: the engine extrapolates unbounded, and the defect
is **compression toward the mean** — a weight at a true −3.0 SD scored −2.64.
The direction matters, because WHO's severe-underweight threshold is −3 SD, so
genuinely affected children were reported just above it.

**3. Preprocessing v2 is worse, not better.** The engineering report estimates a
1–2 month MAE gain from CLAHE + segmentation. Measured on the 200-image locked
test: **MAE 8.92 → 33.34 months, 3.7× worse.** `CURRENT_PREPROCESSING` stays at
v1 with a test pinning it. The estimate was mine and it was wrong.

**4. digiBONE's published figures.** The reports say 4.75 / 4.93 months. The
paper reports **4.7 / 4.9** for segmental GP and **5.7 / 5.9** full-hand — the
full-hand pair was omitted entirely.

**5. "8.99 mo → ~4.8 mo" is not a valid comparison.** Both the plan and the
diagnosis put these side by side. 8.99 is this product's model on a frozen RSNA
split; 4.7/4.9 is digiBONE's own number on its own Indian validation set.
Different models, different test sets, different populations. Producing the
comparable figure is what step 4 of `backend/ai/DIGIBONE.md` exists for, and the
release gate refuses to treat a cross-method adoption as a like-for-like
improvement.

**6. NEW — four of seven columns in the IAP height/weight CSVs are not published
values.** The diagnosis identifies the missing L,M,S as the growth-chart problem.
It is not the only one. Fitting L,M,S per age to p3/p50/p97 and inverting every
column gives the same result in all four files, at all 27 ages:

| column | implied centile |
|---|---|
| p10 | 10.5 |
| **p25** | **26.5** |
| **p75** | **73.5** |
| p90 | 89.5 |

Those implied z values are the p3–p97 range divided into six equal steps. Reading
the interior columns there reproduces them to rounding; reading them at their
nominal centile z misses by 0.27–0.77 units. So **p10, p25, p75 and p90 were
filled in by interpolation during transcription** — only p3, p50 and p97 carry
independent information. The line drawn as the 25th centile is the 26.5th.

Controls: the same probe on WHO recovers 25.00/75.00/10.00/90.00 (worst error
0.07 centile); BMI, transcribed from a different paper, is unaffected. An earlier
hypothesis of mine — that p25/p75 were arithmetic means of their neighbours — was
measured and **rejected**.

Consequence: 0.27–0.48 cm and 0.30–0.77 kg of systematic, one-directional error,
and the M1.1 gate must exclude those columns or it would reject the authors' real
parameters for someone else's interpolation. Code:
`backend/growth/iap_table_consistency.py`. This raises GC-1 verification from
good practice to fixing a known defect.

**7. NEW — `rcpchgrowth` ships two WHO layouts that disagree.** `who.py` reads
`who_infants`/`who_children`/`who_2007_children`; the per-measure
`who_*_five_*` files are a different layout. They differ at one point — girls'
height at exactly 5.000 y, 0.15 cm at the median — inside the 4.95–5.2 handoff
window this product already bridges, so no chart is affected. It does mean
"which WHO tables" is a real question to settle from WHO's own files.

**8. A predicted frontend defect that was not real.** The audit predicted that
`zForValueFromCentileStats` carried the same tail bug as the backend. Measured
error for its only caller: **0.000 SD.** It was not rewritten; a scope limit was
documented instead.

---

## What the numbers still say

The honest headline has not changed, and should not be softened:

- The AI screening model is **below its own release gate** (locked-test MAE 8.99
  months against a 6.0-month threshold) and the product says so in
  `INTENDED-USE.md`.
- The bone age reported today is **not Tanner TW3**: its points come from a
  conference paper's Table 1 and its score→age curve was digitised off a figure.
  The UI labels it provisional. Only the book fixes that.
- Growth-chart accuracy is limited by reference data, not by the engine — and by
  correction 6, more than the original diagnosis said.

A product that publishes those three facts is more credible than one that hides
them, which is why each is surfaced in the app rather than only in a document.

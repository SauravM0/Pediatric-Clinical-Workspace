# Pre-Registered Bone-Age Validation Protocol (Plan 5 WI-8)

**Protocol version:** validation-protocol-1.0 · **Registered:** 2026-07-13
**Status:** acceptance criteria **locked**; the external run is **data-gated** (no Indian cohort yet).

Acceptance criteria are fixed **before** any results are seen, so a claim cannot be
retrofitted to whatever number came out. A change to this protocol is a versioned,
logged event — not an inline tweak. Derived from
`bone_age_product_starter_pack/validation_protocol.md` and the master audit §3.4/§6/§7.

> **A passing internal test is NOT a clinical accuracy claim.** External Indian
> performance (below) is required before any such claim; the external-cohort gate
> stays red until a real run exists.

---

## 1. Reference standard
- Left PA hand/wrist radiograph per case.
- ≥ 2 trained readers assess each image independently; a third adjudicates disagreements.
- Final reference age stored in months + method. For per-bone staging, readers use a legally licensed TW manual.
- Chronological age is a comparison variable, never the ground truth.

## 2. Data splitting (enforced by `leak_guard.py`)
- Split by **patient**, never by image; all of one child's films in one split.
- Separate train / tune / internal-test / **external-test** patients.
- A locked test set is frozen in `locked_test.json` and is off-limits to training, tuning, feedback, and conformal calibration (the guard refuses any overlap).
- Report by sex, age band, site, scanner, and major diagnosis group.
- Age bands: 0–5, >5–8, >8–12, >12–15, >15–18 years.

## 3. Metrics (computed by `evaluate.py`)
- **Whole-hand age:** MAE, median AE, RMSE, signed bias + 95% CI, Bland–Altman limits, % within ±3/6/9/12 mo, conformal coverage vs target, abstention rate.
- **Per-bone staging:** exact-stage accuracy, within-one, quadratic-weighted kappa, per-bone confusion matrix, ordinal distance, model–reader agreement, confidence calibration. Carpals evaluated and gated **separately**.

## 4. Acceptance gates (locked; encoded in `gates.json`, checked by `gates.py`)
| Gate | Threshold |
|---|---|
| Whole-hand MAE (locked test) | ≤ 6 months |
| Any sex/age/site subgroup MAE | ≤ 9 months |
| % within ±12 months | ≥ 90% |
| Overall per-bone staging weighted κ | ≥ 0.80 |
| Any individual bone weighted κ | ≥ 0.70 (else mandatory manual review) |
| Report release when image-quality gate failed | never (zero) |
| Clinician review during pilot | 100% |

## 5. Release rule (enforced by `release_gate.py`)
A candidate ships only if, on the locked test set, it **beats the incumbent** by the
pre-registered margin **and** shows **no subgroup regression** **and** is **calibrated**
**and** passes **every** gate above **and** is **signed off by a human**. Otherwise it
stays a candidate; the shipped model is untouched.

## 6. Local clinical validation (external run — data-gated)
Validate on an Indian cohort spanning normal variants, GH deficiency, constitutional
delay, precocious puberty, hypothyroidism, Turner syndrome, chronic disease, and
treated/untreated follow-up. A pilot may begin at ≥ 200 independently read films; a
larger external cohort is preferred for subgroup analysis. Do not claim accuracy for
diagnoses or age ranges with inadequate sample size.

### How it runs

```bash
python -m backend.ai.validation.carve_local_cohort            # survey: what is still missing
python -m backend.ai.validation.carve_local_cohort --freeze   # one-way
python -m backend.ai.validation.local_cohort_report           # the number
```

The carve writes **its own** registry (`locked_test_local_indian_bone_age_cohort.json`),
not the shared `locked_test.json`. Both frozen sets answer different questions and
must survive alongside each other; `leak_guard.save_registry` now refuses to write
one dataset's registry over another's.

`local_cohort_report` is the counterpart to `baseline_report`. The RSNA report reads
label files from a dataset directory; this cohort lives in the database, where films
are `Radiograph` rows and the label is the consensus of ≥ 2 independent
`TW3Assessment` reads. It leak-guards first, runs the **real** inference path, and
breaks results down by the sex × pubertal-status strata the carve enforces —
reporting `boys:pubertal` separately because published Indian data show TW3 is worst
of three methods there, and saying so explicitly when that stratum is absent.

### Interpreting the number: the inter-reader floor

Bone age has **no ground truth**. The reference standard is itself an expert reading,
and two radiologists routinely differ by 0.5–1.0 year on the same film. A model MAE
quoted alone therefore overstates what "good" means: if the readers disagree by 6
months, a model at 5 months is at the noise floor of the measurement, not superior to
the readers.

So the report prints the inter-reader spread beside the model error and will state
that a model inside that band is *within the range where the reference is itself
uncertain* — never that it beats the readers. There is nothing to beat them against.

The consensus label is a **true median**. `sorted(ages)[len//2]` returns the upper of
two values, and two readers is both the mandated minimum and the expected case — so
that rule made every dual-read label the higher read, biasing the reference standard
up by half the reader disagreement and charging that bias to the model as error.

### Method boundary

The screening model is Greulich–Pyle; the stored consensus carries whatever method the
readers used. Films whose consensus is on a different scale from the model's are
**excluded and counted**, never silently compared — a GP estimate scored against a TW3
consensus is a category error, not a measurement.

## 7. Pre-registered decisions to finalise before the run
- Beat-incumbent margin (e.g. ≥ 0.3 mo MAE and no subgroup regression).
- Locked-test source (carve an internal RSNA test now; keep the external Indian test separate).
- Site(s), reader panel, adjudication procedure, and consent for the external run.
- Which diagnosis subgroups are realistically obtainable for stratified reporting.

*This protocol governs how accuracy is judged. The infrastructure and criteria are
delivered; the external Indian run executes when the cohort exists.*

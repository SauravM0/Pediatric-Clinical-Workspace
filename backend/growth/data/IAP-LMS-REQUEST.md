# Requesting the IAP 2015 L, M, S values

**Status: not obtained.** This is the highest-leverage outstanding item in the
project and it is an email, not an engineering task. The code to use these values
is already written, tested and self-activating (`iap_lms_reference.py`); it turns
itself on the moment a valid file lands here.

---

## Why this is worth an email

The published IAP 2015 paper gives percentile *tables*, not the L,M,S parameters
behind them. Without the parameters the engine has to fit L and S to 6 published
points per age — 2 free parameters against 6 targets, which is overdetermined, so
it can only ever land close. Everything below is downstream of that one gap:

| Consequence today | Removed by real L,M,S |
|---|---|
| Residual tail error ~0.07 SD (was 0.81 before M1.2) | Yes — goes to zero |
| Three parallel value paths (LMS fit, exact-table PCHIP, display-anchor inversion) | Collapse into one Cole transform |
| `_EXACT_TABLE_GUARD` needed to stop them colliding at the WHO/IAP seam | Unnecessary |
| BMI P75/P90/P97 extrapolated from a lower-half-only table | Directly computable |
| Height/weight L,S splines fitted per age row and unsmoothed | Published, smooth by construction |

## The values exist, and the paper says they are available on request

`iap_reference.py` currently says the triplets "were never published". That is
half right and the actionable half is different: they were never *publicly
released*, but the authors hold them and offer them.

The 2015 paper itself states that Cole's LMS method was used and that the
**"Lambda, mu, and sigma values and LMS Macro for Microsoft Excel"** are
available from the authors. That is close to an open invitation, and it is the
single sentence to quote when writing.

Corroborating that they are in active use:

> Khadilkar V, et al. **Extended growth charts for Indian children.**
> *J Pediatr Endocrinol Metab* 2021. doi: 10.1515/jpem-2020-0573

states it used "**LMS values from IAP 2015 growth charts (5–18 years)** and WHO
2006 MGRS charts (<5 years)" to construct the −2.25, −2.5 and −3 SD lines. So the
request is for something the authors have already worked from — not for
unpublished research.

## A second reason to ask, found while building the ingestion

Four of the seven columns in the height and weight CSVs here are **not published
values**. Fitting L,M,S per age to p3/p50/p97 and inverting every column shows
p10, p25, p75 and p90 sitting at evenly spaced z between p3 and p97
(±1.88079/3 and ±1.88079×2/3) rather than at their nominal centile z. Reading
them that way reproduces them to rounding; reading them at their labels misses
by 0.27–0.77 units. The same probe recovers WHO's centiles to 0.07 centile, so
this is about these files.

In practice the line drawn as the 25th centile is the 26.5th, and the 10th is
the 10.5th. Real L,M,S do not merely improve the tails — they replace four
interpolated columns with the actual distribution. See
`backend/growth/iap_table_consistency.py` and `PROVENANCE.md`.

## Who to ask

- **Dr Vaman Khadilkar / Dr Anuradha Khadilkar**, Hirabai Cowasji Jehangir Medical Research Institute (HCJMRI), Pune — corresponding authors of both the 2015 charts and the 2021 extended charts.
- **IAP Growth Charts Committee**, via the Indian Academy of Pediatrics.

Worth noting in the same message: this is the same institute behind **digiBONE**,
which is the other external asset this project wants (see
`backend/ai/DIGIBONE.md`). One conversation can cover both.

## What to ask for, precisely

> The L, M and S parameters underlying the IAP 2015 revised growth charts, for
> **height, weight and BMI**, **boys and girls**, ages **5.0–18.0 years at
> 0.5-year steps** — i.e. the values referenced in Khadilkar et al., *Extended
> growth charts for Indian children*, JPEM 2021.

Any format is fine (CSV, Excel, PDF table). Ask for **at least 4 decimal places
on L and S**; rounding those to 2 places visibly changes the tails.

State the use plainly: a non-commercial clinician-supervised decision-support
tool for Indian paediatric practice, with the IAP charts cited as the reference.

---

## Installing the values

Do **not** hand-edit the CSV. It is 162 rows of numbers that are meaningless to
the eye — an L of 0.87 and an L of 0.78 look equally plausible and only one of
them is what a child gets scored against. Use the ingestion tool, which
normalises the authors' format, reports coverage, runs the real gate and refuses
to install a file that fails it.

Save whatever arrives (Excel, CSV) as CSV, then:

```bash
python -m backend.growth.ingest_iap_lms received_from_authors.csv
```

That reports only. It accepts any recognisable header spelling — `Gender`,
`Parameter`, `Age (years)`, `lambda`/`mu`/`sigma` — and tells you which
(sex, measure, age) cells are missing before it judges any numbers. When the
gate passes:

```bash
python -m backend.growth.ingest_iap_lms received_from_authors.csv --install --supplied-by "Dr V Khadilkar, HCJMRI" --received 2026-08-09
```

Provenance is written to `iap_2015_lms_provenance.json` automatically. Also add
a line to `PROVENANCE.md` describing the form it arrived in.

Then run the suite — every skipped test in `tests/growth/test_iap_lms.py`
activates once the file exists:

```bash
python -m pytest tests/growth/test_iap_lms.py tests/growth/test_iap_lms_ingestion.py -v
```

### What "installed" now means

Installing takes effect. `iap_reference.iap_value_at_z` and `iap_z_for_value`
delegate to the LMS path whenever `lms_available()` is true, so blend,
curve_builder, velocity, the clinical rules and the API all switch together —
value and inverse in the same step, so a plotted point is never scored on a
different model from the curve it sits on.

**This was not true before M1.1's ingestion step.** The loader, the gate and the
status endpoint all existed, and nothing called them: a valid file could land,
pass, report itself active on `/api/growth/validate`, and change no number
anywhere. `test_install_makes_the_lms_path_actually_take_effect` exists to stop
that regressing.

### What the gate can and cannot tell you

It judges against the columns the CSVs actually source — p3/p50/p97 for height
and weight, all five for BMI (see the section above). That is 162 checks per
measure and it catches a wrong number: a 2% error in a single median fails it.

It cannot distinguish the authors' real parameters from a competent refit of
those same three columns, because three judged columns against three free
parameters is exactly determined. Smoothness-in-age was tried as a discriminator
and abandoned — WHO's own published L for height is nearly constant, so any
spread-normalised roughness measure calls it rougher than a refit. So
**provenance carries that weight**: record who sent the file. The gate proves
the numbers are self-consistent; only the record proves whose they are.

## Then, and only then

Once the gate is green on real data, the legacy machinery can be removed:
`_z_from_display_anchors`, the `table_fns` exact-table path, `_EXACT_TABLE_GUARD`,
and the `smooth_ls` branch. **Do not remove them before that.** They exist to
compensate for the missing parameters, and `_EXACT_TABLE_GUARD` in particular is
load-bearing for the WHO/IAP seam — `blend._quintic_bridge` probes derivatives
right at that boundary, and removing it prematurely re-introduces centile-ordering
and slope-continuity failures that `validation.run_full_validation()` caught the
last time.

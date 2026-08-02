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

## The values exist and have been used

`iap_reference.py` currently says the triplets "were never published". That is
half right and the actionable half is different: they were never *publicly
released*, but the authors hold them and have used them.

> Khadilkar V, et al. **Extended growth charts for Indian children.**
> *J Pediatr Endocrinol Metab* 2021. doi: 10.1515/jpem-2020-0573

states it used "**LMS values from IAP 2015 growth charts (5–18 years)** and WHO
2006 MGRS charts (<5 years)" to construct the −2.25, −2.5 and −3 SD lines. So the
request is for something the authors have already worked from — not for
unpublished research.

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

1. Put them in `backend/growth/data/iap_2015_lms.csv` in the schema of
   `iap_2015_lms.template.csv` — one row per (sex, measure, age).
2. Run the gate:

```bash
python -m pytest tests/growth/test_iap_lms.py -v
```

   Every test is written and currently **skips** with "no LMS data". They run
   automatically once the file exists. Two must pass before the path activates:
   exact reproduction of all published percentile cells, and dense-grid
   agreement with the current engine.

3. Record provenance in `PROVENANCE.md`: who supplied the values, when, and in
   what form.
4. Nothing else to switch on. `lms_available()` gates on the reproduction check
   itself, so a bad transcription cannot quietly become the reference — and
   `GET /api/growth/validate` reports exactly why the path is or is not live.

## Then, and only then

Once the gate is green on real data, the legacy machinery can be removed:
`_z_from_display_anchors`, the `table_fns` exact-table path, `_EXACT_TABLE_GUARD`,
and the `smooth_ls` branch. **Do not remove them before that.** They exist to
compensate for the missing parameters, and `_EXACT_TABLE_GUARD` in particular is
load-bearing for the WHO/IAP seam — `blend._quintic_bridge` probes derivatives
right at that boundary, and removing it prematurely re-introduces centile-ordering
and slope-continuity failures that `validation.run_full_validation()` caught the
last time.

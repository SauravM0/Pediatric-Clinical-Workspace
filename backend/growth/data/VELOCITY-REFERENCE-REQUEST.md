# Requesting the Indian height-velocity reference

**Status: not obtained.** The engineering is complete and self-activating
(`velocity_reference.py`); only the numbers are missing.

> Khadilkar V, Khadilkar A, Arya A, et al. **Height Velocity Percentiles in
> Indian Children Aged 5–17 Years.** *Indian Pediatr* 2019;56(1):23-8.
> PMID 30806356 · https://www.indianpediatrics.net/jan2019/23.pdf

## Why this one matters

Height velocity is **the most sensitive single indicator of growth pathology**.
A child can sit on the 25th centile for years and be entirely well; the same
child crossing downward at 3 cm/year is not. M2 already computes the rate from
stored measurements — there is simply nothing to compare it against.

The concrete cost right now: M5's `LOW_HEIGHT_VELOCITY` rule uses a **4 cm/year
rule of thumb** at `confidence: low`, standing in for the real test, which is
*velocity below the 25th centile for age*. A rule of thumb cannot distinguish a
7-year-old growing at 4.5 cm/yr (low, worth attention) from a 13-year-old
growing at 4.5 cm/yr (very low for mid-puberty, urgent).

## Why this paper specifically

- **Indian children**, 2,949 of them (Pune and Delhi), 13,214 velocity measurements.
- **LMS-based**, so exact SDS is possible rather than an interpolated ladder.
- **Same authors and institute** as the IAP 2015 charts this product already
  uses and the L,M,S request in `IAP-LMS-REQUEST.md` — and as digiBONE. All
  three asks can go in one message.

## What to ask for

> The **L, M and S values** underlying the height-velocity percentiles in
> Khadilkar et al., *Height Velocity Percentiles in Indian Children Aged 5–17
> Years* (Indian Pediatr 2019;56:23-8) — boys and girls, across the published
> age range.

Also worth confirming, because it changes how the reference may be applied:

1. **The measurement interval** the velocities were computed over (the paper
   describes annual measurements — please confirm).
2. Whether velocity is indexed by the **midpoint** of the interval or by the
   age at the second measurement. This code assumes midpoint; if the reference
   uses the endpoint, `velocity_reference.velocity_sds` must be adjusted, and
   near the pubertal peak that half-year shift is the difference between normal
   and abnormal.

If only the percentile table is available (P3–P97 by age) rather than L,M,S,
say so — it is usable, but the tails become an interpolated ladder with the
same limitation M1.2 had to correct on the distance charts.

## Installing it

1. Put the values in `backend/growth/data/indian_height_velocity.csv` following
   `indian_height_velocity.template.csv` — one row per (sex, age).
2. Run the gate:

```bash
python -m pytest tests/growth/test_velocity_reference.py -v
```

3. Record provenance in `PROVENANCE.md`.

Nothing to switch on. The path activates only when the installed table **peaks
where the paper says it does** — boys 6.8 cm/yr at 13.5y, girls 6.6 at 10.5y.
That check exists because a velocity reference has a distinctive shape (a
mid-childhood trough, then a pubertal peak), so a table that does not peak there
is not this reference — most likely the sex columns are swapped, or distance
values were entered in place of velocities.

## What changes on the day it lands

- Velocity SDS appears on `/api/patients/{id}/velocity/height`.
- M5's `LOW_HEIGHT_VELOCITY` switches from the 4 cm/yr floor to a real centile
  and stops reporting at `confidence: low`.
- A velocity chart becomes drawable (`velocity_at_centile`).

## One limitation that will remain

SDS is only computed for intervals of **0.75–1.25 years**. Velocity centiles are
interval-specific: annualising a shorter gap divides measurement error by a
smaller Δt, so the spread widens and an ordinary child scores as extreme. Outside
that band the rate is still reported — only the centile is withheld.

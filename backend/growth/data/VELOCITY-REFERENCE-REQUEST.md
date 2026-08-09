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

Use the ingestion tool rather than editing the CSV. Save whatever arrives as
CSV, then:

```bash
python -m backend.growth.ingest_velocity_reference received.csv
```

That reports only. It absorbs the supplier's header spelling (`Gender`,
`Age (years)`, `lambda`/`mu`/`sigma`), skips `#` comment lines, and reports
coverage, structure and curve shape **before** judging any number. When it
passes:

```bash
python -m backend.growth.ingest_velocity_reference received.csv --install --supplied-by "Dr V Khadilkar, HCJMRI" --received 2026-08-09
```

Provenance is written to `indian_height_velocity_provenance.json`. Add a line to
`PROVENANCE.md` too, describing the form it arrived in. Then:

```bash
python -m pytest tests/growth/test_velocity_reference.py tests/growth/test_velocity_ingestion.py -v
```

### What the checks actually are

Three, in order, and a file must clear all of them:

1. **Coverage** — enough ages, and the range must *span the pubertal peak*. A
   count alone looks healthy for a table that stops at 12y, and the peak is the
   part the rule depends on.
2. **Structure** — S in (0,1), plausible L, and a median velocity under
   15 cm/year. There is deliberately **no lower bound** beyond positive: by
   17.5y the median genuinely approaches zero because growth stops, and an
   early draft of this tool rejected a good table for exactly that.
3. **Shape and peak** — the table must peak where the paper reports (boys
   6.8 cm/yr at 13.5y, girls 6.6 at 10.5y) *and* fall away after the peak. The
   peak alone is not enough — a flat table peaks at the right value everywhere.
   Together these catch the failures that actually happen: swapped sex columns,
   an off-by-one age column, or distance values entered as velocities.

This is a **shape** gate, not a reproduction gate. Unlike M1.1 there is no
published table in the repo to regenerate, so it cannot certify precision — it
can only reject a file that is not this reference. Record who supplied it;
provenance carries what the gate cannot.

## What changes on the day it lands

- Velocity SDS appears on `/api/patients/{id}/velocity/height`.
- M5's `LOW_HEIGHT_VELOCITY` switches from the 4 cm/yr floor to a real centile
  and stops reporting at `confidence: low`.
- A velocity chart becomes drawable (`velocity_at_centile`).

The consumption path already exists and is exercised —
`growth_service.velocities_for` scores height intervals and the rule reads the
result — so installing the file genuinely changes the output. (That was worth
checking: the same claim was false for M1.1, where the reference was wired to a
status endpoint and nothing else.)

### One defect this milestone made reachable, now fixed

Velocity SDS is per-interval, and not every interval can be scored: a 4-month
follow-up yields a rate but no centile. The snapshot carried a single
`latest_velocity_sds` — the most recent **scorable** interval — while the rule
reported on the most recent interval *period*. Whenever those differed, the
rule stated one interval's rate with another interval's centile, and chose
urgent-vs-attention from the stale number. Dormant while the field is always
None; live the moment this file is installed. Each interval now carries its own
SDS. See `test_an_unscorable_recent_interval_is_not_labelled_with_an_older_sds`.

## One limitation that will remain

SDS is only computed for intervals of **0.75–1.25 years**. Velocity centiles are
interval-specific: annualising a shorter gap divides measurement error by a
smaller Δt, so the spread widens and an ordinary child scores as extreme. Outside
that band the rate is still reported — only the centile is withheld.

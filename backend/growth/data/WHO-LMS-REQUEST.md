# Obtaining WHO's L, M, S tables (M1.4)

**Status: engineering complete, data not installed.** The loader, the strangler
seam and the equivalence gate are built and tested. What is missing is WHO's own
published tables — and unlike the other outstanding assets, these are freely
downloadable today. This is an afternoon, not an email or a purchase.

## Why remove a dependency that works

`rcpchgrowth` supplies the WHO reference this product charts and scores against.
Three reasons to stop depending on it:

1. **Licence.** It is **AGPL-3.0**. Serving this app over a network triggers
   AGPL §13's source-offer obligation for the whole combined work. That is a
   decision a clinic should take deliberately, not inherit from an import.
2. **Weight.** ~9 MB of data tables for UK-WHO, CDC, Trisomy-21 and Turner
   references this product never queries.
3. **Drift.** The version is exactly pinned because an upgrade silently moves
   chart output (`tests/growth/test_dependency_pin.py`). Holding the tables
   ourselves makes the reference data a reviewable file rather than a package
   version.

Only the tables are needed. Cole's LMS arithmetic already exists in
`lms_core.py` — that part of the dependency was never load-bearing.

## What to download

WHO publishes the Multicentre Growth Reference Study tables openly, as **L, M, S
by age**, per sex and indicator:

| Indicator | Ages | WHO publication |
|---|---|---|
| Length/height-for-age | 0–5 y | WHO Child Growth Standards (2006) |
| Weight-for-age | 0–5 y | WHO Child Growth Standards (2006) |
| BMI-for-age | 0–5 y | WHO Child Growth Standards (2006) |
| Height-for-age | 5–19 y | WHO Growth Reference (2007) |
| Weight-for-age | 5–10 y | WHO Growth Reference (2007) |
| BMI-for-age | 5–19 y | WHO Growth Reference (2007) |

Take the **LMS** files, not the percentile or z-score tables — the whole point
is to hold the parameters rather than re-fit them from drawn centiles, which is
the mistake documented for the IAP charts in `PROVENANCE.md`.

Weight-for-age genuinely stops at 10 y in the 2007 reference. That is WHO's
decision, not a gap: weight alone stops being interpretable once puberty starts.
`who_lms_reference.WEIGHT_MAX_AGE` encodes it.

## Installing

Put every downloaded file in one directory, named so the sex and measure are
readable (`who_boys_height_0_5.csv`, `who_girls_bmi_5_19.txt`, …), then:

```bash
python -m backend.growth.ingest_who_lms --from-who ~/Downloads/who_tables
```

The tool accepts CSV, TSV or JSON, infers whether the age column is in years,
months or days (and **reports which**, rather than assuming), and merges the
0–5 y and 5–19 y studies into one table per sex and measure.

### The overlap is handled explicitly, and it matters

WHO's two studies **overlap**: the under-five tables run a little past 5.0 y
while the over-five tables start at 5.0 y, and they carry different L and S
there. Interleaving both into one interpolant puts an over-five row between two
under-five neighbours; the resulting kink moved the ±3 SD lines by up to
**0.55 cm** at 5.0 y when this tool first ran. The median was unaffected, which
is why only the tails showed it.

So the overlap is resolved by range — under-five owns everything up to its own
last age, over-five everything above — not by deduplication.

## The gate

```bash
python -m backend.growth.ingest_who_lms --gate
```

The tables must reproduce `rcpchgrowth`'s output across a dense age grid at
every percentile the charts draw, for every measure and sex, to within 0.02
units. This is a stronger gate than any other reference in this project gets:
the thing being replaced is still installed, so the check is against the exact
behaviour being replaced rather than against a published table.

Ages strictly inside a seam window (2.0 y and ~5.08 y — see
`who_reference.py`) are excluded, and that is a statement about the code:
`who_value_at_z` does not read the raw lookup there. Inside a window it
evaluates a Hermite bridge built only from the window's endpoints, so a raw
value inside it reaches no caller. The endpoints and their derivative probe
points **are** compared.

## Then, and only then

```bash
# after --gate reports active: true
#   1. remove the rcpchgrowth line from requirements.txt
#   2. update tests/growth/test_dependency_pin.py, which currently asserts it IS pinned
#   3. re-run the full growth suite
```

Removing the requirement is a **separate step, done second**. The dependency is
the oracle the gate compares against — drop it first and there is nothing left
to prove equivalence with.

## A note on the bootstrap path

`--from-installed-rcpchgrowth` lifts the same numbers out of the installed
package. It exists so the engine could be verified before the WHO files are in
hand, and it works: the gate passes at 10,878 compared points, worst deviation
0.0023 cm.

It is **not** a substitute for downloading from WHO. The numbers are WHO's and
factual, but the files are bundled in an AGPL-3.0 package, and whether
extracting them carries an obligation is a question about that licence — which
is the very thing this milestone exists to escape. The tool records
`source: rcpchgrowth-<version>` in `who_lms/PROVENANCE.json` and prints the
caveat, so a bootstrap can never be mistaken for WHO provenance.

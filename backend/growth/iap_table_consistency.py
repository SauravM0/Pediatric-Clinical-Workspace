"""Are the IAP CSV columns mutually consistent with ONE Cole distribution?

Written for M1.1 ingestion, and it changed the design of the gate.

The finding
-----------
The reproduction gate asks: "do these L,M,S values regenerate the published
percentile table?" That presumes the table *is* the Cole transform of a single
(L, M, S) at each age. For the four height and weight CSVs here, it is not.

Fit L, M, S per age against p3/p50/p97 and invert every column back to the z it
implies. On a genuine LMS table each column returns its own label. These do not
-- and the pattern is the same in all four files, at all 27 ages:

    column   implied centile   implied z      nominal z
    p3            3.0          -1.88079  (anchor)
    p10          10.5          -1.2529        -1.28155
    p25          26.5          -0.6270        -0.67449
    p50          50.0           0.0      (anchor)
    p75          73.5          +0.6273        +0.67449
    p90          89.5          +1.2544        +1.28155
    p97          97.0          +1.88079 (anchor)

Every interior column is pulled toward the median, by more the closer it starts.
The implied z values are not arbitrary: dividing the p3..p97 z-range into six
equal steps gives +-1.88079/3 = +-0.62693 and +-1.88079*2/3 = +-1.25386, which
matches the implied values to three decimal places.

Reading the interior columns at those equal-step z values instead of their
nominal ones drops the worst reproduction error from 0.27-0.77 units to
0.057-0.095 -- i.e. to rounding noise. So p10, p25, p75 and p90 in these four
files are **interpolated fillers, evenly spaced in z between p3 and p97**, not
values read from the paper. Only p3, p50 and p97 carry independent information.

Consequence for a patient: the line drawn as the 25th centile is the 26.5th, and
the 10th is the 10.5th. In value terms 0.27-0.48 cm and 0.30-0.77 kg -- small,
systematic, one-directional, and entirely avoidable.

Why this is about the data and not about the probe
--------------------------------------------------
The identical procedure was run against WHO -- a real LMS reference -- with its
centiles rounded to the same 0.1 unit these CSVs carry. It recovered 25.00,
75.00, 10.00 and 90.00, worst error 0.07 centile.

BMI is unaffected: its five columns imply 3.0/4.94/10.0/24.97/50.0 and reproduce
to within 0.057. Note that includes p25 -- so this is not "p25 is unreliable", it
is these four height/weight files. BMI came from a different paper
(IJEM 2015;19(4):470-6) and was evidently transcribed differently.

The cause is inferred, not confirmed at source
----------------------------------------------
The paper states Cole's LMS was used and that 3rd/10th/25th/50th/75th/90th/97th
percentiles were generated, so the paper's own table should sit at nominal z.
That points at reconstruction during transcription here rather than at the
publication. It is not proven: PROVENANCE.md records these CSVs as
author-transcribed with **zero of 1,134 cells verified against the paper**, and
that pending GC-1 dual-person check is what would settle it. This module is an
argument for doing it.

An earlier hypothesis of this author's -- that p25/p75 were arithmetic means of
their neighbours -- was measured and REJECTED: it holds for most height cells but
misses weight by up to 0.9 kg, and WHO fails the same test.

What it changes
---------------
The gate must not fail the authors' real L,M,S because of columns these CSVs
reconstructed. The disagreement is 0.27-0.77 units against a tolerance of 0.06,
so the real parameters would be REJECTED on arrival, and the obvious "fix" would
be to loosen the tolerance to ~0.8 -- wide enough to admit genuine transcription
errors, which is the one thing the gate exists to stop.

So :data:`GATE_EXCLUDED_CENTILES` holds out the reconstructed columns while
:func:`consistency_report` keeps reporting them. What remains still has teeth:
p3, p50 and p97 at 27 ages x 2 sexes is 162 independent checks per measure, and
they pin the median and both tails -- exactly where a wrong L or S shows up
first. BMI keeps all five columns.

If the GC-1 verification later replaces the reconstructed columns with published
ones, emptying GATE_EXCLUDED_CENTILES is the correct end state.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import norm

from . import measures as _measures
from .lms_core import lms_value_at_z, lms_z_score

_DATA_DIR = Path(__file__).resolve().parent / "data"

# Standard-normal z for each published centile column.
Z_FOR_CENTILE: dict[int, float] = {
    3: -1.88079, 5: -1.64485, 10: -1.28155, 25: -0.67449,
    50: 0.0, 75: 0.67449, 90: 1.28155, 97: 1.88079,
}

# Columns held out of the gate's pass/fail decision, per the module docstring:
# the ones reconstructed by equal z-spacing rather than read from the paper.
# Empty for BMI, whose columns are mutually consistent.
GATE_EXCLUDED_CENTILES: dict[str, tuple[int, ...]] = {
    "height": (10, 25, 75, 90),
    "weight": (10, 25, 75, 90),
    "bmi": (),
}

# Where the reconstructed columns actually sit: the p3..p97 z-range divided into
# six equal steps. Kept as data so the claim in the docstring is executable --
# tests assert the CSVs match THESE and not the nominal centile z values.
_Z_P97 = 1.88079
RECONSTRUCTED_Z: dict[int, float] = {
    10: -_Z_P97 * 2 / 3, 25: -_Z_P97 / 3, 75: _Z_P97 / 3, 90: _Z_P97 * 2 / 3,
}

# A column is flagged when its implied centile is this far from its label. The
# WHO control scattered by 0.07 centile, so 0.5 is comfortably above measurement
# noise while far below the ~1.5 actually observed.
IMPLIED_CENTILE_TOL = 0.5

# Columns the per-age fit is anchored on, per measure. These are exact by
# construction, so they are never evidence about themselves -- the diagnosis is
# what the OTHER columns do relative to them. Height/weight use the widest
# available spread; BMI's published table stops at p50, so it anchors inside
# its own range (an anchor set must exist or the fit is underdetermined, which
# is how BMI silently reported nothing in the first draft of this module).
ANCHOR_CENTILES: dict[str, tuple[int, ...]] = {
    "height": (3, 50, 97),
    "weight": (3, 50, 97),
    "bmi": (3, 10, 50),
}


def gate_centiles(measure: str) -> tuple[int, ...]:
    """Published columns the gate is entitled to judge an L,M,S file against."""
    excluded = set(GATE_EXCLUDED_CENTILES.get(measure, ()))
    return tuple(c for c in _measures.PUBLISHED_CENTILES[measure] if c not in excluded)


def _csv_path(measure: str, sex: str) -> Path:
    prefix = {"boys": "boy", "girls": "girl"}[sex]
    return _DATA_DIR / f"{prefix}_{_measures.FILE_PART[measure]}_IAP_5_18.csv"


def _rows(measure: str, sex: str) -> list[dict[int, float]]:
    cols = _measures.PUBLISHED_CENTILES[measure]
    out = []
    with open(_csv_path(measure, sex), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append({c: float(row[f"p{c}"]) for c in cols if f"p{c}" in row})
    return out


def _fit_lms(values: dict[int, float], anchors: tuple[int, ...]) -> Optional[tuple[float, float, float]]:
    """L, M, S least-squares fitted to the given columns only."""
    cols = [c for c in anchors if c in values]
    if len(cols) < 3:
        return None
    zs = np.array([Z_FOR_CENTILE[c] for c in cols])
    ys = np.array([values[c] for c in cols])

    def residual(p):
        l, m, s = p
        if m <= 0 or s <= 1e-6:
            return np.full(len(zs), 1e6)
        got = [lms_value_at_z(l, m, s, z) for z in zs]
        if any(g is None for g in got):
            return np.full(len(zs), 1e6)
        return np.array(got) - ys

    fit = least_squares(residual, [1.0, values[50], 0.12], max_nfev=20000)
    return float(fit.x[0]), float(fit.x[1]), float(fit.x[2])


@lru_cache(maxsize=16)
def implied_centiles(measure: str, sex: str,
                     anchors: Optional[tuple[int, ...]] = None) -> dict[int, float]:
    """Where each published column actually sits, in centiles.

    L,M,S is fitted per age against ``anchors`` (exact there by construction),
    then every column's value is inverted through that distribution. A column
    returning its own label is consistent with the anchors; one that does not
    cannot come from the same distribution.
    """
    anchors = anchors or ANCHOR_CENTILES[measure]
    per_column: dict[int, list[float]] = {}
    n_fitted = 0
    for values in _rows(measure, sex):
        triplet = _fit_lms(values, anchors)
        if triplet is None:
            continue
        n_fitted += 1
        for centile, value in values.items():
            z = lms_z_score(value, *triplet)
            if z is not None:
                per_column.setdefault(centile, []).append(z)
    if not n_fitted:
        raise ValueError(
            f"{sex}/{measure}: no age row could be fitted on anchors {anchors}. "
            "An empty diagnosis reads as 'consistent', so this raises instead."
        )
    return {c: float(norm.cdf(np.mean(zs)) * 100) for c, zs in sorted(per_column.items())}


@lru_cache(maxsize=16)
def gate_residual(measure: str, sex: str) -> float:
    """Worst value-space error when an L,M,S is fitted to the GATE columns only.

    This is the number that decides whether the gate's tolerance is reachable at
    all. If a free three-parameter fit cannot reproduce the very columns the gate
    judges against, then no supplied file can either, and the gate would reject
    the authors' real parameters for a defect in the CSVs.
    """
    cols = gate_centiles(measure)
    worst = 0.0
    for values in _rows(measure, sex):
        triplet = _fit_lms(values, cols)
        if triplet is None:
            continue
        for c in cols:
            got = lms_value_at_z(*triplet, Z_FOR_CENTILE[c])
            if got is not None:
                worst = max(worst, abs(got - values[c]))
    return worst


def consistency_report() -> dict:
    """Per-series column diagnosis, for the ingestion CLI and /api/growth/validate."""
    series = {}
    any_flagged = False
    for measure in _measures.IAP_TABLE_KEYS:
        for sex in ("boys", "girls"):
            implied = implied_centiles(measure, sex)
            # Anchors are exact by construction, so they are excluded from the
            # verdict -- counting them as "consistent" would inflate it.
            anchors = ANCHOR_CENTILES[measure]
            flagged = sorted(
                c for c, got in implied.items()
                if c not in anchors and abs(got - c) > IMPLIED_CENTILE_TOL
            )
            any_flagged = any_flagged or bool(flagged)
            series[f"{sex}/{measure}"] = {
                "anchors": list(anchors),
                "implied_centiles": {c: round(v, 2) for c, v in implied.items()},
                "flagged_columns": flagged,
                "excluded_from_gate": list(GATE_EXCLUDED_CENTILES.get(measure, ())),
                "gate_columns": list(gate_centiles(measure)),
                "gate_residual": round(gate_residual(measure, sex), 4),
            }
    return {
        "all_columns_consistent": not any_flagged,
        "tolerance_centiles": IMPLIED_CENTILE_TOL,
        "series": series,
        "note": (
            "Columns whose implied centile differs from their label cannot come "
            "from the same Cole distribution as the anchors. See "
            "iap_table_consistency.__doc__ and PROVENANCE.md — these CSVs are "
            "author-transcribed and not yet verified against the paper."
        ),
    }


if __name__ == "__main__":  # pragma: no cover
    import json

    print(json.dumps(consistency_report(), indent=2))

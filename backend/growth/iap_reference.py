"""IAP 2015 (Khadilkar et al.) Indian growth reference, 5-18 years.

India is not one of rcpchgrowth's bundled references, and the IAP committee's
original L,M,S triplets were never published (available only on request from
the authors -- Khadilkar V, et al. Indian Pediatrics 2015;52:47-55; Khadilkar
VV & Khadilkar AV, Indian J Endocrinol Metab 2015;19(4):470-6). What *is*
published is the full percentile table (p3/p10/p25/p50/p75/p90/p97 for height
& weight; p3/p5/p10/p25/p50 + IOTF 23/27 adult-equivalent cutoffs for BMI) at
0.5-year steps, 5.0-18.0y -- see actual LMS macro/*.csv, sourced directly from
the paper. This module fits Cole's L,M,S to those *real, published* numbers
(holding M fixed at the exact published median, since that's ground truth and
free to reproduce exactly; only L and S are fit, to the remaining points), then
feeds every subsequent measurement/z-score calculation through rcpchgrowth's
generic LMS functions (lms_core) -- so the fitting is ours (necessarily, since
no one has released the original coefficients), but the actual clinical
computation is rcpchgrowth's tested implementation, exactly as for WHO.

This is fit once at import time and cached; it is not a per-request cost.

Chart-rendering exact reproduction -- the LMS refit above is a 2-parameter
(L,S) least-squares approximation to 6 independent published targets (M is
pinned exact, but that leaves 2 numbers to satisfy 6 points), which is
overdetermined and so can only ever land *close* to the published table, not
on it -- confirmed against this app's own reference-chart images: every
non-median percentile is off by up to ~0.4-0.65 units at some ages, even
though the chart's whole purpose is to reproduce that exact table. For any
percentile that IS actually published (all 7 standard centiles for
height/weight; 3/10/25/50 for BMI), we have the real numbers already, so the
rendered curve interpolates that column directly
(monotone PCHIP across the published ages) instead of going through the LMS
approximation at all -- see iap_value_at_z's exact-table branch. This makes
the drawn curve match the paper's table exactly at every published age.

The LMS fit is still the only source for: BMI's unpublished upper tail
(75/90/97 -- the paper's BMI table only goes up to the median, so there's
nothing exact to interpolate there), z-scores for an arbitrary *observed*
patient value (iap_z_for_value -- inverting a continuous measurement needs a
continuous model, not 7 discrete table points), and a small guard band just
above IAP_MIN_AGE (see _EXACT_TABLE_GUARD) that blend.py's WHO/IAP seam
derivative calculation depends on staying LMS-based end to end.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator, UnivariateSpline
from scipy.optimize import curve_fit

from .lms_core import lms_value_at_z, lms_z_score

_DATA_DIR = Path(__file__).resolve().parent / "data"

# 3/10/25/50/75/90/97 standard centiles -> z; BMI's published table only has
# the lower half (3/5/10/25/50) plus two IOTF adult-equivalent cutoff curves
# that are NOT fixed-z percentiles (see bmi_cutoffs_at below).
_Z_HEIGHT_WEIGHT = {3: -1.88079, 10: -1.28155, 25: -0.67449, 50: 0.0, 75: 0.67449, 90: 1.28155, 97: 1.88079}
_Z_BMI = {3: -1.88079, 5: -1.64485, 10: -1.28155, 25: -0.67449, 50: 0.0}

# IAP is only real data for 5.0-18.0y. A short backward extrapolation shoulder
# (down to 4.5y) is retained purely so blend.py has real IAP-side curvature to
# blend against across the 4.0-5.0y transition window -- see blend.py.
IAP_MIN_AGE = 5.0
IAP_MAX_AGE = 18.0
BLEND_SHOULDER_AGE = 4.5

# blend.py's bridge (blend._quintic_bridge) anchors on iap_value_at_z at
# IAP_MIN_AGE itself AND probes its derivative/curvature at IAP_MIN_AGE
# +-1/24y (blend._DERIV_EPS_YEARS) -- validation.py's own edge-continuity
# checks probe a bit further still (+-EPS_YEARS/2, each with its own further
# +-EPS_YEARS=0.08y). All three of those quantities (value, slope, curvature)
# have to come from the *same* underlying function at that boundary, or the
# bridge is handed a value from one model and a slope/curvature from another,
# which is self-inconsistent and was confirmed (empirically, via
# validation.run_full_validation) to reintroduce centile-ordering violations
# and slope-continuity failures right at the seam. So the exact-table branch
# below only activates comfortably *past* every one of those probe points --
# never at IAP_MIN_AGE itself, even though that's a published value too;
# everything up to the guard band still resolves through the LMS fit, exactly
# as the bridge math assumes.
_EXACT_TABLE_GUARD = 0.15  # years -- clears the deepest probe above (~0.12y)

_SEX_FILE = {"boys": "boy", "girls": "girl"}


def _cole(z, l, m, s):
    l_safe = np.where(np.abs(l) < 1e-6, 1e-6, l)
    return m * np.power(1 + l_safe * s * z, 1.0 / l_safe)


def _fit_row(row: dict, zmap: dict[int, float]) -> tuple[float, float, float]:
    """Fit L,S with M held fixed at the exact published median."""
    cols = [c for c in zmap if c != 50]
    zs = np.array([zmap[c] for c in cols])
    vals = np.array([row[c] for c in cols], dtype=float)
    m = float(row[50])
    s0 = (row.get(75, row[50] * 1.1) - row.get(25, row[50] * 0.9)) / (2 * m * 0.6745)

    def cole_fixed_m(z, l, s):
        return _cole(z, l, m, s)

    (l, s), _ = curve_fit(cole_fixed_m, zs, vals, p0=[1.0, s0], maxfev=20000)
    return float(l), m, float(s)


def _load_csv(path: Path, pct_cols: list[int]) -> dict[float, dict]:
    rows: dict[float, dict] = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            age = float(r["age_years"])
            rows[age] = {p: float(r[f"p{p}"]) for p in pct_cols}
    return rows


def _load_bmi_csv(path: Path) -> tuple[dict[float, dict], dict[float, tuple[float, float]]]:
    rows: dict[float, dict] = {}
    cutoffs: dict[float, tuple[float, float]] = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            age = float(r["age_years"])
            rows[age] = {p: float(r[f"p{p}"]) for p in (3, 5, 10, 25, 50)}
            cutoffs[age] = (float(r["adult_eq_23"]), float(r["adult_eq_27"]))
    return rows, cutoffs


@dataclass
class _FittedSeries:
    """L(age), exact-median M(age), S(age) as callables, valid over
    [BLEND_SHOULDER_AGE, IAP_MAX_AGE]; plus, for whichever centiles are
    actually published (table_fns), a direct monotone interpolation across
    the published ages -- the exact-reproduction path (see module docstring),
    valid only over the real data domain [IAP_MIN_AGE, IAP_MAX_AGE]."""
    l_fn: object
    m_fn: object
    s_fn: object
    age_min: float
    age_max: float
    table_fns: dict[int, object] = field(default_factory=dict)

    def lms_at(self, age_years: float) -> tuple[float, float, float]:
        a = min(max(age_years, self.age_min), self.age_max)
        return float(self.l_fn(a)), float(self.m_fn(a)), float(self.s_fn(a))


def _build_series(rows: dict[float, dict], zmap: dict[int, float], smooth_ls: bool) -> _FittedSeries:
    ages = np.array(sorted(rows.keys()))
    fitted = [_fit_row(rows[a], zmap) for a in ages]
    ls = np.array([f[0] for f in fitted])
    ms = np.array([f[1] for f in fitted])
    ss = np.array([f[2] for f in fitted])

    m_fn = CubicSpline(ages, ms)
    if smooth_ls:
        # BMI's L is only weakly identified from 5 nearby low-half percentiles
        # (all close to the median) -- per-age fits come out jagged even though
        # the percentiles they reproduce are fine. Smooth L/S against age; M
        # (and therefore the published percentiles at the sampled ages) stays
        # exact regardless, since it's a separate exact spline above.
        n = len(ages)
        l_fn = UnivariateSpline(ages, ls, k=3, s=n * 0.35)
        s_fn = UnivariateSpline(ages, ss, k=3, s=n * 0.0006)
    else:
        l_fn = CubicSpline(ages, ls)
        s_fn = CubicSpline(ages, ss)

    # Exact-reproduction path: interpolate each published percentile column
    # directly across age (shape-preserving, so it can't overshoot the real
    # data between ages) -- this is what iap_value_at_z reaches for first, see
    # module docstring. Built for every column zmap knows about (all 7 for
    # height/weight, 3/10/25/50 for BMI).
    table_fns = {p: PchipInterpolator(ages, np.array([rows[a][p] for a in ages], dtype=float)) for p in zmap}

    # Extend the LMS fit's *evaluable* domain down to the blend shoulder
    # (backward extrapolation via the same spline) -- real data still starts
    # at 5.0y; the exact table_fns above never extrapolate past IAP_MIN_AGE.
    return _FittedSeries(l_fn, m_fn, s_fn, BLEND_SHOULDER_AGE, IAP_MAX_AGE, table_fns)


def _build_cutoff_series(cutoffs: dict[float, tuple[float, float]]):
    ages = np.array(sorted(cutoffs.keys()))
    c23 = np.array([cutoffs[a][0] for a in ages])
    c27 = np.array([cutoffs[a][1] for a in ages])
    return CubicSpline(ages, c23), CubicSpline(ages, c27), ages.min(), ages.max()


def _load_all():
    series: dict[tuple[str, str], _FittedSeries] = {}
    cutoff_series: dict[str, tuple] = {}
    for sex, prefix in _SEX_FILE.items():
        h_rows = _load_csv(_DATA_DIR / f"{prefix}_height_cm_IAP_5_18.csv", [3, 10, 25, 50, 75, 90, 97])
        w_rows = _load_csv(_DATA_DIR / f"{prefix}_weight_kg_IAP_5_18.csv", [3, 10, 25, 50, 75, 90, 97])
        b_rows, b_cutoffs = _load_bmi_csv(_DATA_DIR / f"{prefix}_bmi_IAP_5_18.csv")

        series[(sex, "height")] = _build_series(h_rows, _Z_HEIGHT_WEIGHT, smooth_ls=False)
        series[(sex, "weight")] = _build_series(w_rows, _Z_HEIGHT_WEIGHT, smooth_ls=False)
        series[(sex, "bmi")] = _build_series(b_rows, _Z_BMI, smooth_ls=True)
        cutoff_series[sex] = _build_cutoff_series(b_cutoffs)
    return series, cutoff_series


_SERIES, _CUTOFF_SERIES = _load_all()


def iap_covers(age_years: float) -> bool:
    return BLEND_SHOULDER_AGE <= age_years <= IAP_MAX_AGE


def _centile_for_z(measure: str, z: float) -> int | None:
    """Which published centile column (if any) this z-score exactly asks
    for -- e.g. curve_builder always queries one of the 7 standard centiles,
    so this matches essentially always for height/weight, and for BMI's
    published lower half."""
    zmap = _Z_BMI if measure == "bmi" else _Z_HEIGHT_WEIGHT
    for centile, zz in zmap.items():
        if abs(zz - z) < 1e-4:
            return centile
    return None


def iap_value_at_z(measure: str, sex: str, age_years: float, z: float) -> float | None:
    if not iap_covers(age_years):
        return None
    series = _SERIES[(sex, measure)]

    # Exact-reproduction path (see module docstring): only comfortably past
    # the guard band, and only for a centile that's actually published. Never
    # at/near IAP_MIN_AGE itself -- see _EXACT_TABLE_GUARD.
    if age_years >= IAP_MIN_AGE + _EXACT_TABLE_GUARD:
        centile = _centile_for_z(measure, z)
        table_fn = series.table_fns.get(centile) if centile is not None else None
        if table_fn is not None:
            return float(table_fn(min(age_years, IAP_MAX_AGE)))

    l, m, s = series.lms_at(age_years)
    return lms_value_at_z(l, m, s, z)


def iap_z_for_value(measure: str, sex: str, age_years: float, value: float) -> float | None:
    if not iap_covers(age_years):
        return None
    l, m, s = _SERIES[(sex, measure)].lms_at(age_years)
    return lms_z_score(value, l, m, s)


def iap_bmi_cutoffs(sex: str, age_years: float) -> tuple[float, float] | None:
    """IAP/IOTF adult-equivalent 23 & 27 kg/m^2 overweight/obesity boundary
    curves -- the Indian-specific classification the paper defines, not a
    fixed BMI z-score cutoff like WHO's +1/+2 SD."""
    cs23, cs27, amin, amax = _CUTOFF_SERIES[sex]
    if not (BLEND_SHOULDER_AGE <= age_years <= amax):
        return None
    a = min(max(age_years, amin), amax)
    return float(cs23(a)), float(cs27(a))

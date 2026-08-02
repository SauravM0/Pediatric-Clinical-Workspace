"""IAP 2015 growth reference from published L,M,S — the replacement path (M1.1).

**The data is not bundled and is not invented.** This module is the complete
engineering half of M1.1: loader, activation gate, and the exact-reproduction
check. It activates itself the moment a valid ``iap_2015_lms.csv`` is dropped in,
and stays inert until then. See ``data/IAP-LMS-REQUEST.md`` for what to ask the
authors for.

Why this matters more than any other single item in the roadmap
---------------------------------------------------------------
Today ``iap_reference.py`` has only the published *percentile values*, so it
maintains three parallel machines to work around that: a 2-parameter L,S refit
(overdetermined against 6 published points, so it can only ever land close), an
exact-table PCHIP path for the drawn centiles, and ``_z_from_display_anchors`` to
invert them — plus ``_EXACT_TABLE_GUARD`` to stop the three colliding at the
WHO/IAP seam. With real L,M,S all three collapse into one closed-form Cole
transform, and the residual 0.069 SD tail error (M1.2) goes to zero, because it
is the refit's own approximation error and nothing else.

Strangler pattern, deliberately
-------------------------------
This module sits ALONGSIDE ``iap_reference`` and does not modify it. The legacy
paths are removed only after the equivalence gate passes on real data — deleting
``_EXACT_TABLE_GUARD`` early would re-introduce the seam inconsistency it was
added to fix (``blend._quintic_bridge`` probes derivatives right at that
boundary, and validation.run_full_validation caught it last time).

Activation is on EVIDENCE, not a flag
-------------------------------------
``lms_status()`` reports why the path is or is not live. A flag someone flips is
a flag someone flips by mistake; requiring the file to reproduce the published
table before it can be used means a bad transcription cannot silently become the
reference. ``PCW_DISABLE_IAP_LMS=1`` is a kill switch, not an enable switch.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.interpolate import PchipInterpolator

from . import measures as _measures
from .lms_core import lms_value_at_z, lms_z_score

_DATA_DIR = Path(__file__).resolve().parent / "data"
LMS_PATH = _DATA_DIR / "iap_2015_lms.csv"

SEXES = ("boys", "girls")
# Canonical registry (M0.3) -- a measure added there must not be silently
# absent from the LMS requirement, or the file would "pass" while missing one.
MEASURES = _measures.MEASURE_KEYS
AGE_MIN, AGE_MAX = 5.0, 18.0
REQUIRED_AGES = tuple(round(5.0 + 0.5 * i, 1) for i in range(27))  # 5.0 .. 18.0

# Tolerance for "does this L,M,S reproduce the paper's own percentile table".
# The published values are quoted to 0.1 units, so a correct LMS triplet should
# land within rounding of them. A looser bound would let a transcription error
# through; a tighter one would fail on the paper's own rounding.
REPRODUCTION_TOL = {k: 0.06 for k in _measures.MEASURE_KEYS}

_CSV_SEX = {"boy": "boys", "boys": "boys", "girl": "girls", "girls": "girls"}


class LmsDataError(ValueError):
    """The LMS file exists but is not usable."""


@dataclass(frozen=True)
class LmsSeries:
    ages: np.ndarray
    l_fn: object
    m_fn: object
    s_fn: object

    def at(self, age_years: float) -> tuple[float, float, float]:
        a = float(min(max(age_years, self.ages[0]), self.ages[-1]))
        return float(self.l_fn(a)), float(self.m_fn(a)), float(self.s_fn(a))


def disabled_by_env() -> bool:
    return os.environ.get("PCW_DISABLE_IAP_LMS", "").strip().lower() in ("1", "true", "yes")


def _read_rows() -> dict[tuple[str, str], dict[float, tuple[float, float, float]]]:
    out: dict[tuple[str, str], dict[float, tuple[float, float, float]]] = {}
    with open(LMS_PATH, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            if not (row.get("sex") or "").strip():
                continue  # blank template line
            try:
                sex = _CSV_SEX[row["sex"].strip().lower()]
                measure = row["measure"].strip().lower()
                age = round(float(row["age_years"]), 2)
                triplet = (float(row["L"]), float(row["M"]), float(row["S"]))
            except (KeyError, ValueError) as exc:
                raise LmsDataError(f"{LMS_PATH.name} line {i}: {exc}") from exc
            if measure not in MEASURES:
                raise LmsDataError(f"{LMS_PATH.name} line {i}: unknown measure {measure!r}")
            if triplet[1] <= 0 or triplet[2] <= 0:
                raise LmsDataError(
                    f"{LMS_PATH.name} line {i}: M and S must be positive "
                    f"(got M={triplet[1]}, S={triplet[2]})"
                )
            out.setdefault((sex, measure), {})[age] = triplet
    return out


@lru_cache(maxsize=1)
def _load() -> Optional[dict[tuple[str, str], LmsSeries]]:
    """Parse and interpolate, or None when the file is absent/incomplete."""
    if not LMS_PATH.exists():
        return None
    rows = _read_rows()
    if not rows:
        return None

    series: dict[tuple[str, str], LmsSeries] = {}
    for sex in SEXES:
        for measure in MEASURES:
            table = rows.get((sex, measure))
            if not table:
                return None
            missing = [a for a in REQUIRED_AGES if a not in table]
            if missing:
                raise LmsDataError(
                    f"{sex}/{measure}: LMS missing for age(s) {missing[:6]}"
                    f"{'...' if len(missing) > 6 else ''}. The full 5.0-18.0y grid "
                    "at 0.5y steps is required — a partial table would silently "
                    "extrapolate over the gaps."
                )
            ages = np.array(sorted(table))
            l = np.array([table[a][0] for a in ages])
            m = np.array([table[a][1] for a in ages])
            s = np.array([table[a][2] for a in ages])
            # Interpolate L, M and S SEPARATELY, then apply Cole. Interpolating
            # the resulting VALUES instead is subtly wrong for a skewed
            # distribution: the centile curve between two knots is not the
            # Cole transform of the interpolated parameters.
            series[(sex, measure)] = LmsSeries(
                ages, PchipInterpolator(ages, l), PchipInterpolator(ages, m),
                PchipInterpolator(ages, s))
    return series


def reset_cache() -> None:
    """Test seam — the file is read once per process in normal operation."""
    _load.cache_clear()
    _reproduction.cache_clear()


# ── the activation gate ─────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _reproduction() -> dict:
    """Does the LMS reproduce the paper's own published percentile table?

    This is the gate. A transcription error in an L,M,S triplet is invisible by
    inspection but shows up immediately as a centile that does not match the
    published number, so the reference is checked against the numbers it is
    supposed to explain before it is allowed to become the reference.
    """
    from . import iap_reference as legacy

    series = _load()
    if series is None:
        return {"checked": 0, "worst": {}, "ok": False, "reason": "no LMS data"}

    worst: dict[str, float] = {}
    checked = 0
    for sex, prefix in (("boys", "boy"), ("girls", "girl")):
        for measure in _measures.IAP_TABLE_KEYS:
            zmap = legacy._Z_BMI if measure == "bmi" else legacy._Z_HEIGHT_WEIGHT
            path = _DATA_DIR / f"{prefix}_{_measures.FILE_PART[measure]}_IAP_5_18.csv"
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    age = float(row["age_years"])
                    l, m, s = series[(sex, measure)].at(age)
                    for centile, z in zmap.items():
                        col = f"p{centile}"
                        if col not in row:
                            continue
                        got = lms_value_at_z(l, m, s, z)
                        err = abs(got - float(row[col]))
                        worst[measure] = max(worst.get(measure, 0.0), err)
                        checked += 1

    ok = all(worst.get(k, 0.0) <= REPRODUCTION_TOL[k] for k in MEASURES)
    return {
        "checked": checked,
        "worst": {k: round(v, 4) for k, v in worst.items()},
        "tolerance": REPRODUCTION_TOL,
        "ok": ok,
        "reason": "ok" if ok else "LMS does not reproduce the published percentile table",
    }


def lms_available() -> bool:
    """True only when real LMS data is present, complete, and reproduces the
    published table. Everything else keeps using the legacy fit."""
    if disabled_by_env():
        return False
    try:
        if _load() is None:
            return False
        return bool(_reproduction()["ok"])
    except LmsDataError:
        return False


def lms_status() -> dict:
    """Why the LMS path is or is not live — surfaced on /api/growth/validate."""
    if disabled_by_env():
        return {"active": False, "reason": "disabled by PCW_DISABLE_IAP_LMS", "file_present": LMS_PATH.exists()}
    if not LMS_PATH.exists():
        return {
            "active": False, "file_present": False,
            "reason": (
                "backend/growth/data/iap_2015_lms.csv is not present. The IAP 2015 "
                "L,M,S values are not public; request them from the authors (see "
                "data/IAP-LMS-REQUEST.md). Until then the engine fits L and S to "
                "the published percentiles, which leaves a residual tail error of "
                "about 0.07 SD."
            ),
        }
    try:
        loaded = _load()
    except LmsDataError as exc:
        return {"active": False, "file_present": True, "reason": str(exc)}
    if loaded is None:
        return {"active": False, "file_present": True,
                "reason": "LMS file is present but empty or missing a sex/measure"}

    rep = _reproduction()
    return {
        "active": bool(rep["ok"]), "file_present": True,
        "reason": rep["reason"], "reproduction": rep,
    }


# ── the reference itself ────────────────────────────────────────────────────

def covers(age_years: float) -> bool:
    return AGE_MIN <= age_years <= AGE_MAX


def lms_at(measure: str, sex: str, age_years: float) -> Optional[tuple[float, float, float]]:
    series = _load()
    if series is None or not covers(age_years):
        return None
    entry = series.get((sex, measure))
    return None if entry is None else entry.at(age_years)


def iap_lms_value_at_z(measure: str, sex: str, age_years: float, z: float) -> Optional[float]:
    """Closed-form Cole. One path for every centile, published or not — no exact
    table, no guard band, no display-anchor inversion."""
    triplet = lms_at(measure, sex, age_years)
    if triplet is None:
        return None
    return lms_value_at_z(*triplet, z)


def iap_lms_z_for_value(measure: str, sex: str, age_years: float, value: float) -> Optional[float]:
    """Exact inverse of the above at every value, including the tails.

    This is what removes M1.2's residual: the tail is the distribution's own
    shape rather than an LMS-shaped extrapolation grafted onto a centile ladder.
    """
    triplet = lms_at(measure, sex, age_years)
    if triplet is None or not (value and value > 0):
        return None
    return lms_z_score(value, *triplet)

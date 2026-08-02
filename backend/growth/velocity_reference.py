"""Indian height-velocity reference (M1.3).

    Khadilkar V, Khadilkar A, Arya A, et al. Height Velocity Percentiles in
    Indian Children Aged 5-17 Years. Indian Pediatr 2019;56(1):23-8.

**The data is not bundled and is not invented.** As with the IAP L,M,S (M1.1),
this module is the complete engineering half: loader, activation gate, interval
guard, and SDS. It activates itself when a valid ``indian_height_velocity.csv``
appears. See ``data/VELOCITY-REFERENCE-REQUEST.md``.

Why velocity matters more than another distance centile
-------------------------------------------------------
Height velocity is the most sensitive single indicator of growth pathology. A
child can sit on the 25th centile for years and be entirely well; the same child
crossing downward at 3 cm/year is not. M2 computes the rate. Without this
reference there is nothing to compare it against, so M5's LOW_HEIGHT_VELOCITY
rule currently uses a 4 cm/year rule of thumb at ``confidence: low`` -- a coarse
floor standing in for "below the 25th centile for age".

The interval problem, which is the real subtlety here
-----------------------------------------------------
Velocity centiles are **interval-specific**, and this is not a technicality.
The reference is built from roughly annual measurements. Annualising a shorter
interval does not land on the same distribution: measurement error is divided by
a smaller delta-t, so the spread of annualised velocity widens as the interval
shrinks. Scoring a 4-month interval against an annual reference would report
perfectly ordinary children as extreme.

So the reference records the interval it was constructed on, and SDS is withheld
outside a tolerance band around it -- the rate is still reported, only the
centile is withheld. Same choice made everywhere else here: refuse rather than
answer with a number whose meaning does not hold.
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

from .lms_core import lms_value_at_z, lms_z_score

_DATA_DIR = Path(__file__).resolve().parent / "data"
REFERENCE_PATH = _DATA_DIR / "indian_height_velocity.csv"

SEXES = ("boys", "girls")
AGE_MIN, AGE_MAX = 5.0, 17.5

# The reference is built on ~annual measurements. SDS is only meaningful for an
# interval close to that; outside the band the rate is reported without a
# centile rather than scored against a distribution it does not belong to.
REFERENCE_INTERVAL_YEARS = 1.0
INTERVAL_TOLERANCE = (0.75, 1.25)

# Published median peak height velocity, from the paper's own abstract. Used
# only as a sanity check on an installed file -- a table that does not peak
# near these values is not this reference.
EXPECTED_PEAK = {
    "boys": {"velocity_cm_per_year": 6.8, "age_years": 13.5},
    "girls": {"velocity_cm_per_year": 6.6, "age_years": 10.5},
}
PEAK_TOL_CM = 1.0
PEAK_TOL_AGE = 1.0

_CSV_SEX = {"boy": "boys", "boys": "boys", "girl": "girls", "girls": "girls"}


class VelocityReferenceError(ValueError):
    """The velocity reference file exists but is not usable."""


@dataclass(frozen=True)
class VelocitySeries:
    ages: np.ndarray
    l_fn: object
    m_fn: object
    s_fn: object

    def at(self, age_years: float) -> tuple[float, float, float]:
        a = float(min(max(age_years, self.ages[0]), self.ages[-1]))
        return float(self.l_fn(a)), float(self.m_fn(a)), float(self.s_fn(a))


def disabled_by_env() -> bool:
    return os.environ.get("PCW_DISABLE_VELOCITY_REF", "").strip().lower() in ("1", "true", "yes")


@lru_cache(maxsize=1)
def _load() -> Optional[dict[str, VelocitySeries]]:
    """Parse the reference, or None when absent.

    Expects L,M,S per sex per age. The paper states the centiles were built with
    LMS ChartMaker, so the parameters exist -- and they are what makes an exact
    SDS possible rather than an interpolated ladder with the tail behaviour M1.2
    had to correct for the distance charts.
    """
    if not REFERENCE_PATH.exists():
        return None

    rows: dict[str, dict[float, tuple[float, float, float]]] = {}
    with open(REFERENCE_PATH, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            if not (row.get("sex") or "").strip():
                continue
            try:
                sex = _CSV_SEX[row["sex"].strip().lower()]
                age = round(float(row["age_years"]), 2)
                triplet = (float(row["L"]), float(row["M"]), float(row["S"]))
            except (KeyError, ValueError) as exc:
                raise VelocityReferenceError(f"{REFERENCE_PATH.name} line {i}: {exc}") from exc
            if triplet[1] <= 0 or triplet[2] <= 0:
                raise VelocityReferenceError(
                    f"{REFERENCE_PATH.name} line {i}: M and S must be positive"
                )
            rows.setdefault(sex, {})[age] = triplet

    if not rows:
        return None

    series: dict[str, VelocitySeries] = {}
    for sex in SEXES:
        table = rows.get(sex)
        if not table or len(table) < 8:
            raise VelocityReferenceError(
                f"{sex}: too few age rows ({len(table or {})}). The reference spans "
                f"{AGE_MIN}-{AGE_MAX}y and a sparse table would be interpolated "
                "across the pubertal peak, which is the part that matters."
            )
        ages = np.array(sorted(table))
        series[sex] = VelocitySeries(
            ages,
            PchipInterpolator(ages, np.array([table[a][0] for a in ages])),
            PchipInterpolator(ages, np.array([table[a][1] for a in ages])),
            PchipInterpolator(ages, np.array([table[a][2] for a in ages])),
        )
    return series


def reset_cache() -> None:
    _load.cache_clear()
    _peak_check.cache_clear()


# ── activation gate ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _peak_check() -> dict:
    """Does the installed table peak where the paper says it does?

    A weak but genuinely useful check: velocity references are distinctive in
    shape (a mid-childhood trough then a pubertal peak), so a table that does
    not peak near 6.8 cm/yr at 13.5y in boys and 6.6 at 10.5y in girls is not
    this reference -- most likely the wrong sex column, or distance values
    entered in place of velocity.
    """
    series = _load()
    if series is None:
        return {"ok": False, "reason": "no velocity reference data", "observed": {}}

    observed: dict[str, dict] = {}
    ok = True
    for sex in SEXES:
        grid = np.arange(AGE_MIN, AGE_MAX + 1e-9, 0.1)
        medians = np.array([series[sex].at(a)[1] for a in grid])
        i = int(np.argmax(medians))
        peak = {"velocity_cm_per_year": round(float(medians[i]), 2),
                "age_years": round(float(grid[i]), 2)}
        expected = EXPECTED_PEAK[sex]
        matches = (abs(peak["velocity_cm_per_year"] - expected["velocity_cm_per_year"]) <= PEAK_TOL_CM
                   and abs(peak["age_years"] - expected["age_years"]) <= PEAK_TOL_AGE)
        observed[sex] = {"observed": peak, "expected": expected, "matches": matches}
        ok = ok and matches

    return {
        "ok": ok, "observed": observed,
        "reason": "ok" if ok else (
            "the installed table does not peak where Khadilkar 2019 reports "
            "(boys 6.8 cm/yr at 13.5y, girls 6.6 at 10.5y) -- check the sex "
            "columns and that these are velocities, not distances"
        ),
    }


def reference_available() -> bool:
    if disabled_by_env():
        return False
    try:
        if _load() is None:
            return False
        return bool(_peak_check()["ok"])
    except VelocityReferenceError:
        return False


def reference_status() -> dict:
    if disabled_by_env():
        return {"active": False, "reason": "disabled by PCW_DISABLE_VELOCITY_REF"}
    if not REFERENCE_PATH.exists():
        return {
            "active": False, "file_present": False,
            "reason": (
                "backend/growth/data/indian_height_velocity.csv is not present. "
                "Height velocity is the most sensitive indicator of growth "
                "pathology and there is currently nothing to score it against, so "
                "the LOW_HEIGHT_VELOCITY rule falls back to a 4 cm/year rule of "
                "thumb at low confidence. See data/VELOCITY-REFERENCE-REQUEST.md."
            ),
            "source": "Khadilkar et al., Indian Pediatr 2019;56(1):23-8",
        }
    try:
        loaded = _load()
    except VelocityReferenceError as exc:
        return {"active": False, "file_present": True, "reason": str(exc)}
    if loaded is None:
        return {"active": False, "file_present": True, "reason": "file present but empty"}

    check = _peak_check()
    return {"active": bool(check["ok"]), "file_present": True,
            "reason": check["reason"], "peak_check": check["observed"],
            "reference_interval_years": REFERENCE_INTERVAL_YEARS,
            "valid_interval_years": list(INTERVAL_TOLERANCE)}


# ── scoring ─────────────────────────────────────────────────────────────────

def interval_is_scorable(interval_years: float) -> bool:
    lo, hi = INTERVAL_TOLERANCE
    return lo <= interval_years <= hi


def velocity_sds(sex: str, mid_age_years: float, cm_per_year: float,
                 interval_years: float) -> tuple[Optional[float], str]:
    """(SDS, status) for a measured velocity.

    Scored at the MIDPOINT of the interval, which is what the velocity actually
    describes -- attributing a year's growth to either endpoint would shift the
    comparison by half a year, and around the pubertal peak that is the
    difference between normal and abnormal.
    """
    if not reference_available():
        return None, "no_velocity_reference_available"
    if not interval_is_scorable(interval_years):
        lo, hi = INTERVAL_TOLERANCE
        return None, (
            f"interval_outside_reference_band: {interval_years:.2f}y is outside "
            f"{lo}-{hi}y. The reference is built on ~annual measurements, and "
            "annualising a shorter interval widens the spread, so a centile from "
            "it would misrepresent an ordinary child as extreme."
        )
    if not (AGE_MIN <= mid_age_years <= AGE_MAX):
        return None, f"age_outside_reference: {mid_age_years:.1f}y not in {AGE_MIN}-{AGE_MAX}y"

    series = _load()[sex]
    l, m, s = series.at(mid_age_years)
    return lms_z_score(cm_per_year, l, m, s), "ok"


def velocity_at_centile(sex: str, age_years: float, z: float) -> Optional[float]:
    """The reference velocity at a given z — for drawing the velocity chart."""
    if not reference_available() or not (AGE_MIN <= age_years <= AGE_MAX):
        return None
    l, m, s = _load()[sex].at(age_years)
    return lms_value_at_z(l, m, s, z)

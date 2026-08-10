"""WHO 2006/2007 reference from our OWN L,M,S tables (M1.4).

Replaces the ``rcpchgrowth`` dependency for the WHO layer. That package supplies
two things: WHO's published LMS tables, and Cole's LMS arithmetic. This project
already has the arithmetic (``lms_core``), so only the tables are genuinely
needed -- and those are WHO's own published data, not rcpchgrowth's.

Why remove a working dependency
-------------------------------
``rcpchgrowth`` is **AGPL-3.0**. Serving this app over a network triggers
AGPL §13's source-offer obligation for the whole combined work, which is a
licensing decision the operator of a clinic should make deliberately rather than
inherit from a transitive import. It is also ~9 MB of data tables for UK-WHO,
CDC, Trisomy-21 and Turner references this product never queries, and a pinned
version whose upgrade silently moves chart output (see
``tests/growth/test_dependency_pin.py``).

The gate is EQUIVALENCE, and it is the strongest one available
---------------------------------------------------------------
M1.1 could only ask "does this reproduce a published table". Here the thing
being replaced is still installed, so the gate is direct: our tables must
reproduce ``rcpchgrowth``'s own output across a dense age grid at every
percentile the charts draw, for every measure and sex. Anything that changes a
number a clinician has already seen fails.

That check is only possible while the incumbent is present, which is why the
dependency is removed in two steps: install the tables and prove equivalence
first, drop the requirement second. Reversing that order would mean deleting the
only available oracle.

Activation is on evidence, not a flag
-------------------------------------
``lms_status()`` reports why the path is or is not live. ``PCW_DISABLE_WHO_LMS=1``
is a kill switch, not an enable switch -- there is deliberately no variable that
forces our tables on, because activation is earned by matching the incumbent.
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

_DATA_DIR = Path(__file__).resolve().parent / "data" / "who_lms"

SEXES = ("boys", "girls")
# Only the measures this product actually charts. WHO also publishes head
# circumference; it is not ingested because nothing here reads it, and an
# unused table is one more thing to keep verified.
MEASURES = tuple(m.key for m in _measures.MEASURES.values() if m.who_backed)

AGE_MIN, AGE_MAX = 0.0, 19.0

# WHO weight-for-age is officially undefined beyond 10y -- the standard stops
# there because weight alone stops being interpretable once puberty starts.
WEIGHT_MAX_AGE = 10.0

# Equivalence tolerance against rcpchgrowth, in each measure's own unit. Tight
# on purpose: this is not "close enough clinically", it is "the same number".
# The two implementations interpolate the same WHO knots, so the only expected
# difference is float noise and interpolation between them.
#
# One value for every measure, derived from the canonical registry rather than
# listed per measure -- a hardcoded {"height": ..., "weight": ...} here is the
# drift M0 exists to prevent, and its guard caught exactly that.
EQUIVALENCE_TOL_UNITS = 0.02
EQUIVALENCE_TOL = {k: EQUIVALENCE_TOL_UNITS for k in MEASURES}


class WhoLmsDataError(ValueError):
    """The WHO LMS files exist but are not usable."""


@dataclass(frozen=True)
class WhoSeries:
    ages: np.ndarray
    l_fn: object
    m_fn: object
    s_fn: object

    def covers(self, age_years: float) -> bool:
        return self.ages[0] <= age_years <= self.ages[-1]

    def at(self, age_years: float) -> tuple[float, float, float]:
        a = float(min(max(age_years, self.ages[0]), self.ages[-1]))
        return float(self.l_fn(a)), float(self.m_fn(a)), float(self.s_fn(a))


def disabled_by_env() -> bool:
    return os.environ.get("PCW_DISABLE_WHO_LMS", "").strip().lower() in ("1", "true", "yes")


def table_path(measure: str, sex: str) -> Path:
    return _DATA_DIR / f"who_{sex}_{measure}.csv"


def _read_one(path: Path) -> WhoSeries:
    ages, ls, ms, ss = [], [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            if not (row.get("age_years") or "").strip():
                continue
            try:
                ages.append(float(row["age_years"]))
                ls.append(float(row["L"]))
                ms.append(float(row["M"]))
                ss.append(float(row["S"]))
            except (KeyError, ValueError) as exc:
                raise WhoLmsDataError(f"{path.name} line {i}: {exc}") from exc

    if len(ages) < 24:
        raise WhoLmsDataError(
            f"{path.name}: only {len(ages)} rows. WHO publishes these at daily or "
            "monthly resolution; a table this sparse would be interpolated across "
            "the steepest part of infant growth."
        )
    order = np.argsort(ages)
    a = np.asarray(ages)[order]
    if np.any(np.diff(a) <= 0):
        raise WhoLmsDataError(f"{path.name}: duplicate ages after sorting")
    m = np.asarray(ms)[order]
    if np.any(m <= 0):
        raise WhoLmsDataError(f"{path.name}: M must be positive at every age")
    s = np.asarray(ss)[order]
    if np.any(s <= 0):
        raise WhoLmsDataError(f"{path.name}: S must be positive at every age")

    # L, M and S interpolated SEPARATELY, then Cole applied -- interpolating the
    # resulting values instead is wrong for a skewed distribution (same reason
    # as iap_lms_reference).
    return WhoSeries(a, PchipInterpolator(a, np.asarray(ls)[order]),
                     PchipInterpolator(a, m), PchipInterpolator(a, s))


@lru_cache(maxsize=1)
def _load() -> Optional[dict[tuple[str, str], WhoSeries]]:
    """Parse every (sex, measure) table, or None when the set is absent."""
    if not _DATA_DIR.exists():
        return None
    present = {(sex, measure) for sex in SEXES for measure in MEASURES
               if table_path(measure, sex).exists()}
    if not present:
        return None
    missing = [f"{sex}/{measure}" for sex in SEXES for measure in MEASURES
               if (sex, measure) not in present]
    if missing:
        raise WhoLmsDataError(
            f"WHO LMS tables are incomplete: missing {missing}. A partial set "
            "would leave some measures on rcpchgrowth and others on these "
            "tables, so the two could disagree with nothing to detect it."
        )
    return {(sex, measure): _read_one(table_path(measure, sex))
            for sex in SEXES for measure in MEASURES}


def reset_cache() -> None:
    """Test seam -- the tables are read once per process in normal operation."""
    _load.cache_clear()
    _equivalence.cache_clear()


# ── the activation gate ─────────────────────────────────────────────────────

def _grid() -> list[float]:
    """Ages the gate compares at.

    Dense where WHO's own data is dense -- infancy changes fastest, so weekly to
    2y and monthly thereafter -- plus every seam boundary and derivative probe
    point explicitly, because those are exactly the values the bridge reads.

    Ages STRICTLY INSIDE a seam window are excluded, and that is a statement
    about the code rather than a convenience: ``who_reference.who_value_at_z``
    does not call the raw lookup there. Inside a window it evaluates a Hermite
    bridge built only from the window's endpoints and their derivatives, so a
    raw value inside the window reaches no caller and no chart. Comparing there
    would fail the gate on numbers nobody can see -- which it did: the two WHO
    layouts inside rcpchgrowth differ by 0.15 cm at the median for girls' height
    at exactly 5.000y, three points out of 11,466, all inside the 4.95-5.2
    handoff window this project already bridges.
    """
    from . import who_reference

    fine = [round(i * 7 / 365.25, 4) for i in range(0, 105)]      # 0-2y weekly
    coarse = [round(2.0 + i / 12, 4) for i in range(0, 205)]      # 2-19y monthly
    eps = who_reference._SEAM_DERIV_EPS

    # Boundary points are kept EXACT rather than rounded with the rest: they are
    # matched against who_reference's own float values, and rounding them to 6dp
    # moves them by ~3e-8, which is enough to miss an identity comparison.
    exact = {e for s in who_reference._SEAMS
             for e in (s.lo, s.hi, s.lo - eps, s.lo + eps, s.hi - eps, s.hi + eps)}
    candidates = {round(a, 6) for a in fine + coarse if AGE_MIN <= a <= AGE_MAX}
    candidates |= {a for a in exact if AGE_MIN <= a <= AGE_MAX}
    return sorted(
        a for a in candidates
        if a in exact or not any(s.lo < a < s.hi for s in who_reference._SEAMS)
    )


_GATE_Z = (-3.0, -1.88079, -1.28155, 0.0, 1.28155, 1.88079, 3.0)


@lru_cache(maxsize=1)
def _equivalence() -> dict:
    """Do our tables reproduce rcpchgrowth's output everywhere the charts read?

    Returns a report rather than raising: an unavailable incumbent is a reason
    the gate cannot be evaluated, not a failure of the data.
    """
    series = _load()
    if series is None:
        return {"ok": False, "reason": "no WHO LMS tables installed", "checked": 0}

    try:
        import rcpchgrowth as rg
    except ImportError:
        return {
            "ok": False, "checked": 0,
            "reason": (
                "rcpchgrowth is not installed, so equivalence cannot be measured. "
                "That is the oracle these tables must match -- install the pinned "
                "version, run the gate, and only then drop the dependency."
            ),
        }

    sex_map = {"boys": rg.MALE, "girls": rg.FEMALE}
    worst: dict[str, float] = {}
    worst_at: dict[str, str] = {}
    checked = 0
    for sex in SEXES:
        for measure in MEASURES:
            method = _measures.MEASURES[measure].who_measurement_method
            for age in _grid():
                if measure == "weight" and age > WEIGHT_MAX_AGE:
                    continue
                for z in _GATE_Z:
                    try:
                        expected = rg.measurement_from_sds(
                            reference=rg.WHO, requested_sds=z,
                            measurement_method=method, sex=sex_map[sex], age=age)
                    except (LookupError, ValueError):
                        continue     # incumbent has no data here; nothing to match
                    got = value_at_z(measure, sex, age, z)
                    if got is None:
                        continue
                    err = abs(got - expected)
                    if measure == "weight" and age > WEIGHT_MAX_AGE:
                        continue
                    if err > worst.get(measure, 0.0):
                        worst[measure] = err
                        worst_at[measure] = f"{sex} @ {age:.3f}y z={z}"
                    checked += 1

    ok = bool(checked) and all(
        worst.get(k, 0.0) <= EQUIVALENCE_TOL[k] for k in MEASURES)
    return {
        "ok": ok,
        "checked": checked,
        "worst": {k: round(v, 5) for k, v in worst.items()},
        "worst_at": worst_at,
        "tolerance": EQUIVALENCE_TOL,
        "reason": "ok" if ok else (
            "our WHO tables do not reproduce rcpchgrowth's output within tolerance"
            if checked else "no comparable points -- the gate proved nothing"
        ),
    }


def lms_available() -> bool:
    """True only when the tables are present, complete, and match the incumbent."""
    if disabled_by_env():
        return False
    try:
        if _load() is None:
            return False
        return bool(_equivalence()["ok"])
    except WhoLmsDataError:
        return False


def lms_status() -> dict:
    """Why the path is or is not live -- surfaced on /api/growth/validate."""
    if disabled_by_env():
        return {"active": False, "reason": "disabled by PCW_DISABLE_WHO_LMS"}
    try:
        loaded = _load()
    except WhoLmsDataError as exc:
        return {"active": False, "files_present": True, "reason": str(exc)}
    if loaded is None:
        return {
            "active": False, "files_present": False,
            "reason": (
                "backend/growth/data/who_lms/ is empty. WHO's published LMS "
                "tables are the last thing standing between this product and "
                "dropping its AGPL-licensed dependency. See "
                "data/WHO-LMS-REQUEST.md."
            ),
        }
    report = _equivalence()
    return {"active": bool(report["ok"]), "files_present": True,
            "reason": report["reason"], "equivalence": report}


# ── the reference itself ────────────────────────────────────────────────────

def covers(measure: str, sex: str, age_years: float) -> bool:
    if measure == "weight" and age_years > WEIGHT_MAX_AGE:
        return False
    series = (_load() or {}).get((sex, measure))
    return series is not None and series.covers(age_years)


def value_at_z(measure: str, sex: str, age_years: float, z: float) -> Optional[float]:
    if not covers(measure, sex, age_years):
        return None
    l, m, s = _load()[(sex, measure)].at(age_years)
    return lms_value_at_z(l, m, s, z)


def z_for_value(measure: str, sex: str, age_years: float, value: float) -> Optional[float]:
    if not covers(measure, sex, age_years) or not (value and value > 0):
        return None
    l, m, s = _load()[(sex, measure)].at(age_years)
    return lms_z_score(value, l, m, s)

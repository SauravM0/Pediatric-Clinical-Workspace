"""WHO reference lookups, delegated entirely to rcpchgrowth's bundled WHO data
and its LMS math (rcpchgrowth.measurement_from_sds / sds_for_measurement).

We do not re-derive or re-store WHO's L,M,S ourselves -- rcpchgrowth already
ships the official WHO 2006 (0-5y) and WHO 2007 (5-19y) reference tables and
the exact Cole LMS calculations the WHO computation guide specifies. This
module only adds three things on top:

1. Sex-name mapping (this app uses "boys"/"girls").
2. WHO weight-for-age being officially undefined beyond 10y.
3. Smoothing two seams internal to rcpchgrowth's own WHO data, found by a
   full-range (0-18y) discontinuity scan across every measure/sex/percentile
   (see tests/growth -- both are covered by permanent regression tests):

   a. Recumbent-length vs. standing-height at 2.0y. WHO measures supine
      length under 2y and standing height from 2y on, and standing height
      reads consistently a little shorter than recumbent length for the same
      child -- so height (and BMI, derived from height) has a real,
      documented step at exactly 2.0y read naively. Measured directly on
      this app's data: girls height median dropped from 86.31cm (age 1.99)
      to 85.75cm (age 2.00) before this fix.
   b. The WHO-2006-child/WHO-2007-child table handoff around 5.08y (WHO's
      under-5 and 5-19y references are two separate published documents;
      rcpchgrowth's own internal tables don't quite agree at the exact
      handoff age). Measured: girls height dropped ~0.31cm and boys BMI
      jumped ~0.08 kg/m^2 in a single 0.005y step at age ~5.08. This one is
      currently invisible in this app's actual chart/scoring output --
      blend.py's WHO/IAP transition window (4.0-5.0y) never queries raw WHO
      at any age other than exactly 4.5 within that range, so it fully masks
      this seam as a side effect -- but it's fixed here anyway so
      who_reference stays correct on its own, independent of how the blend
      window happens to be configured elsewhere.

   Both are bridged the same way (monotone/bounded cubic Hermite, matching
   each side's true local slope) -- the shared machinery lives in hermite.py,
   the same module used for the WHO/IAP handover in blend.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import rcpchgrowth as rg

from . import hermite
from . import who_lms_reference as _who_lms
from .measures import MEASURES, SEAM_2Y_KEYS, SEAM_5Y_KEYS

_SEX_MAP = {"boys": rg.MALE, "girls": rg.FEMALE}
# rcpchgrowth adapter. Derived from the canonical registry (measures.py) rather
# than re-declared, so a newly registered measure cannot silently be missing a
# WHO binding -- test_measure_registry asserts these strings equal the real
# rcpchgrowth constants, and that every WHO-backed measure appears here.
_MEASURE_MAP = {
    m.key: m.who_measurement_method for m in MEASURES.values() if m.who_backed
}

# Small nudges tried (in order) when an age lands in the WHO under-2/over-2
# dataset's own dead zone (observed empirically around 1.999-2.0014y).
_BOUNDARY_NUDGES_YEARS = (0.0, 0.003, -0.003, 0.006, -0.006, 0.01)

_SEAM_DERIV_EPS = 1 / 24  # half-month; well inside each seam window's unambiguous ends


@dataclass(frozen=True)
class _Seam:
    lo: float
    hi: float
    measures: frozenset[str]
    monotonic: bool  # True: value must not decrease (height/weight); False: BMI-style, signed derivatives allowed


# Recumbent-length/standing-height (weight is smooth through 2.0y -- it
# doesn't depend on the length/height measurement convention). Window widened
# to +-0.3y (from an original +-0.1y): the ~0.7cm standing-reads-shorter step
# is a fixed absolute offset, so spreading it over more calendar time directly
# lowers how far the bridge's velocity has to dip below the true ~10-11 cm/yr
# flanking rate to still land on the right endpoint value -- confirmed on this
# app's own data (girls height: +-0.1y dipped to ~5.4 cm/yr, +-0.3y only to
# ~8.8 cm/yr, both well inside monotone_bridge's floor protection either way).
_SEAM_2Y = _Seam(lo=1.7, hi=2.3, measures=SEAM_2Y_KEYS, monotonic=True)
# WHO-2006-child/WHO-2007-child handoff (~5.08y). Applied to all three
# measures since the scan found it on height, weight, and BMI. BMI keeps a
# bounded (non-monotonic-safe) bridge since it can legitimately have a small
# local slope reversal near its adiposity-trough age anyway.
#
# NB: `monotonic` here is a property of the SEAM (which bridge to use across
# it), NOT of the measure -- the 5y handoff uses the bounded bridge for every
# measure, height included. It is therefore deliberately NOT derived from
# Measure.monotonic; only the affected-measure sets come from the registry.
_SEAM_5Y = _Seam(lo=4.95, hi=5.2, measures=SEAM_5Y_KEYS, monotonic=False)

_SEAMS = (_SEAM_2Y, _SEAM_5Y)


def _rg_args(measure: str, sex: str) -> tuple[str, str]:
    return _MEASURE_MAP[measure], _SEX_MAP[sex]


def _raw_who_value_at_z(measure: str, sex: str, age_years: float, z: float) -> float | None:
    # M1.4 strangler seam. Our own WHO LMS tables answer once they are installed
    # AND have reproduced rcpchgrowth's output across a dense grid; until then
    # this falls through to the incumbent. Swapping HERE rather than at the
    # public functions means the seam-smoothing above, and every caller, is
    # unchanged -- the only thing that moves is where the raw LMS comes from.
    if _who_lms.lms_available():
        v = _who_lms.value_at_z(measure, sex, age_years, z)
        if v is not None:
            return v

    measurement_method, rg_sex = _rg_args(measure, sex)
    for nudge in _BOUNDARY_NUDGES_YEARS:
        try:
            return rg.measurement_from_sds(
                reference=rg.WHO,
                requested_sds=z,
                measurement_method=measurement_method,
                sex=rg_sex,
                age=age_years + nudge,
            )
        except (LookupError, ValueError):
            continue
    return None


def _seam_derivative(measure: str, sex: str, anchor_age: float, z: float) -> float:
    v_next = _raw_who_value_at_z(measure, sex, anchor_age + _SEAM_DERIV_EPS, z)
    v_prev = _raw_who_value_at_z(measure, sex, anchor_age - _SEAM_DERIV_EPS, z)
    return (v_next - v_prev) / (2 * _SEAM_DERIV_EPS) if v_next is not None and v_prev is not None else 0.0


def _seam_for(measure: str, age_years: float) -> _Seam | None:
    for seam in _SEAMS:
        if measure in seam.measures and seam.lo < age_years < seam.hi:
            return seam
    return None


def who_value_at_z(measure: str, sex: str, age_years: float, z: float) -> float | None:
    """The measurement at a given z-score, age and sex, per WHO. None if WHO
    has no data at this age/measure (e.g. weight-for-age beyond 10y, or
    outside the 0-19y WHO range). Transparently smooths WHO's own internal
    seams (2.0y and ~5.08y -- see module docstring) for every caller."""
    seam = _seam_for(measure, age_years)
    if seam is None:
        return _raw_who_value_at_z(measure, sex, age_years, z)

    y0 = _raw_who_value_at_z(measure, sex, seam.lo, z)
    y1 = _raw_who_value_at_z(measure, sex, seam.hi, z)
    if y0 is None or y1 is None:
        return _raw_who_value_at_z(measure, sex, age_years, z)

    m0 = _seam_derivative(measure, sex, seam.lo, z)
    m1 = _seam_derivative(measure, sex, seam.hi, z)
    if seam.monotonic:
        bridge = hermite.monotone_bridge(seam.lo, seam.hi, y0, m0, y1, m1)
    else:
        bridge = hermite.bounded_bridge(seam.lo, seam.hi, y0, m0, y1, m1)
    return hermite.hermite_eval(age_years, seam.lo, seam.hi, *bridge)


def who_z_for_value(measure: str, sex: str, age_years: float, value: float) -> float | None:
    """The z-score for an observed measurement, age and sex, per WHO. Uses
    the same seam-smoothed value curve as who_value_at_z (solved numerically
    inside a seam window, since the smoothing there isn't a pure LMS
    transform any more), so a patient's z-score is always the exact inverse
    of what's plotted."""
    if not (value and value > 0):
        return None
    if _seam_for(measure, age_years) is None:
        # Same seam as _raw_who_value_at_z, and they must flip together: a value
        # scored on one model while the curve it sits on is drawn from another
        # is the display-vs-scoring mismatch this project has already fixed once
        # for IAP (audit GC-3/GC-4).
        if _who_lms.lms_available():
            z = _who_lms.z_for_value(measure, sex, age_years, value)
            if z is not None:
                return z

        measurement_method, rg_sex = _rg_args(measure, sex)
        for nudge in _BOUNDARY_NUDGES_YEARS:
            try:
                return rg.sds_for_measurement(
                    reference=rg.WHO,
                    age=age_years + nudge,
                    measurement_method=measurement_method,
                    observation_value=value,
                    sex=rg_sex,
                )
            except (LookupError, ValueError):
                continue
        return None

    from scipy.optimize import brentq

    lo, hi = -4.0, 4.0
    v_lo, v_hi = who_value_at_z(measure, sex, age_years, lo), who_value_at_z(measure, sex, age_years, hi)
    if v_lo is None or v_hi is None:
        return None
    if value <= v_lo:
        return lo
    if value >= v_hi:
        return hi
    return float(brentq(lambda z: who_value_at_z(measure, sex, age_years, z) - value, lo, hi, xtol=1e-6))


def who_has_data(measure: str, sex: str, age_years: float) -> bool:
    return who_value_at_z(measure, sex, age_years, 0.0) is not None

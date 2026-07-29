"""Cole's LMS math, delegated to rcpchgrowth's generic (reference-agnostic)
implementation rather than a locally hand-rolled copy.

rcpchgrowth.global_functions.z_score / measurement_for_z implement exactly:
    Z = ((X/M)^L - 1) / (L*S)              if L != 0
    Z = ln(X/M) / S                        if L == 0
    X = M*(1 + L*S*Z)^(1/L)                if L != 0
    X = M*exp(S*Z)                         if L == 0
which is the CDC/WHO-specified LMS transform. They take raw L, M, S directly,
so the same functions serve both the WHO lookups (where rcpchgrowth already
knows the L,M,S internally) and our locally-fit IAP 2015 L,M,S (where it
doesn't) -- one validated implementation for both reference populations.
"""
from __future__ import annotations

from rcpchgrowth.global_functions import z_score as _z_score
from rcpchgrowth.global_functions import measurement_for_z as _measurement_for_z


def lms_z_score(value: float, l: float, m: float, s: float) -> float | None:
    if not (value and value > 0 and m > 0 and s > 0):
        return None
    return _z_score(l=l, m=m, s=s, observation=value)


def lms_value_at_z(l: float, m: float, s: float, z: float) -> float | None:
    return _measurement_for_z(z=z, l=l, m=m, s=s)


# ── Reportable range (M1.2) ─────────────────────────────────────────────────
# A z-score is mathematically defined for any positive measurement, but past a
# few SD it stops being a meaningful clinical statement and starts being a
# confident-looking artefact of extrapolating a reference beyond the data it was
# built from: a 40 cm height entered for a 6-year-old scores z = -12.9, which
# reads as a precise finding rather than "this input is outside the reference".
#
# The domain functions deliberately keep returning the exact value -- they are
# the honest primitive. This bound is a REPORTING policy applied at the API
# boundary, so the UI can show "outside reference range" instead of a number no
# clinician should act on. +/-5 SD is well outside any real paediatric
# measurement while still leaving genuine extremes (severe malnutrition at -4)
# reportable.
Z_REPORTABLE_MIN = -5.0
Z_REPORTABLE_MAX = 5.0


def clamp_reportable_z(z: float | None) -> tuple[float | None, bool]:
    """(z clamped into the reportable range, whether it was outside it).

    Returns the ORIGINAL z when in range, so ordinary results are untouched.
    """
    if z is None:
        return None, False
    if z < Z_REPORTABLE_MIN:
        return Z_REPORTABLE_MIN, True
    if z > Z_REPORTABLE_MAX:
        return Z_REPORTABLE_MAX, True
    return z, False

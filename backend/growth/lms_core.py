"""Cole's LMS transform (Cole TJ, Green PJ. Stat Med 1992;11:1305-19):

    Z = ((X/M)^L - 1) / (L*S)              if L != 0
    Z = ln(X/M) / S                        if L == 0
    X = M*(1 + L*S*Z)^(1/L)                if L != 0   (None if 1+L*S*Z < 0)
    X = M*exp(S*Z)                         if L == 0

Implemented here rather than imported (step 7). It used to delegate to
rcpchgrowth.global_functions, which made an AGPL-3.0 package a hard runtime
dependency for four lines of published arithmetic. The operations below are
the SAME operations in the SAME order as that implementation, so results are
bit-identical -- tests/growth/test_lms_core_parity.py compares the two across a
dense grid of L, M, S and z whenever rcpchgrowth is installed (it now lives in
requirements-dev.txt only).
"""
from __future__ import annotations

import math


def _z_score(l: float, m: float, s: float, observation: float) -> float:
    if l != 0.0:
        return (((observation / m) ** l) - 1) / (l * s)
    return math.log(observation / m) / s


def _measurement_for_z(z: float, l: float, m: float, s: float) -> float | None:
    if l != 0.0:
        first_step = 1 + (l * s * z)
        if first_step < 0:
            return None      # no real power exists; not a measurement
        return (first_step ** (1 / l)) * m
    return math.exp(s * z) * m


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

"""Smooth WHO <-> IAP 2015 transition over a 4.0-5.0y window.

WHO and IAP are independently-fit statistical models from different source
populations -- IAP's Indian reference runs systematically *lower* than WHO's
international one at these ages (that's the whole clinical point of using it).
That value gap makes a naive "blend the raw values with a smoothstep weight"
construction dangerous: as the weight slides from 0 to 1, the curve is also
sliding *down* from the WHO level to the lower IAP level, and that downward
slide can outrun the underlying growth trend, producing an actual local
DECREASE in the blended curve -- proven on this app's own data: girls height
P3 went from 99.01cm at 5.0y to 98.85cm at 5.2y with the old value-weighted
blend. Impossible clinically (height medians never shrink with age) and
visible on the rendered chart as a flat/dipping segment right in the
transition window.

Fix: bridge the two curves with a 2-point monotone *quintic* Hermite spline
from (4.0y, pure WHO value+slope+curvature) to (5.0y, pure IAP
value+slope+curvature -- IAP's own published table starts here), instead of
linearly blending the two curves' raw values (see hermite.py for the shared
bridge math -- also used for WHO's own internal recumbent-length/
standing-height seam at 2.0y, see who_reference.py). Matching value and slope
alone (a cubic bridge) is C1-continuous but not visually smooth: a cubic's
curvature is rigidly determined by its 4 boundary conditions, so it routinely
has 10-40x the curvature of the curve it's joining onto just outside the
window -- confirmed on this app's own data -- which reads as a visible
kink/elbow. The quintic bridge also matches curvature (true G2 continuity),
eliminating that. Endpoint derivatives/curvatures are each side's TRUE local
values, shrunk only as much as necessary (curvature first, then slope) to
guarantee monotonicity -- matching the real values exactly whenever safe.

WHO and IAP data are NOT merged/mutated anywhere -- this module only combines
their *evaluated* values at read time; who_reference.py and iap_reference.py
remain the two independent, separately-sourced data layers.
"""
from __future__ import annotations

from scipy.optimize import brentq

from . import hermite
from . import iap_reference as iap
from . import who_reference as who

# IAP's published table starts at 5.0 (real, non-extrapolated data, 0.5y steps
# to 18.0) -- so the bridge should hand off exactly there, not at an
# IAP-extrapolated 5.5, or the blended curve misses IAP's own first real data
# point. But just moving the old [4.5, 5.5] window's *end* back to 5.0 (a
# [4.5, 5.0] window) compresses the same WHO<->IAP value gap into half the
# distance, which forces a visibly steeper bridge and fails
# check_edge_slope_continuity -- shrinking the window changes its curvature,
# not just where it lands.
#
# BLEND_LO widened from 4.0 to 3.0y: for weight specifically, WHO and IAP
# disagree so much at these ages (WHO's girls median grows ~2.2 kg/yr through
# age 4; IAP's own median is only 0.3kg higher a full year later at 5.0) that
# even the full monotone_quintic_bridge protection could only hold the
# mid-window velocity at ~0.18 kg/yr in a 1.0y window -- a nearly flat shelf
# that reads as a kink where the curve snaps back to ~2.6 kg/yr right at
# 5.0y. Spreading the same fixed value gap over a 2.0y window instead raises
# the window's own secant much closer to the true flanking velocity (0.33 ->
# 1.27 kg/yr for girls weight, confirmed on this app's own data), so the
# bridge needs far less compression to stay monotonic.
BLEND_LO = 3.0  # years -- below this, pure WHO
BLEND_HI = 5.0  # years -- at/above this, pure IAP (IAP's own real data starts here)
_DERIV_EPS_YEARS = 1 / 24  # half-month, for a local finite-difference derivative

# Height and weight medians are always increasing in real children -- a
# decrease anywhere is a construction artifact, never correct, so it's
# force-guaranteed away. BMI-for-age is different: it has a well-documented
# "adiposity rebound" trough in early-mid childhood -- WHO's own P3 BMI
# curve, unblended, already declines from 13.48 (3.0y) to 13.01 (5.0y) in
# this app's own data -- so a further gentle decline through the 4.0-5.0y
# transition can be the *correct*, real trend continuing, not an artifact,
# and forcing monotonicity there would itself be the distortion.
_REQUIRE_MONOTONIC = {"height": True, "weight": True, "bmi": False}


def blend_weight(age_years: float) -> float:
    """0.0 strictly below the window, 1.0 strictly above it, in between only
    meaningful as "how far through the transition" -- no longer used to
    combine values directly (see module docstring), kept for callers that
    just want to know which regime an age is in."""
    if age_years <= BLEND_LO:
        return 0.0
    if age_years >= BLEND_HI:
        return 1.0
    return (age_years - BLEND_LO) / (BLEND_HI - BLEND_LO)


def _true_derivative(value_fn, age: float, z: float) -> float:
    v_next = value_fn(age + _DERIV_EPS_YEARS, z)
    v_prev = value_fn(age - _DERIV_EPS_YEARS, z)
    return (v_next - v_prev) / (2 * _DERIV_EPS_YEARS) if v_next is not None and v_prev is not None else 0.0


def _true_curvature(value_fn, age: float, z: float) -> float:
    v_next = value_fn(age + _DERIV_EPS_YEARS, z)
    v_here = value_fn(age, z)
    v_prev = value_fn(age - _DERIV_EPS_YEARS, z)
    if v_next is None or v_here is None or v_prev is None:
        return 0.0
    return (v_next - 2 * v_here + v_prev) / (_DERIV_EPS_YEARS ** 2)


def _quintic_bridge(measure: str, sex: str, z: float) -> tuple[float, float, float, float, float, float] | None:
    """(y0, m0, a0, y1, m1, a1) for a 2-point quintic Hermite bridge from
    (BLEND_LO, pure WHO) to (BLEND_HI, pure IAP). Returns None if either
    endpoint is unavailable (e.g. no IAP coverage at all for this measure)."""
    y0 = who.who_value_at_z(measure, sex, BLEND_LO, z)
    y1 = iap.iap_value_at_z(measure, sex, BLEND_HI, z)
    if y0 is None or y1 is None:
        return None
    who_fn = lambda a, zz: who.who_value_at_z(measure, sex, a, zz)
    iap_fn = lambda a, zz: iap.iap_value_at_z(measure, sex, a, zz)
    m0 = _true_derivative(who_fn, BLEND_LO, z)
    m1 = _true_derivative(iap_fn, BLEND_HI, z)
    a0 = _true_curvature(who_fn, BLEND_LO, z)
    a1 = _true_curvature(iap_fn, BLEND_HI, z)

    if not _REQUIRE_MONOTONIC.get(measure, True):
        return hermite.bounded_quintic_bridge(BLEND_LO, BLEND_HI, y0, m0, a0, y1, m1, a1)

    secant = (y1 - y0) / (BLEND_HI - BLEND_LO)
    if secant <= 0:
        # WHO and IAP disagree enough (at the low tail, a real dataset
        # mismatch of a few tenths of a unit -- not biology, unlike BMI above)
        # that even a flat transition can't avoid a zero-or-negative implied
        # trend. Match IAP's arriving value exactly (so there's no
        # discontinuity where the bridge hands off to pure IAP at 5.0y, the
        # side most subsequent clinical use actually reads from) and hold it
        # flat back to 4.0y -- the tiny (sub-1-unit) mismatch is absorbed as a
        # single step entering the window from WHO's side instead of a
        # visible decrease spread across the whole window.
        return y1, 0.0, 0.0, y1, 0.0, 0.0
    return hermite.monotone_quintic_bridge(BLEND_LO, BLEND_HI, y0, m0, a0, y1, m1, a1)


def unified_value_at_z(measure: str, sex: str, age_years: float, z: float) -> float | None:
    """Percentile value at z. Pure WHO below 4.0y, pure IAP above 5.0y (or
    wherever IAP has no coverage, e.g. weight-for-age beyond 10y falls back to
    WHO even inside the nominal IAP range); a monotone quintic Hermite bridge,
    matching each side's true local slope AND curvature whenever safe, for
    ages strictly inside the transition window."""
    if age_years <= BLEND_LO:
        v = who.who_value_at_z(measure, sex, age_years, z)
        return v if v is not None else iap.iap_value_at_z(measure, sex, age_years, z)
    if age_years >= BLEND_HI:
        v = iap.iap_value_at_z(measure, sex, age_years, z)
        return v if v is not None else who.who_value_at_z(measure, sex, age_years, z)

    bridge = _quintic_bridge(measure, sex, z)
    if bridge is None:
        # No IAP coverage at all for this measure inside the window (e.g.
        # weight-for-age beyond WHO's 10y cutoff, before IAP would take over)
        # -- fall back to whichever single source is available.
        vw = who.who_value_at_z(measure, sex, age_years, z)
        return vw if vw is not None else iap.iap_value_at_z(measure, sex, age_years, z)
    return hermite.quintic_eval(age_years, BLEND_LO, BLEND_HI, *bridge)


def unified_z_for_value(measure: str, sex: str, age_years: float, value: float) -> float | None:
    """Inverse of unified_value_at_z: the z-score for an observed measurement.
    Outside the transition window this is exact (WHO's or IAP's own z-score
    function). Inside the window, solved numerically as the exact inverse of
    unified_value_at_z at this age (monotone increasing in z), so a patient's
    plotted point always lands precisely on the curve their z-score implies --
    no separate/inconsistent "blend the z-scores instead" formula that could
    drift from what's actually drawn on the chart."""
    if not (value and value > 0):
        return None
    if age_years <= BLEND_LO:
        z = who.who_z_for_value(measure, sex, age_years, value)
        return z if z is not None else iap.iap_z_for_value(measure, sex, age_years, value)
    if age_years >= BLEND_HI:
        z = iap.iap_z_for_value(measure, sex, age_years, value)
        return z if z is not None else who.who_z_for_value(measure, sex, age_years, value)

    lo, hi = -4.0, 4.0
    v_lo = unified_value_at_z(measure, sex, age_years, lo)
    v_hi = unified_value_at_z(measure, sex, age_years, hi)
    if v_lo is None or v_hi is None:
        return None
    if value <= v_lo:
        return lo
    if value >= v_hi:
        return hi

    def f(z):
        return unified_value_at_z(measure, sex, age_years, z) - value

    return float(brentq(f, lo, hi, xtol=1e-6))


def unified_bmi_cutoffs(sex: str, age_years: float) -> tuple[float, float] | None:
    """IAP/IOTF 23 & 27 adult-equivalent BMI cutoffs. IAP-only concept (WHO
    uses a fixed z threshold instead), so no blend is meaningful below IAP's
    own coverage -- returns None there."""
    return iap.iap_bmi_cutoffs(sex, age_years)

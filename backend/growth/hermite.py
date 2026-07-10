"""Generic 2-point Hermite bridges (cubic and quintic) for splicing together
two piecewise reference functions that don't naturally agree at their shared
boundary -- originally built for the WHO/IAP 2015 handover at 4.0-5.0y (see
blend.py), and reused as-is for WHO's own internal recumbent-length-vs-
standing-height seam at 2.0y (see who_reference.py).

Matching value and slope (the cubic bridge) is necessary but not sufficient
for a visually smooth join: a cubic Hermite segment's curvature is rigidly
determined by its 4 boundary conditions, with no free parameter left to also
match curvature -- so even a "perfectly smooth" (C1) cubic bridge routinely
has 10-40x the curvature of the reference curve it's joining onto just
outside the window, which reads as a visible kink/elbow despite having
matching value and slope. Confirmed on this app's own data (girls weight:
curvature -3.7 just inside the window vs -0.5 just outside). The quintic
bridge below also matches *curvature* (the 2nd derivative) at both
endpoints -- true G2 continuity -- eliminating that visible elbow.
"""
from __future__ import annotations

import numpy as np


def hermite_eval(t_age: float, x0: float, x1: float, y0: float, m0: float, y1: float, m1: float) -> float:
    """Evaluate the Hermite cubic at age t_age, for a segment spanning
    [x0, x1] with values/derivatives (y0, m0) and (y1, m1) at the ends."""
    h = x1 - x0
    t = (t_age - x0) / h
    t2, t3 = t * t, t * t * t
    h00 = 2 * t3 - 3 * t2 + 1
    h10 = t3 - 2 * t2 + t
    h01 = -2 * t3 + 3 * t2
    h11 = t3 - t2
    return h00 * y0 + h10 * h * m0 + h01 * y1 + h11 * h * m1


def _deriv_at_t(t: float, y0: float, m0: float, y1: float, m1: float, h: float) -> float:
    t2 = t * t
    h00d = 6 * t2 - 6 * t
    h10d = 3 * t2 - 4 * t + 1
    h01d = -6 * t2 + 6 * t
    h11d = 3 * t2 - 2 * t
    return h00d * y0 + h10d * h * m0 + h01d * y1 + h11d * h * m1


def _min_derivative(y0: float, m0: float, y1: float, m1: float, h: float) -> float:
    """Minimum of the segment's derivative w.r.t. age, found by dense
    sampling -- simpler and more reliable than the closed-form Fritsch-Carlson
    monotone region, which a naive per-endpoint clip only approximates."""
    ts = np.linspace(0.0, 1.0, 41)
    derivs = np.array([_deriv_at_t(t, y0, m0, y1, m1, h) for t in ts]) / h
    return float(derivs.min())


def monotone_bridge(x0: float, x1: float, y0: float, m0: float, y1: float, m1: float, min_slope_frac: float = 0.5) -> tuple[float, float, float, float]:
    """Return (y0, m0', y1, m1') with the derivatives shrunk (in lockstep,
    preserving their ratio) only as much as necessary to keep the Hermite
    segment's derivative from dropping below min_slope_frac * secant
    anywhere in the middle. Matches the true m0/m1 exactly whenever that's
    already safe.

    Bare non-negativity (min derivative >= 0) is not enough: when both true
    endpoint slopes sit well above the secant (e.g. the WHO recumbent-length/
    standing-height seam at 2.0y, where real growth velocity on both sides is
    ~10-11 cm/yr but the seam's own secant is ~7 cm/yr because of the ~0.7cm
    standing-reads-shorter step folded into the window), a cubic segment
    that starts and ends at those slopes must dip well *below* the secant in
    the middle to make the endpoints match -- while staying >= 0 the whole
    time. Confirmed on this app's own data: girls height velocity at this
    seam went 10.9 -> ~6.8 (a mid-window trough) -> 10.3 cm/yr, passing the
    old >= -1e-9 check on its very first (unclipped) iteration while still
    reading as a sharp dip-then-snap-back kink on the rendered chart. Same
    min_slope_frac=0.5 threshold as monotone_quintic_bridge's own fallback
    stage, for consistency between the two bridges."""
    h = x1 - x0
    secant = (y1 - y0) / h
    if secant <= 0:
        return y0, 0.0, y1, 0.0
    floor = min_slope_frac * secant
    m0 = min(max(m0, 0.0), 3 * secant)
    m1 = min(max(m1, 0.0), 3 * secant)
    for _ in range(40):
        if _min_derivative(y0, m0, y1, m1, h) >= floor:
            break
        m0 *= 0.8
        m1 *= 0.8
    return y0, m0, y1, m1


def bounded_bridge(x0: float, x1: float, y0: float, m0: float, y1: float, m1: float, bound_mult: float = 5.0, floor: float = 0.05) -> tuple[float, float, float, float]:
    """Like monotone_bridge, but for quantities that are allowed to move in
    either direction (e.g. BMI's real adiposity-rebound trough) -- keeps the
    true signed derivatives, only bounding their magnitude against a
    pathological blow-up so the bridge stays one graceful curve rather than
    an oscillation."""
    h = x1 - x0
    secant = (y1 - y0) / h
    scale = max(abs(secant), floor)
    m0 = max(min(m0, bound_mult * scale), -bound_mult * scale)
    m1 = max(min(m1, bound_mult * scale), -bound_mult * scale)
    return y0, m0, y1, m1


# ---------------------------------------------------------------------------
# Quintic (degree-5) Hermite: matches value, slope, AND curvature at both
# ends -- the G2-continuous upgrade to the cubic bridge above.
# ---------------------------------------------------------------------------

def quintic_eval(t_age: float, x0: float, x1: float, y0: float, m0: float, a0: float, y1: float, m1: float, a1: float) -> float:
    """Evaluate the quintic Hermite at age t_age, for a segment spanning
    [x0, x1] with value/slope/curvature (y0, m0, a0) and (y1, m1, a1) at the
    ends. m0/m1 are d(value)/d(age); a0/a1 are d^2(value)/d(age)^2 -- real
    units (e.g. cm/year, cm/year^2), scaled to the unit interval internally."""
    h = x1 - x0
    t = (t_age - x0) / h
    t2, t3, t4, t5 = t * t, t ** 3, t ** 4, t ** 5
    h00 = 1 - 10 * t3 + 15 * t4 - 6 * t5
    h10 = t - 6 * t3 + 8 * t4 - 3 * t5
    h20 = 0.5 * t2 - 1.5 * t3 + 1.5 * t4 - 0.5 * t5
    h01 = 10 * t3 - 15 * t4 + 6 * t5
    h11 = -4 * t3 + 7 * t4 - 3 * t5
    h21 = 0.5 * t3 - t4 + 0.5 * t5
    return (y0 * h00 + (m0 * h) * h10 + (a0 * h * h) * h20
            + y1 * h01 + (m1 * h) * h11 + (a1 * h * h) * h21)


def _min_quintic_derivative(y0: float, m0: float, a0: float, y1: float, m1: float, a1: float, h: float) -> float:
    """Minimum of the segment's derivative w.r.t. age, found by dense
    sampling of the *values* (central differences) -- simplest and most
    reliable way to check monotonicity for the quintic bridge."""
    ts = np.linspace(0.0, 1.0, 81)
    ages = ts * h
    vals = np.array([
        y0 * (1 - 10*t**3 + 15*t**4 - 6*t**5) + (m0*h) * (t - 6*t**3 + 8*t**4 - 3*t**5)
        + (a0*h*h) * (0.5*t**2 - 1.5*t**3 + 1.5*t**4 - 0.5*t**5)
        + y1 * (10*t**3 - 15*t**4 + 6*t**5) + (m1*h) * (-4*t**3 + 7*t**4 - 3*t**5)
        + (a1*h*h) * (0.5*t**3 - t**4 + 0.5*t**5)
        for t in ts
    ])
    derivs = np.diff(vals) / np.diff(ages)
    return float(derivs.min())


def monotone_quintic_bridge(x0: float, x1: float, y0: float, m0: float, a0: float, y1: float, m1: float, a1: float, min_slope_frac: float = 0.5) -> tuple[float, float, float, float, float, float]:
    """Like monotone_bridge, but for the quintic (curvature-matching) bridge.
    Shrinks the curvature terms (a0, a1) toward zero first -- preserving the
    true value/slope match, which is the more important constraint -- and
    only if the segment is *still* not "smooth enough" at zero curvature does
    it fall back to also shrinking the slopes, exactly as the cubic bridge
    does. Matches the true a0/a1 (and m0/m1) exactly whenever that's already
    safe.

    "Smooth enough" is deliberately stricter than bare non-negativity
    (min derivative >= 0): true endpoint curvature is often strongly
    decelerating on both sides at once (real height/weight growth velocity
    genuinely slows with age), and matching both exactly can pinch the
    segment's derivative down to near-zero in the middle without ever
    actually going negative -- passing the old >= -1e-9 check on its very
    first (unshrunk) iteration while still reading as an obvious flat
    "shelf" on the rendered chart. Confirmed on this app's own data: boys
    height P3 dropped from a true WHO growth rate of 5.9 cm/yr to a
    mid-window low of 2.1 cm/yr (a visible plateau in the SVG path), and
    girls height P3 dropped to 0.03 cm/yr -- an almost perfectly flat
    segment -- even though both endpoints and the whole segment were
    "monotone" by the old, purely non-negative definition. Requiring the
    minimum derivative to stay above min_slope_frac * secant (not just >= 0)
    keeps damping curvature -- and, if that's not enough, slope -- until the
    transition's velocity stays reasonably close to the straight-line trend
    throughout, not just at the two ends."""
    h = x1 - x0
    secant = (y1 - y0) / h
    if secant <= 0:
        return y0, 0.0, 0.0, y1, 0.0, 0.0
    floor = min_slope_frac * secant
    m0 = min(max(m0, 0.0), 3 * secant)
    m1 = min(max(m1, 0.0), 3 * secant)
    for _ in range(40):
        if _min_quintic_derivative(y0, m0, a0, y1, m1, a1, h) >= floor:
            return y0, m0, a0, y1, m1, a1
        a0 *= 0.75
        a1 *= 0.75
    # Zero curvature still isn't enough -- same territory as the cubic
    # bridge's fallback (a genuine, large WHO/IAP disagreement); shrink the
    # slopes the same way monotone_bridge does, with curvature left at 0.
    # Shrinking m0/m1 toward 0 drives the segment toward the straight secant
    # line (whose derivative is exactly `secant` everywhere), so this always
    # converges below `floor` well within the iteration budget.
    for _ in range(40):
        if _min_quintic_derivative(y0, m0, 0.0, y1, m1, 0.0, h) >= floor:
            break
        m0 *= 0.8
        m1 *= 0.8
    return y0, m0, 0.0, y1, m1, 0.0


def _direction_changes_and_overshoot(y0: float, m0: float, a0: float, y1: float, m1: float, a1: float, h: float) -> tuple[int, float]:
    """Dense-sample the segment and report (sign changes in its
    direction, overshoot beyond the [y0, y1] span) -- the same measure
    check_bmi_smoothness uses, so a bridge built to satisfy this is
    guaranteed to pass that check, not just approximate it."""
    ts = np.linspace(0.0, 1.0, 81)
    vals = np.array([
        y0 * (1 - 10*t**3 + 15*t**4 - 6*t**5) + (m0*h) * (t - 6*t**3 + 8*t**4 - 3*t**5)
        + (a0*h*h) * (0.5*t**2 - 1.5*t**3 + 1.5*t**4 - 0.5*t**5)
        + y1 * (10*t**3 - 15*t**4 + 6*t**5) + (m1*h) * (-4*t**3 + 7*t**4 - 3*t**5)
        + (a1*h*h) * (0.5*t**3 - t**4 + 0.5*t**5)
        for t in ts
    ])
    diffs = np.diff(vals)
    nonzero = diffs[diffs != 0]
    sign_changes = int(np.sum(np.diff(np.sign(nonzero)) != 0)) if len(nonzero) else 0
    lo, hi = min(y0, y1), max(y0, y1)
    overshoot = float(max(lo - vals.min(), vals.max() - hi, 0))
    return sign_changes, overshoot


def bounded_quintic_bridge(x0: float, x1: float, y0: float, m0: float, a0: float, y1: float, m1: float, a1: float, bound_mult: float = 5.0, floor: float = 0.05, wiggle_tolerance: float = 0.05) -> tuple[float, float, float, float, float, float]:
    """Quintic counterpart of bounded_bridge, for quantities allowed to move
    in either direction (BMI): keeps the true signed slope and curvature,
    bounding their magnitude against a pathological blow-up, and -- since a
    quintic has more shape freedom than a cubic -- also damping curvature
    (toward zero, same lockstep-shrink pattern as monotone_quintic_bridge)
    if that freedom produces more than one real direction change (an actual
    S-wiggle, not BMI's single legitimate adiposity-rebound trough)."""
    h = x1 - x0
    secant = (y1 - y0) / h
    scale = max(abs(secant), floor)
    m0 = max(min(m0, bound_mult * scale), -bound_mult * scale)
    m1 = max(min(m1, bound_mult * scale), -bound_mult * scale)
    a_scale = max(abs(a0), abs(a1), floor)
    a_bound = bound_mult * a_scale
    a0 = max(min(a0, a_bound), -a_bound)
    a1 = max(min(a1, a_bound), -a_bound)

    for _ in range(20):
        sign_changes, overshoot = _direction_changes_and_overshoot(y0, m0, a0, y1, m1, a1, h)
        if sign_changes <= 1 or overshoot <= wiggle_tolerance:
            return y0, m0, a0, y1, m1, a1
        a0 *= 0.75
        a1 *= 0.75
    # Zero curvature still isn't enough -- this happens when both endpoint
    # slopes share a sign that disagrees with the secant (e.g. BMI rising at
    # both window edges while the net change across the window is a decline),
    # which geometrically forces a second direction change no matter the
    # curvature. Damp the slopes too, same lockstep shrink as
    # monotone_quintic_bridge's own second stage.
    for _ in range(20):
        sign_changes, overshoot = _direction_changes_and_overshoot(y0, m0, 0.0, y1, m1, 0.0, h)
        if sign_changes <= 1 or overshoot <= wiggle_tolerance:
            break
        m0 *= 0.8
        m1 *= 0.8
    return y0, m0, 0.0, y1, m1, 0.0

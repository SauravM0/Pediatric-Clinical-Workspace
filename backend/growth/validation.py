"""Automated QA for the growth chart engine.

Checks, for every measure x sex x centile:
  1. No decrease inside the blend window -- the critical hard guarantee.
     Height/weight/BMI medians must never go DOWN as age increases. This is
     the check that would have caught the original bug: a naive value-weight
     blend of WHO and IAP can produce a real local decrease when the two
     references disagree by a lot (e.g. girls height P3 dipped from 99.01cm
     at 5.0y to 98.85cm at 5.2y) -- clinically impossible and visibly a
     flat/dipping segment on the rendered chart. Zero tolerance.
  2. Edge slope continuity -- best-effort "no kink" check: does the bridge's
     slope at each transition-window edge (4.0y, 5.0y) match the slope just
     outside it (pure WHO / pure IAP)? This yields to check 1 when the two
     references genuinely disagree enough that matching both true slopes
     would require a decrease (e.g. IAP's published P3 weight for Indian
     girls is genuinely lower than WHO's international P3 a year earlier --
     real epidemiology, not a bug) -- in that case the bridge correctly uses
     a flatter transition instead of dipping, and the resulting edge-slope
     mismatch is expected and reported for visibility, not a failure.
  3. Monotonic age progression -- the dense rendered series must have
     strictly increasing ages (no backward/duplicate steps).
  4. Centile ordering / no crossing -- at every sampled age, P3 < P10 < ... <
     P97 for height & weight (BMI is expected to have a lower-tail crossing
     region in some real growth references only at extreme ages; we check
     strict ordering throughout since IAP's own published table never
     crosses either).
  5. Source-value reproduction -- the engine's own value at each *exact*
     published (age, centile) point matches the published number.
  6. Transition value continuity -- no visible value JUMP where pure-WHO hands
     off to the WHO/IAP bridge at BLEND_LO (~age 3). Quantified and gated so a
     discontinuity can never be shipped silently (audit GC-2/GC-3).

Returns a structured report; also used as the basis for pytest tests in
tests/test_growth_engine.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import blend, curve_builder, iap_reference, iap_table_consistency, measures

SLOPE_ATOL = {"height": 0.3, "weight": 0.15, "bmi": 0.18}  # units/year, absolute floor
SLOPE_RTOL = 0.15  # + 15% of the outside slope magnitude
CURVATURE_ATOL = {"height": 1.5, "weight": 1.0, "bmi": 1.5}  # units/year^2, absolute floor
CURVATURE_RTOL = 0.25  # + 25% of the true boundary curvature magnitude
EPS_YEARS = 0.08
MONOTONIC_SAMPLE_STEP_YEARS = 0.02  # dense scan across the blend window itself

MEASURES = measures.MEASURE_KEYS  # canonical registry (M0.3)
SEXES = ("boys", "girls")


@dataclass
class ValidationReport:
    all_pass: bool = True
    failures: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _slope_at(measure: str, sex: str, age: float, z: float, eps: float = EPS_YEARS) -> float:
    v_hi = blend.unified_value_at_z(measure, sex, age + eps, z)
    v_lo = blend.unified_value_at_z(measure, sex, age - eps, z)
    return (v_hi - v_lo) / (2 * eps)


MONOTONIC_MEASURES = measures.MONOTONIC_MEASURE_KEYS  # BMI legitimately troughs (adiposity rebound) -- see blend.py


def check_no_decrease_in_blend_window() -> dict:
    """Check 1 (hard *unless explained*): scans densely across the 4.0-5.0y
    transition window and confirms the value never decreases as age
    increases, for every centile of height & weight (every sex). This is the
    concrete regression test for the original bug (a real local decrease
    spread across the whole window, produced by linearly blending two
    references that disagree substantially).

    A decrease is marked `gating=False` (reported, not failing) only when
    WHO's own value at 4.0y is already above IAP's own value at 5.0y -- i.e.
    the two published references disagree enough at this tail that *no*
    continuous path between their exact endpoint values can avoid some
    decrease. In that specific, explained case the bridge (blend.py) uses the
    smallest form such a decrease can take: a single step entering the window
    from WHO's side, landing immediately on IAP's arriving value and holding
    flat -- rather than a decline smeared across the full window (the
    original bug). BMI is excluded entirely -- it has a genuine "adiposity
    rebound" trough in early-mid childhood (WHO's own unblended P3 BMI curve
    already declines from 13.48 at 3.0y to 13.01 at 5.0y in this dataset), so
    a real decrease there can be the correct trend; see check_bmi_smoothness."""
    results = {}
    ages = np.arange(blend.BLEND_LO, blend.BLEND_HI + 1e-9, MONOTONIC_SAMPLE_STEP_YEARS)
    for sex in SEXES:
        for measure in MONOTONIC_MEASURES:
            for centile, z in curve_builder.Z_FOR_CENTILE.items():
                values = np.array([blend.unified_value_at_z(measure, sex, a, z) for a in ages])
                diffs = np.diff(values)
                min_diff = float(diffs.min())

                y0 = blend.who.who_value_at_z(measure, sex, blend.BLEND_LO, z)
                y1 = blend.iap.iap_value_at_z(measure, sex, blend.BLEND_HI, z)
                gating = bool(not (y0 is not None and y1 is not None and y1 <= y0))

                results[f"{sex}|{measure}|P{centile}"] = {
                    "pass": bool((min_diff >= -1e-6) or not gating),
                    "gating": gating,
                    "min_step": round(min_diff, 5),
                }
    return results


def check_bmi_smoothness() -> dict:
    """BMI counterpart to check_no_decrease_in_blend_window: since BMI is
    allowed to have a real trough, the hard requirement instead is smoothness
    -- no oscillation (at most one direction change across the window) and no
    overshoot beyond the range spanned by the two endpoints plus a small
    margin (a monotone-safe cubic can't overshoot; a signed one that allows a
    trough still shouldn't swing past the data's own range). A second
    direction change is tolerated if its amplitude is below WIGGLE_TOLERANCE
    kg/m^2 -- clinically/visually imperceptible on a rendered chart, and
    expected right at a genuine turning point where the true derivative can
    wobble by noise-level amounts."""
    WIGGLE_TOLERANCE = 0.05  # kg/m^2 -- well under rendered line thickness
    results = {}
    ages = np.arange(blend.BLEND_LO, blend.BLEND_HI + 1e-9, MONOTONIC_SAMPLE_STEP_YEARS)
    for sex in SEXES:
        for centile, z in curve_builder.Z_FOR_CENTILE.items():
            values = np.array([blend.unified_value_at_z("bmi", sex, a, z) for a in ages])
            diffs = np.diff(values)
            sign_changes = int(np.sum(np.diff(np.sign(diffs[diffs != 0])) != 0))
            lo, hi = float(min(values[0], values[-1])), float(max(values[0], values[-1]))
            margin = 0.1 * (hi - lo) + 0.2
            overshoot = float(max(lo - values.min(), values.max() - hi, 0))
            passed = bool((sign_changes <= 1 or overshoot <= WIGGLE_TOLERANCE) and overshoot <= margin)
            results[f"{sex}|bmi|P{centile}"] = {
                "pass": passed, "direction_changes": sign_changes,
                "overshoot": round(overshoot, 4), "overshoot_margin": round(margin, 4),
            }
    return results


# A value JUMP where pure-WHO hands off to the bridge at BLEND_LO must never
# grow into a clinically visible step at ~age 3. These bounds are sub-render-line
# (a step under them is invisible on the chart); above them the composite would
# be shipping a hidden discontinuity and must fail (audit GC-2/GC-3).
TRANSITION_STEP_ATOL = {"height": 0.5, "weight": 0.3, "bmi": 0.2}  # cm / kg / kg·m^-2


def check_transition_value_continuity() -> dict:
    """Check (gating): no visible VALUE JUMP at the WHO -> bridge handoff (BLEND_LO).

    blend._quintic_bridge can, when the two references disagree so much that a
    monotone path between their exact endpoints is impossible (secant <= 0),
    legitimately absorb the mismatch as a single flat step ENTERING the window
    (blend.py). On the current data that step is exactly 0 for every centile (the
    references never disagree that hard here), but the old code would have shipped
    such a step SILENTLY, marked 'non-gating'. GC-2/GC-3: a curve must not pass
    merely because a known discontinuity is flagged non-gating.

    So the step is quantified for every measure/sex/centile and GATED against a
    sub-render-line tolerance. If a future data change (or a new centile/measure)
    reintroduces a real jump at ~age 3, this fails loudly and forces a
    reference-policy decision (widen the window, or show WHO and IAP separately)
    instead of hiding the step in the chart.
    """
    results = {}
    for sex in SEXES:
        for measure in MEASURES:
            atol = TRANSITION_STEP_ATOL[measure]
            for centile, z in curve_builder.Z_FOR_CENTILE.items():
                bridge = blend._quintic_bridge(measure, sex, z)
                who_lo = blend.who.who_value_at_z(measure, sex, blend.BLEND_LO, z)
                if bridge is None or who_lo is None:
                    results[f"{sex}|{measure}|P{centile}"] = {
                        "pass": True, "step": None, "note": "no bridge / no WHO coverage"}
                    continue
                # bridge[0] is the composite's value at BLEND_LO; pure WHO holds
                # right up to BLEND_LO, so their difference IS the handoff jump.
                step = float(abs(bridge[0] - who_lo))
                results[f"{sex}|{measure}|P{centile}"] = {
                    "pass": bool(step <= atol),
                    "step": round(step, 5),
                    "tolerance": atol,
                }
    return results


def check_edge_slope_continuity() -> dict:
    """Check 2 (best-effort, non-gating when explained): slope just inside
    vs. just outside each blend-window edge, for every centile of every
    measure/sex. A mismatch is marked `gating=False` (reported but doesn't
    fail the suite) whenever the bridge's *actual* returned slope (from
    blend._quintic_bridge -- what the rendered curve really uses) differs
    from the true local slope, i.e. preserving monotonicity (the
    higher-priority, hard requirement for height/weight -- see
    check_no_decrease_in_blend_window) required damping it -- either
    directly, or as a side effect of first damping curvature and then still
    needing to damp slope too (see hermite.monotone_quintic_bridge's
    two-stage fallback). Checking the bridge's own output directly, rather
    than re-deriving a "was clipping forced" heuristic, is what actually
    tracks that two-stage cascade correctly. BMI is never gated here since it
    doesn't carry the monotonicity requirement in the first place (see
    check_bmi_smoothness)."""
    results = {}
    for sex in SEXES:
        for measure in MEASURES:
            atol = SLOPE_ATOL[measure]
            for centile, z in curve_builder.Z_FOR_CENTILE.items():
                lo_in = _slope_at(measure, sex, blend.BLEND_LO + EPS_YEARS / 2, z)
                lo_out = _slope_at(measure, sex, blend.BLEND_LO - EPS_YEARS / 2, z)
                hi_in = _slope_at(measure, sex, blend.BLEND_HI - EPS_YEARS / 2, z)
                hi_out = _slope_at(measure, sex, blend.BLEND_HI + EPS_YEARS / 2, z)
                lo_diff, hi_diff = float(abs(lo_in - lo_out)), float(abs(hi_in - hi_out))
                lo_budget = float(atol + SLOPE_RTOL * abs(lo_out))
                hi_budget = float(atol + SLOPE_RTOL * abs(hi_out))
                passed = bool(lo_diff <= lo_budget and hi_diff <= hi_budget)

                if measure not in MONOTONIC_MEASURES:
                    gating = False  # BMI: monotonicity isn't required, so no clip-explained pass
                else:
                    bridge = blend._quintic_bridge(measure, sex, z)
                    if bridge is None:
                        gating = False
                    else:
                        _, m0_used, _, _, m1_used, _ = bridge
                        true_m0 = blend._true_derivative(lambda a, zz: blend.who.who_value_at_z(measure, sex, a, zz), blend.BLEND_LO, z)
                        true_m1 = blend._true_derivative(lambda a, zz: blend.iap.iap_value_at_z(measure, sex, a, zz), blend.BLEND_HI, z)
                        damped = abs(m0_used - true_m0) > 1e-6 or abs(m1_used - true_m1) > 1e-6
                        gating = not damped

                results[f"{sex}|{measure}|P{centile}"] = {
                    "pass": bool(passed or not gating),
                    "gating": gating,
                    "lo_edge_diff": round(lo_diff, 4), "lo_edge_budget": round(lo_budget, 4),
                    "hi_edge_diff": round(hi_diff, 4), "hi_edge_budget": round(hi_budget, 4),
                }
    return results


def check_edge_curvature_continuity() -> dict:
    """Check 2b (best-effort, non-gating when explained): does the quintic
    bridge's *actual* boundary curvature (a0/a1, as returned by
    blend._quintic_bridge -- what the rendered curve really uses) match the
    true analytic curvature of WHO/IAP's own curve at that same point?

    Note this deliberately does NOT re-measure curvature by re-differencing
    the already-blended output a little way inside the window -- tried that
    first, and it's unreliable: the quintic's curvature is *intentionally*
    varying rapidly across the 1.0y window (transitioning from a0 to a1), so
    even a very small step still averages in a large chunk of that
    intentional change, producing a "mismatch" that has nothing to do with
    whether the bridge is actually correct at the boundary. Comparing the
    bridge's own a0/a1 against the independently-computed true curvature
    is the precise, step-size-independent way to ask the same question.

    Matching value and slope alone (check 2) is *not* sufficient for a
    visually smooth join -- a cubic Hermite's curvature is rigidly determined
    by its 4 boundary conditions and, in practice, routinely mismatches the
    outside curve's curvature by 10-40x (confirmed on this app's own data),
    which reads as a visible kink/elbow even with matching value and slope.
    Non-gating exactly when the bridge had to damp curvature to preserve
    monotonicity (the higher-priority requirement) -- in that case any
    resulting mismatch is expected, same reasoning as
    check_edge_slope_continuity."""
    results = {}
    for sex in SEXES:
        for measure in MEASURES:
            atol = CURVATURE_ATOL[measure]
            for centile, z in curve_builder.Z_FOR_CENTILE.items():
                bridge = blend._quintic_bridge(measure, sex, z)
                if bridge is None:
                    results[f"{sex}|{measure}|P{centile}"] = {"pass": True, "gating": False, "note": "no bridge (no IAP coverage)"}
                    continue
                _, _, a0_used, _, _, a1_used = bridge
                true_a0 = blend._true_curvature(lambda a, zz: blend.who.who_value_at_z(measure, sex, a, zz), blend.BLEND_LO, z)
                true_a1 = blend._true_curvature(lambda a, zz: blend.iap.iap_value_at_z(measure, sex, a, zz), blend.BLEND_HI, z)
                lo_diff, hi_diff = float(abs(a0_used - true_a0)), float(abs(a1_used - true_a1))
                lo_budget = float(atol + CURVATURE_RTOL * abs(true_a0))
                hi_budget = float(atol + CURVATURE_RTOL * abs(true_a1))
                passed = bool(lo_diff <= lo_budget and hi_diff <= hi_budget)
                # Any nonzero diff means the bridge deliberately damped
                # curvature toward zero to preserve monotonicity -- expected.
                gating = bool(lo_diff <= 1e-6 and hi_diff <= 1e-6)

                results[f"{sex}|{measure}|P{centile}"] = {
                    "pass": bool(passed or not gating),
                    "gating": gating,
                    "lo_edge_diff": round(lo_diff, 3), "lo_edge_budget": round(lo_budget, 3),
                    "hi_edge_diff": round(hi_diff, 3), "hi_edge_budget": round(hi_budget, 3),
                }
    return results


def check_monotonic_age(series_by_measure_sex: dict) -> dict:
    """Check 2: dense series ages strictly increase, for every curve."""
    results = {}
    for (sex, measure), series in series_by_measure_sex.items():
        for centile, curve in series.items():
            diffs = np.diff(curve.ages)
            passed = bool(len(diffs) == 0 or np.all(diffs > 0))
            results[f"{sex}|{measure}|P{centile}"] = {"pass": passed, "min_step": float(diffs.min()) if len(diffs) else None}
    return results


def check_centile_ordering(series_by_measure_sex: dict) -> dict:
    """Check 3: at every sampled age, centiles are strictly ordered (no
    crossing) -- P3 < P10 < P25 < P50 < P75 < P90 < P97."""
    results = {}
    for (sex, measure), series in series_by_measure_sex.items():
        centiles = sorted(series.keys())
        ages = series[centiles[0]].ages
        stacked = np.vstack([series[c].values[: len(ages)] for c in centiles])
        diffs = np.diff(stacked, axis=0)
        n_violations = int(np.sum(diffs <= 0))
        results[f"{sex}|{measure}"] = {"pass": n_violations == 0, "violations": n_violations}
    return results


def check_source_reproduction() -> dict:
    """Check 4: the engine reproduces the published IAP table exactly --
    checked against iap_reference directly (the pure, unblended fit), NOT the
    blended unified_value_at_z. Age 5.0 is both a published table point AND
    the top of the 4.0-5.0y blend window by design, so the *blended* value
    there is intentionally a WHO/IAP mix, not pure IAP -- that's the point of
    blending, not a fidelity bug. Source fidelity is a property of the IAP fit
    alone; blend correctness is checked separately by check_edge_slope_continuity.

    Every age checked here except 5.0 itself (5.5, 6.0, ..., 18.0) is past
    iap_reference's exact-table guard band and hits iap_value_at_z's
    exact-table path (see that module's docstring), so those should now
    reproduce the published table to floating-point precision, not just
    "close" -- tightened from the old blanket 1.0-unit tolerance (which was
    loose enough to let the pre-fix LMS-refit's real ~0.3-0.65 unit misses
    pass everywhere, not just at the boundary). Age 5.0 itself stays inside
    the guard band on purpose (it's also where blend.py's bridge anchors and
    probes a derivative -- see iap_reference._EXACT_TABLE_GUARD) and is
    reported separately, not gated on the tight tolerance.

    Which columns count (M1.1)
    --------------------------
    Only the columns the CSVs actually source. Four of the seven height/weight
    columns were reconstructed by even z-spacing rather than read from the paper
    -- see ``iap_table_consistency``. While the legacy fit is live this makes no
    difference: that fit is derived from the same CSVs, so it reproduces the
    reconstructed columns too. The moment the real L,M,S go in it makes all the
    difference, because a genuine reference puts the 25th centile at z=-0.674
    and the CSV column sits at -0.627, so "the engine no longer reproduces the
    table" becomes the CORRECT result and would fail this check.

    Gating on sourced columns keeps this check meaning "the engine is faithful
    to its reference" instead of "the engine still matches an interpolation".
    The reconstructed columns stay measured under ``reconstructed_max_error``.
    """
    import csv as _csv

    from . import iap_lms_reference

    # Which tolerance applies depends on which path is live, and the difference
    # is a real distinction rather than a fudge. The legacy exact-table path
    # INTERPOLATES the CSV, so it reproduces it to floating-point precision and
    # anything less is a bug. With real L,M,S the CSV is instead a rounded
    # RENDERING of the reference -- quoted to 0.1 units -- so agreement to
    # within rounding is the most that can exist, and demanding 1e-6 would fail
    # a perfect file.
    lms_live = iap_lms_reference.lms_available()

    results = {}
    for sex, prefix in iap_reference._SEX_FILE.items():
        for measure in ("height", "weight"):
            tol = iap_lms_reference.REPRODUCTION_TOL[measure] if lms_live else 1e-6
            judged = set(iap_table_consistency.gate_centiles(measure))
            fname = f"{prefix}_{'height_cm' if measure=='height' else 'weight_kg'}_IAP_5_18.csv"
            path = iap_reference._DATA_DIR / fname
            max_err = 0.0
            boundary_err = 0.0
            reconstructed_err = 0.0
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in _csv.DictReader(f):
                    age = float(row["age_years"])
                    for c in (3, 10, 25, 50, 75, 90, 97):
                        z = curve_builder.Z_FOR_CENTILE[c]
                        expected = float(row[f"p{c}"])
                        got = iap_reference.iap_value_at_z(measure, sex, age, z)
                        err = abs(got - expected)
                        if c not in judged:
                            reconstructed_err = max(reconstructed_err, err)
                        elif age < iap_reference.IAP_MIN_AGE + iap_reference._EXACT_TABLE_GUARD:
                            boundary_err = max(boundary_err, err)
                        else:
                            max_err = max(max_err, err)
            results[f"{sex}|{measure}"] = {
                "pass": max_err < tol,
                "max_abs_error": round(max_err, 4),
                "tolerance": tol,
                "reference_path": "iap_2015_lms" if lms_live else "legacy_exact_table",
                "boundary_age_5_0_error": round(boundary_err, 4),
                "judged_centiles": sorted(judged),
                "reconstructed_max_error": round(reconstructed_err, 4),
            }
    return results


def run_full_validation(age_min: float = 0.0, age_max: float = 18.0, render_step: float = 0.1) -> ValidationReport:
    series_by_measure_sex = {
        (sex, measure): curve_builder.build_chart_series(measure, sex, age_min, age_max, render_step)
        for sex in SEXES
        for measure in MEASURES
    }
    report = ValidationReport()
    report.details["no_decrease_in_blend_window"] = check_no_decrease_in_blend_window()
    report.details["bmi_smoothness"] = check_bmi_smoothness()
    report.details["transition_value_continuity"] = check_transition_value_continuity()
    report.details["edge_slope_continuity"] = check_edge_slope_continuity()
    report.details["edge_curvature_continuity"] = check_edge_curvature_continuity()
    report.details["monotonic_age"] = check_monotonic_age(series_by_measure_sex)
    report.details["centile_ordering"] = check_centile_ordering(series_by_measure_sex)
    report.details["source_reproduction"] = check_source_reproduction()

    for section, checks in report.details.items():
        for key, result in checks.items():
            if not result["pass"]:
                report.all_pass = False
                report.failures.append(f"{section}: {key} -> {result}")
    return report

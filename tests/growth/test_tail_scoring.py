"""IAP tail z-scores follow the distribution's real skew (M1.2).

`_z_from_display_anchors` inverts a value against the centile curves the chart
actually draws, which keeps display and scoring consistent (audit GC-3/GC-4).
Between P3 and P97 it interpolates the ladder linearly, which is fine. Beyond
them it used to EXTEND that ladder in a straight line -- and the ladder is
linear in VALUE, so that is only correct where the distribution is near
symmetric.

Weight and BMI are strongly right-skewed (Cole's L far from 1). Measured before
the fix, at age 10:

    boys  weight, true z -3.0 -> scored -2.637   (+0.363)
    boys  weight, true z +3.0 -> scored +3.535   (+0.535)
    girls weight, true z +3.0 -> scored +3.814   (+0.814) at age 6

The lower tail is the dangerous direction: WHO's severe-underweight threshold is
-3 SD, so a child who genuinely met it was reported just above it -- false
reassurance, the worse way to be wrong.

The tail now follows the LMS shape, shifted to stay continuous with the drawn
P3/P97 anchor so the display/scoring guarantee is not broken to fix the skew.
"""
import pytest

from backend.growth import iap_reference as iap
from backend.growth.lms_core import lms_value_at_z

_MEASURES = ("height", "weight", "bmi")
_SEXES = ("boys", "girls")
_AGES = (6.0, 8.0, 10.0, 13.0, 16.0, 17.5)

# Residual tolerance. The LMS *fit* only approximates the published table (2
# free parameters against 6 published points), so a small mismatch survives --
# it is the fit's own error, not the tail's shape, and M1.1 (real published
# L,M,S) is what removes it. Pre-fix the same measurement was up to 0.81 SD.
_TAIL_TOL = 0.10


def _lms_value(measure, sex, age, z):
    l, m, s = iap._SERIES[(sex, measure)].lms_at(age)
    return lms_value_at_z(l, m, s, z)


@pytest.mark.parametrize("sex", _SEXES)
@pytest.mark.parametrize("measure", _MEASURES)
def test_tail_round_trip_is_accurate(sex, measure):
    """A value the distribution places at z must score back as ~z, in the tails."""
    worst = 0.0
    worst_at = None
    for age in _AGES:
        for target_z in (-4.0, -3.5, -3.0, -2.5, 2.5, 3.0, 3.5, 4.0):
            value = _lms_value(measure, sex, age, target_z)
            got = iap.iap_z_for_value(measure, sex, age, value)
            assert got is not None
            err = abs(got - target_z)
            if err > worst:
                worst, worst_at = err, (age, target_z, value, got)
    assert worst <= _TAIL_TOL, (
        f"{sex} {measure}: worst tail error {worst:.3f} SD at "
        f"age={worst_at[0]} true_z={worst_at[1]} value={worst_at[2]:.2f} -> {worst_at[3]:.3f}"
    )


@pytest.mark.parametrize("sex", _SEXES)
def test_severe_underweight_is_not_reported_as_moderate(sex):
    """The clinical consequence, pinned directly.

    A weight at a true -3.0 SD must not be handed back above the -3 SD severe
    threshold. Pre-fix it scored ~-2.64, i.e. inside the 'moderate' band.
    """
    for age in _AGES:
        value = _lms_value("weight", sex, age, -3.0)
        got = iap.iap_z_for_value("weight", sex, age, value)
        assert got < -2.9, (
            f"{sex} age {age}: a true -3.0 SD weight ({value:.2f} kg) scored {got:.3f} -- "
            "a child meeting the WHO severe-underweight threshold would be reported above it"
        )


@pytest.mark.parametrize("sex", _SEXES)
@pytest.mark.parametrize("measure", ("height", "weight"))
def test_no_step_where_the_ladder_hands_off_to_the_lms_tail(sex, measure):
    """The tail is shifted onto the drawn anchor precisely so this stays smooth.

    A discontinuity at P3/P97 would reintroduce the display-vs-scoring mismatch
    (GC-3/GC-4) that inverting the drawn centiles exists to prevent.
    """
    for age in (6.0, 10.0, 16.0):
        for z_anchor in (-1.88079, 1.88079):
            v = iap.iap_value_at_z(measure, sex, age, z_anchor)
            eps = v * 1e-7
            just_in = iap.iap_z_for_value(measure, sex, age, v + eps * (1 if z_anchor < 0 else -1))
            just_out = iap.iap_z_for_value(measure, sex, age, v - eps * (1 if z_anchor < 0 else -1))
            assert abs(just_out - just_in) < 1e-4, (
                f"{sex} {measure} age {age} at z={z_anchor}: step of "
                f"{abs(just_out - just_in):.2e} SD across the ladder/tail handoff"
            )


@pytest.mark.parametrize("sex", _SEXES)
@pytest.mark.parametrize("measure", _MEASURES)
def test_drawn_centiles_still_score_exactly(sex, measure):
    """Guard against fixing the tails by breaking the middle: a value sitting on
    a DRAWN centile must still return exactly that centile's z.

    Deliberately iterates the 7 drawn centiles (_STANDARD_Z), not every published
    column. BMI also publishes a p5 value, but p5 is not one of the curves the
    chart draws, so scoring interpolates it between the drawn P3 and P10 anchors
    and returns ~-1.71 rather than -1.64485. That is pre-existing and correct for
    a display-anchored inverse -- the guarantee is 'scores match what is drawn',
    not 'scores match every published column'.
    """
    for age in _AGES:
        for z in iap._STANDARD_Z:
            v = iap.iap_value_at_z(measure, sex, age, z)
            got = iap.iap_z_for_value(measure, sex, age, v)
            assert got == pytest.approx(z, abs=1e-6)


@pytest.mark.parametrize("sex", _SEXES)
@pytest.mark.parametrize("measure", _MEASURES)
def test_scoring_stays_monotonic_through_the_tails(sex, measure):
    """More measurement must never mean a lower z, including across the handoff."""
    age = 10.0
    lo = iap.iap_value_at_z(measure, sex, age, -1.88079)
    hi = iap.iap_value_at_z(measure, sex, age, 1.88079)
    # Multiplicative sweep, not additive: for weight P97-P3 exceeds P3, so
    # `lo - span` is a negative weight, which is not a measurement and correctly
    # scores None. Sweeping 0.5x-1.6x of the drawn range stays physical while
    # still crossing both handoffs.
    values = [lo * f for f in (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99)] + \
             [lo + (hi - lo) * k / 20 for k in range(21)] + \
             [hi * f for f in (1.01, 1.05, 1.10, 1.20, 1.35, 1.50, 1.60)]
    zs = [iap.iap_z_for_value(measure, sex, age, v) for v in values]
    assert all(z is not None for z in zs), "a physical measurement scored None"
    for (v0, z0), (v1, z1) in zip(zip(values, zs), zip(values[1:], zs[1:])):
        assert z1 > z0, f"{sex} {measure}: z fell from {z0:.4f} to {z1:.4f} as value rose {v0:.2f}->{v1:.2f}"

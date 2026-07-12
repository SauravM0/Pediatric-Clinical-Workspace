"""Display <-> scoring consistency for the IAP region (audit GC-3/GC-4).

The chart draws each published centile from the exact IAP table, but a patient's
z-score used to come from the fitted LMS model -- two different models, so a
value sitting exactly on a drawn centile did NOT necessarily score as that
centile. iap_z_for_value now inverts the SAME curves the chart draws, so:

  unified_z_for_value(unified_value_at_z(z)) == z   at every published centile,

and a value between two drawn centiles gets a z strictly between them.

These tests operate on the blend engine directly (fast, exact) and pin the fix,
plus a guard proving the old pure-LMS inversion really did diverge (so the fix
is not a no-op).
"""
import math

import pytest

from backend.growth import blend, curve_builder, iap_reference, lms_core

_Z = curve_builder.Z_FOR_CENTILE
_MEASURES = ("height", "weight", "bmi")
_SEXES = ("boys", "girls")
# Exact-table region only: at/just above IAP_MIN_AGE the drawn curve is still
# LMS by design (the guard band), so consistency there is trivially LMS-vs-LMS.
_AGES = (5.2, 6.0, 8.5, 10.0, 12.5, 15.0, 18.0)


@pytest.mark.parametrize("measure", _MEASURES)
@pytest.mark.parametrize("sex", _SEXES)
def test_value_on_a_drawn_centile_scores_as_that_centile(measure, sex):
    for age in _AGES:
        for centile, z in _Z.items():
            v = blend.unified_value_at_z(measure, sex, age, z)
            if v is None:
                continue
            z_back = blend.unified_z_for_value(measure, sex, age, v)
            assert z_back is not None
            assert z_back == pytest.approx(z, abs=1e-6), (
                f"{measure}/{sex}/{age}y P{centile}: value {v:.3f} scored as "
                f"z={z_back:.5f}, expected {z:.5f} -- display/scoring drifted."
            )


@pytest.mark.parametrize("measure", _MEASURES)
@pytest.mark.parametrize("sex", _SEXES)
def test_value_between_two_drawn_centiles_scores_between_them(measure, sex):
    for age in (6.0, 10.0, 15.0):
        v75 = blend.unified_value_at_z(measure, sex, age, _Z[75])
        v90 = blend.unified_value_at_z(measure, sex, age, _Z[90])
        if v75 is None or v90 is None:
            continue
        z_mid = blend.unified_z_for_value(measure, sex, age, (v75 + v90) / 2)
        assert z_mid is not None
        assert _Z[75] < z_mid < _Z[90], (
            f"{measure}/{sex}/{age}y: value halfway between P75 and P90 scored "
            f"z={z_mid:.4f}, expected strictly between {_Z[75]} and {_Z[90]}."
        )


def test_percentile_of_a_p90_point_is_about_90():
    # End-to-end sanity: a value on the drawn 90th centile reads ~90th percentile.
    from scipy.stats import norm
    for measure in _MEASURES:
        for sex in _SEXES:
            v90 = blend.unified_value_at_z(measure, sex, 10.0, _Z[90])
            z = blend.unified_z_for_value(measure, sex, 10.0, v90)
            pct = float(norm.cdf(z) * 100)
            assert pct == pytest.approx(90.0, abs=0.5), f"{measure}/{sex}: {pct:.2f}th"


def test_old_pure_lms_inversion_really_did_diverge():
    """Regression guard: prove the fix is not a no-op. The retired pure-LMS
    inversion, applied to an exact-table centile value, missed the centile's own
    z by a clinically visible margin for at least one published centile."""
    worst = 0.0
    for measure in _MEASURES:
        for sex in _SEXES:
            series = iap_reference._SERIES[(sex, measure)]
            for age in _AGES:
                l, m, s = series.lms_at(age)
                for centile, z in _Z.items():
                    v = blend.unified_value_at_z(measure, sex, age, z)
                    if v is None:
                        continue
                    old_z = lms_core.lms_z_score(v, l, m, s)  # what iap_z_for_value used to return
                    worst = max(worst, abs(old_z - z))
    # The old model was off by well over a hundredth of an SD somewhere; the new
    # inversion (test above) is exact to 1e-6. This documents the gap that GC-4
    # closed.
    assert worst > 0.03, f"expected the old LMS inversion to diverge; worst was {worst:.4f}"

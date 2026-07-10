"""Automated tests for the pediatric growth calculation engine
(backend/growth/). Run with: pytest tests/growth -v
"""
import math

import pytest

from backend.growth import blend, curve_builder, iap_reference, validation, who_reference


# ── Root-level sanity: rcpchgrowth's WHO data agrees with published values ──

def test_who_boys_height_median_at_9y_matches_official_who_table():
    # Official WHO 2007 boys height-for-age median at 108 months (9.0y) = 132.5652cm
    assert who_reference.who_value_at_z("height", "boys", 9.0, 0.0) == pytest.approx(132.5652, abs=1e-3)


def test_who_weight_unavailable_beyond_10_years():
    assert who_reference.who_value_at_z("weight", "boys", 12.0, 0.0) is None


def test_who_handles_the_under_over_2y_dataset_boundary():
    # WHO's under-2 (recumbent length) / over-2 (standing height) datasets
    # leave a ~5-day gap around exactly 2.0y; the wrapper must not crash.
    v = who_reference.who_value_at_z("height", "boys", 2.0, 0.0)
    assert v is not None and 80 < v < 95


def _local_slopes(measure, sex, ages):
    """Per-year slope between each consecutive pair of (possibly unevenly
    spaced) sample ages -- the right way to check for a discontinuity,
    unlike a raw value difference which conflates step size with jump size."""
    values = [blend.unified_value_at_z(measure, sex, a, 0.0) for a in ages]
    return [(v1 - v0) / (a1 - a0) for a0, a1, v0, v1 in zip(ages, ages[1:], values, values[1:])], values


@pytest.mark.parametrize("sex,measure", [(s, m) for s in ("boys", "girls") for m in ("height", "bmi")])
def test_no_jump_at_2y_recumbent_length_vs_standing_height_seam(sex, measure):
    # Concrete regression: girls height median dropped from 86.31cm (1.99y) to
    # 85.75cm (2.00y) -- a slope of roughly -190 cm/year over that single-day
    # step -- before this was fixed. WHO's recumbent-length/standing-height
    # measurement convention switches at exactly 2.0y, and BMI inherits the
    # same step since it's derived from height. Weight is unaffected (doesn't
    # depend on the convention) and isn't checked here.
    ages = [1.90, 1.94, 1.96, 1.98, 1.99, 2.00, 2.01, 2.02, 2.04, 2.06, 2.10]
    slopes, values = _local_slopes(measure, sex, ages)
    # Normal height/BMI slopes in this age range are single-digit units/year;
    # a real discontinuity showed up as ~100+ units/year. Use a generous but
    # discontinuity-scale threshold.
    assert max(abs(s) for s in slopes) < 20, f"still a visible jump near 2.0y: {list(zip(ages, values))}"


def test_weight_is_smooth_through_2y_seam_too():
    # Weight doesn't depend on the length/height convention, so it should
    # already have been smooth -- guard against a future change breaking it.
    ages = [1.90, 1.95, 1.99, 2.00, 2.01, 2.05, 2.10]
    slopes, values = _local_slopes("weight", "boys", ages)
    assert max(abs(s) for s in slopes) < 10


@pytest.mark.parametrize("sex,measure", [(s, m) for s in ("boys", "girls") for m in ("height", "weight", "bmi")])
def test_no_jump_at_508_who_2006_2007_table_handoff_seam(sex, measure):
    # Found via a full 0-18y discontinuity scan (not from a bug report):
    # rcpchgrowth's own WHO-2006-child (0-5y) and WHO-2007-child (5-19y)
    # tables don't quite agree at their ~5.08y handoff -- girls height dropped
    # ~0.31cm and boys BMI jumped ~0.08 kg/m^2 in a single 0.005y step before
    # this was fixed. Currently invisible in this app's actual chart/scoring
    # output (blend.py's 4.5-5.0y WHO/IAP window masks it as a side effect --
    # it never queries raw WHO at any age other than exactly 4.5 in that
    # range), but who_reference.py is fixed independently so it stays correct
    # regardless of how the blend window happens to be configured elsewhere.
    ages = [4.98, 5.02, 5.06, 5.08, 5.09, 5.10, 5.12, 5.16, 5.2]
    slopes, values = _local_slopes(measure, sex, ages)
    assert max(abs(s) for s in slopes) < 15, f"still a visible jump near 5.08y: {list(zip(ages, values))}"


# ── IAP fit reproduces the actual published tables ──────────────────────────

@pytest.mark.parametrize("sex,age,measure,z,expected", [
    ("boys", 12.0, "height", 0.0, 148.4),
    ("boys", 12.0, "weight", 0.0, 39.0),
    ("boys", 12.0, "bmi", 0.0, 17.7),
    ("girls", 18.0, "height", 0.0, 157.8),   # exact figure stated in the paper's abstract
    ("boys", 5.0, "height", -1.88079, 99.0),
])
def test_iap_reproduces_published_percentile_table(sex, age, measure, z, expected):
    got = iap_reference.iap_value_at_z(measure, sex, age, z)
    assert got == pytest.approx(expected, abs=0.5)


def test_iap_bmi_cutoffs_match_iotf_adult_equivalent_values():
    c23, c27 = iap_reference.iap_bmi_cutoffs("boys", 18.0)
    assert c23 == pytest.approx(23.2, abs=0.1)
    assert c27 == pytest.approx(26.6, abs=0.1)


def test_iap_returns_none_outside_its_coverage():
    assert iap_reference.iap_value_at_z("height", "boys", 3.0, 0.0) is None
    assert iap_reference.iap_value_at_z("height", "boys", 19.0, 0.0) is None


# ── Blend: no hard switch, WHO/IAP separate, smooth join at 5y ──────────────

def test_blend_weight_is_pure_who_below_window_and_pure_iap_above():
    assert blend.blend_weight(blend.BLEND_LO - 0.1) == 0.0
    assert blend.blend_weight(blend.BLEND_HI + 0.1) == 1.0
    assert 0.0 < blend.blend_weight((blend.BLEND_LO + blend.BLEND_HI) / 2) < 1.0


def test_blend_falls_back_to_who_beyond_iap_range():
    # 19y (228mo) adult-height projection: IAP has no data there, so this must
    # fall back to WHO rather than returning None (a real bug caught during
    # development -- the blend must query both sources, not just the one the
    # weight nominally favors).
    v = blend.unified_value_at_z("height", "girls", 19.0, 0.0)
    assert v == pytest.approx(163.1548, abs=1e-2)


def test_no_hard_jump_at_5_years_boys_bmi_p97():
    # This is the concrete regression the whole rebuild targets: a hard
    # WHO/IAP switch at exactly 5.0y produced a ~2 kg/m^2 jump for boys BMI
    # P97 within a single month. The blended value must change smoothly.
    z97 = curve_builder.Z_FOR_CENTILE[97]
    ages = [4.83, 4.92, 5.0, 5.08, 5.17]
    values = [blend.unified_value_at_z("bmi", "boys", a, z97) for a in ages]
    diffs = [abs(b - a) for a, b in zip(values, values[1:])]
    assert max(diffs) < 0.5, f"still a visible jump: {values}"


@pytest.mark.parametrize("sex,measure", [(s, m) for s in ("boys", "girls") for m in ("height", "weight", "bmi")])
def test_edge_slope_continuity_for_every_measure_and_sex(sex, measure):
    results = validation.check_edge_slope_continuity()
    failing = [k for k, v in results.items() if k.startswith(f"{sex}|{measure}|") and not v["pass"]]
    assert not failing, f"slope discontinuity at window edge: {failing}"


# ── Curve builder: PCHIP, dense, monotone, non-oscillating ──────────────────

def test_dense_curve_has_many_more_points_than_sparse_source_rows():
    curve = curve_builder.build_centile_curve("height", "boys", 50)
    assert len(curve.ages) > 150   # 18 years / 0.1y step ~= 180
    # The IAP source table itself is 27 rows (0.5y steps, 5-18y); rendering
    # must not fall back to connecting those sparse rows with straight lines.
    n_source_rows = 27
    assert len(curve.ages) > 5 * n_source_rows


def test_dense_curve_ages_strictly_increasing():
    curve = curve_builder.build_centile_curve("weight", "girls", 3)
    assert all(b > a for a, b in zip(curve.ages, curve.ages[1:]))


def test_centiles_never_cross():
    series = curve_builder.build_chart_series("height", "boys")
    ages = series[3].ages
    for i in range(len(ages)):
        values_at_age = [series[c].values[i] for c in curve_builder.STANDARD_CENTILES]
        assert values_at_age == sorted(values_at_age), f"centile crossing at age {ages[i]}"


def test_pchip_does_not_overshoot_beyond_anchor_range():
    curve = curve_builder.build_centile_curve("bmi", "girls", 97)
    assert curve.values.min() >= curve.anchor_values.min() - 0.5
    assert curve.values.max() <= curve.anchor_values.max() + 0.5


# ── Full validation suite (also runnable standalone / in CI) ────────────────

def test_full_validation_suite_passes():
    report = validation.run_full_validation()
    assert report.all_pass, "\n".join(report.failures)


def test_validation_report_is_json_serializable():
    # Regression: numpy bool_/float64 values leaking into the report (from
    # comparisons involving numpy-array-derived intermediates in the
    # validation checks) pass every pytest assertion fine but crash FastAPI's
    # response serializer at /api/growth/validate with "Unable to serialize
    # unknown type: numpy.bool". Pytest alone won't catch this -- only an
    # actual JSON round-trip will.
    import json

    report = validation.run_full_validation()
    json.dumps({"all_pass": report.all_pass, "failures": report.failures, "details": report.details})

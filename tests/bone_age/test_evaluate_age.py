"""Whole-hand age evaluator (Plan 5 WI-2/WI-3) — hand-verified metrics.

Pure numpy math; every expected value below is computed by hand so the test is a
specification, not a mirror of the implementation.
"""
import math

import pytest

from backend.ai.evaluate import age_band_years, evaluate_age, evaluate_by_subgroup

# Reference case used across tests:
#   preds   = [12, 24, 36]   targets = [10, 20, 40]
#   diff    = [ 2,  4, -4]   abs_err = [ 2,  4,  4]
_PREDS = [12, 24, 36]
_TARGETS = [10, 20, 40]


def test_point_metrics_hand_verified():
    r = evaluate_age(_PREDS, _TARGETS)
    assert r["n"] == 3
    assert r["mae_months"] == round(10 / 3, 3)                 # (2+4+4)/3
    assert r["median_ae_months"] == 4.0                       # median[2,4,4]
    assert abs(r["rmse_months"] - math.sqrt(12)) < 1e-3       # sqrt((4+16+16)/3)
    assert abs(r["signed_bias_months"] - (2 / 3)) < 1e-3      # mean[2,4,-4]


def test_within_bands():
    r = evaluate_age(_PREDS, _TARGETS)["pct_within_months"]
    assert r["3"] == round(100 / 3, 2)   # only |2| <= 3
    assert r["6"] == 100.0               # all <= 6
    assert r["9"] == 100.0 and r["12"] == 100.0


def test_bland_altman_limits():
    ba = evaluate_age(_PREDS, _TARGETS)["bland_altman"]
    # diff mean 0.667; sd(ddof=1) = sqrt(((1.333^2)+(3.333^2)+(4.667^2))/2) = 4.163
    assert abs(ba["mean_diff_months"] - (2 / 3)) < 1e-3
    assert abs(ba["sd_diff_months"] - 4.163) < 1e-2
    assert ba["loa_lower_months"] < ba["mean_diff_months"] < ba["loa_upper_months"]


def test_coverage_and_target_flag():
    # targets [10,20,40]; intervals cover 10 and 40 but not 20 -> 2/3.
    intervals = [(7, 17), (25, 35), (35, 45)]
    r = evaluate_age(_PREDS, _TARGETS, intervals=intervals, target_coverage=0.90)
    assert r["coverage"]["n_covered"] == 2
    assert r["coverage"]["empirical"] == round(2 / 3, 4)
    assert r["coverage"]["meets_target"] is False


def test_abstention_rate():
    r = evaluate_age([1, 2, 3], [1, 2, 3], abstained=[False, True, False])
    assert r["abstention_rate"] == round(1 / 3, 4)


def test_bias_ci_is_deterministic_and_brackets_truth():
    preds = list(range(100))
    targets = [p - 5 for p in preds]         # exact +5 month bias everywhere
    a = evaluate_age(preds, targets)
    b = evaluate_age(preds, targets)
    assert a["signed_bias_ci95_months"] == b["signed_bias_ci95_months"]  # seeded
    lo, hi = a["signed_bias_ci95_months"]
    assert lo <= 5.0 <= hi
    assert a["signed_bias_months"] == 5.0


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        evaluate_age([1, 2], [1])


def test_empty_is_insufficient():
    r = evaluate_age([], [])
    assert r["n"] == 0 and r.get("insufficient") is True


def test_age_bands():
    assert age_band_years(3) == "0-5y"
    assert age_band_years(5) == "0-5y"
    assert age_band_years(7) == ">5-8y"
    assert age_band_years(11) == ">8-12y"
    assert age_band_years(14) == ">12-15y"
    assert age_band_years(17) == ">15-18y"
    assert age_band_years(None) == "unknown"


def test_subgroup_flags_worst_and_marks_underpowered():
    recs = [
        {"pred": 12, "target": 12, "sex": "boys"},
        {"pred": 20, "target": 20, "sex": "boys"},
        {"pred": 30, "target": 40, "sex": "girls"},   # 10 mo error
        {"pred": 30, "target": 42, "sex": "girls"},   # 12 mo error
        {"pred": 15, "target": 15, "sex": "unknown"},  # single -> underpowered at min_n=2
    ]
    out = evaluate_by_subgroup(recs, by=["sex"], min_n=2)
    assert out["overall"]["n"] == 5
    assert out["worst_subgroup"]["group"] == {"sex": "girls"}
    underpowered = [c for c in out["subgroups"] if c.get("insufficient")]
    assert underpowered and underpowered[0]["group"] == {"sex": "unknown"}

"""Subgroup-conditional (Mondrian) conformal (Plan 3 WI-3).

Pure math + selection logic -- no model file needed. Proves per-group quantiles,
safe fallback for small/unknown groups, and that select_interval prefers the
grouped interval, then marginal conformal, then a labelled MAE band.
"""
import numpy as np

from backend.ai import conformal


def test_age_band_months_boundaries():
    assert conformal.age_band_months(0) == "0-5y"
    assert conformal.age_band_months(60) == "0-5y"       # 5.0y
    assert conformal.age_band_months(84) == ">5-8y"      # 7.0y
    assert conformal.age_band_months(132) == ">8-12y"    # 11.0y
    assert conformal.age_band_months(168) == ">12-15y"   # 14.0y
    assert conformal.age_band_months(216) == ">15-18y"   # 18.0y


def test_bucket_key():
    assert conformal.bucket(True, 120) == "boys:>8-12y"
    assert conformal.bucket(False, 36) == "girls:0-5y"


def test_grouped_large_group_gets_own_quantile_small_falls_back():
    rng = np.random.default_rng(0)
    big = list(np.abs(rng.normal(0, 5, size=200)))    # tight group
    wide = list(np.abs(rng.normal(0, 20, size=200)))  # wide group
    small = [50.0, 60.0]                               # 2 points -> fallback
    residuals = big + wide + small
    groups = ["boys:0-5y"] * 200 + ["boys:>12-15y"] * 200 + ["girls:0-5y"] * 2
    out = conformal.calibrate_grouped(residuals, groups, (0.90,), min_group=30)
    g = out["groups"]
    assert g["boys:0-5y"]["fallback"] is False
    assert g["boys:>12-15y"]["fallback"] is False
    # the tight group has a narrower 90% half-width than the wide group
    assert g["boys:0-5y"]["quantiles"]["0.90"] < g["boys:>12-15y"]["quantiles"]["0.90"]
    # the 2-point group fell back to the marginal quantile
    assert g["girls:0-5y"]["fallback"] is True
    assert g["girls:0-5y"]["quantiles"]["0.90"] == out["marginal"]["quantiles"]["0.90"]


def test_group_quantile_unknown_group_falls_back():
    groups = {"boys:0-5y": {"quantiles": {"0.90": 10.0}, "fallback": False}}
    marginal = {"0.90": 18.0}
    q, fb = conformal.group_quantile(groups, marginal, "boys:0-5y", "0.90")
    assert q == 10.0 and fb is False
    q2, fb2 = conformal.group_quantile(groups, marginal, "girls:>15-18y", "0.90")
    assert q2 == 18.0 and fb2 is True     # unknown group -> marginal


def test_select_interval_prefers_grouped_then_marginal_then_mae():
    meta_grouped = {"val_mae_months": 8.6, "conformal": {
        "default_coverage": "0.90",
        "quantiles_months": {"0.90": 18.0},
        "by_group": {"boys:>8-12y": {"quantiles": {"0.90": 11.0}, "fallback": False}},
    }}
    s = conformal.select_interval(meta_grouped, is_male=True, months=120)  # ->boys:>8-12y
    assert s["kind"] == "conformal_grouped" and s["half"] == 11.0
    assert s["group"] == "boys:>8-12y" and s["fallback"] is False and s["coverage"] == "0.90"

    # a group not in by_group -> marginal fallback, flagged
    s2 = conformal.select_interval(meta_grouped, is_male=False, months=36)  # girls:0-5y
    assert s2["kind"] == "conformal_grouped" and s2["half"] == 18.0 and s2["fallback"] is True

    # no by_group -> marginal conformal
    meta_marginal = {"conformal": {"default_coverage": "0.90", "quantiles_months": {"0.90": 18.0}}}
    assert conformal.select_interval(meta_marginal, True, 100)["kind"] == "conformal"

    # only MAE -> labelled approximation, no coverage
    s3 = conformal.select_interval({"val_mae_months": 8.6}, True, 100)
    assert s3["kind"] == "mae_approx" and s3["half"] == 8.6 and s3["coverage"] is None

    # nothing -> none
    assert conformal.select_interval({}, True, 100)["kind"] == "none"

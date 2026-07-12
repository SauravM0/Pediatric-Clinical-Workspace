"""Split-conformal uncertainty for the bone-age screening model (directive S-BA-5).

Proves the pure conformal math gives its coverage guarantee, and that
predict_months surfaces a CONFORMAL interval when the model is calibrated and a
clearly-labelled MAE approximation (never a fake guarantee) when it is not.
"""
import numpy as np
import pytest

from backend.ai import boneage, conformal


# ── pure conformal math ──────────────────────────────────────────────────────

def test_finite_sample_quantile_is_the_kth_residual():
    # residuals 1..100, alpha=0.1 -> k = ceil(101*0.9) = 91 -> the 91st smallest
    assert conformal.conformal_quantile(range(1, 101), 0.1) == 91.0


@pytest.mark.parametrize("alpha", [0.2, 0.1, 0.05])
def test_coverage_guarantee_holds_on_the_calibration_set(alpha):
    rng = np.random.default_rng(0)
    r = np.abs(rng.normal(0, 10, size=2000))
    q = conformal.conformal_quantile(r, alpha)
    assert conformal.empirical_coverage(r, q) >= (1 - alpha)


def test_calibrate_is_monotonic_in_coverage():
    rng = np.random.default_rng(1)
    r = np.abs(rng.normal(0, 8, size=1500))
    cal = conformal.calibrate(r, (0.80, 0.90, 0.95))
    q = cal["quantiles"]
    assert q["0.80"] < q["0.90"] < q["0.95"]
    assert cal["n_calib"] == 1500


def test_small_n_returns_widest_not_a_false_guarantee():
    # n=3, alpha=0.05 -> k=ceil(4*0.95)=4 > 3 -> widest residual
    assert conformal.conformal_quantile([2, 5, 9], 0.05) == 9.0


def test_alpha_must_be_a_probability():
    with pytest.raises(ValueError):
        conformal.conformal_quantile([1, 2, 3], 1.5)


def test_interval_clamps_to_plausible_range():
    assert conformal.interval(120.0, 18.0) == (102.0, 138.0)
    assert conformal.interval(6.0, 18.0)[0] == 0.0        # no negative age
    assert conformal.interval(10.0, None) == (None, None)


# ── predict_months integration ───────────────────────────────────────────────

def _synthetic_image():
    from PIL import Image
    arr = np.random.default_rng(0).integers(0, 256, (224, 224), dtype=np.uint8)
    return Image.fromarray(arr, mode="L")


@pytest.mark.skipif(not boneage.model_available(), reason="no ONNX model installed")
def test_predict_uses_calibrated_conformal_interval():
    r = boneage.predict_months(_synthetic_image(), is_male=True)
    assert r["interval_kind"] == "conformal"
    assert r["interval_coverage"] == "0.90"
    # the 90% band must be materially wider than +/-MAE (the old, overconfident band)
    assert r["uncertainty_months"] > r["val_mae_months"]
    assert r["ci_low_years"] < r["bone_age_years"] < r["ci_high_years"]


@pytest.mark.skipif(not boneage.model_available(), reason="no ONNX model installed")
def test_predict_falls_back_to_labelled_mae_without_calibration(monkeypatch):
    monkeypatch.setattr(boneage, "model_metadata",
                        lambda: {"val_mae_months": 8.6, "input_size": 224})
    r = boneage.predict_months(_synthetic_image(), is_male=False)
    assert r["interval_kind"] == "mae_approx"      # honestly labelled, not "conformal"
    assert r["interval_coverage"] is None
    assert r["uncertainty_months"] == 8.6


@pytest.mark.skipif(not boneage.model_available(), reason="no ONNX model installed")
def test_predict_reports_no_interval_when_no_stats(monkeypatch):
    monkeypatch.setattr(boneage, "model_metadata", lambda: {"input_size": 224})
    r = boneage.predict_months(_synthetic_image(), is_male=True)
    assert r["interval_kind"] == "none"
    assert r["ci_low_years"] is None and r["ci_high_years"] is None

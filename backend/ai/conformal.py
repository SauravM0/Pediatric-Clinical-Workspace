"""Split-conformal prediction intervals for the bone-age screening model
(directive S-BA-5).

A single validation MAE is not a patient-level confidence interval -- it hides
tail errors and gives no coverage guarantee. Split conformal prediction fixes
that with one distribution-free guarantee: given calibration residuals
r_i = |y_i - yhat_i| on a held-out set the model never trained on, the half-width

    q = the k-th smallest residual,  k = ceil((n + 1)(1 - alpha))

yields an interval [yhat - q, yhat + q] with **marginal coverage >= 1 - alpha**
for an exchangeable new case -- no distributional assumptions, no retraining.

This module is the pure math (calibrate + apply). The actual residuals come from
backend/ai/calibrate_conformal.py running the model on the RSNA val split; the
resulting quantiles are stored in the model metadata and used by
boneage.predict_months.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional


def conformal_quantile(residuals: Iterable[float], alpha: float) -> Optional[float]:
    """Finite-sample split-conformal half-width for miscoverage ``alpha``.

    Returns the smallest q such that at least ceil((n+1)(1-alpha)) of the n
    calibration residuals are <= q -- the exact quantile that guarantees
    >= 1-alpha marginal coverage. When n is too small to reach the requested
    coverage (k > n), returns the largest residual (the widest the data
    supports) rather than pretending to a guarantee it can't give.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    r = sorted(abs(float(x)) for x in residuals)
    n = len(r)
    if n == 0:
        return None
    k = math.ceil((n + 1) * (1 - alpha))
    if k > n:
        return r[-1]
    return r[k - 1]


def calibrate(residuals: Iterable[float], coverage_levels: Iterable[float]) -> dict:
    """Compute conformal half-widths for several target coverage levels.

    Returns {"n_calib", "quantiles": {coverage_str: half_width}}. coverage is the
    target 1-alpha (e.g. 0.9); the key is a fixed-precision string for JSON.
    """
    r = [abs(float(x)) for x in residuals]
    n = len(r)
    quantiles: dict[str, float] = {}
    for cov in coverage_levels:
        q = conformal_quantile(r, 1.0 - cov)
        if q is not None:
            quantiles[f"{cov:.2f}"] = round(q, 2)
    return {"n_calib": n, "quantiles": quantiles}


def interval(point: float, half_width: Optional[float],
             lo_clamp: float = 0.0, hi_clamp: float = 240.0) -> tuple[Optional[float], Optional[float]]:
    """Clamp [point - q, point + q] to a plausible range (months). q None -> (None, None)."""
    if half_width is None:
        return None, None
    return max(lo_clamp, point - half_width), min(hi_clamp, point + half_width)


def empirical_coverage(residuals: Iterable[float], half_width: float) -> float:
    """Fraction of residuals within +/- half_width -- for validating a calibration."""
    r = [abs(float(x)) for x in residuals]
    return sum(1 for x in r if x <= half_width) / len(r) if r else 0.0

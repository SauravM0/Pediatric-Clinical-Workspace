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


# ── subgroup-conditional (Mondrian) conformal (directive S-BA-5 / Plan 3 WI-3) ──
#
# A single marginal interval is the SAME width for a clear 6-yo film and an
# ambiguous pubertal one. Mondrian conformal calibrates a separate quantile per
# group (here sex x age-band) so coverage holds WITHIN a group and intervals
# sharpen where the model is reliable. The group must be computable from the
# inputs at inference time -- so the age band uses the PREDICTED bone age, not the
# (unknown) true age. Groups too small to guarantee coverage fall back to the
# marginal quantile (honest: marginal coverage, not conditional).

_AGE_BANDS_YEARS = ((5.0, "0-5y"), (8.0, ">5-8y"), (12.0, ">8-12y"), (15.0, ">12-15y"))


def age_band_months(months: float) -> str:
    """validation_protocol.md §3 age band for an age in MONTHS."""
    years = float(months) / 12.0
    for hi, label in _AGE_BANDS_YEARS:
        if years <= hi:
            return label
    return ">15-18y"


def bucket(is_male: bool, months: float) -> str:
    """Mondrian group key = sex x predicted-age-band, e.g. 'boys:>8-12y'."""
    return f"{'boys' if is_male else 'girls'}:{age_band_months(months)}"


def calibrate_grouped(residuals: Iterable[float], groups: Iterable[str],
                      coverage_levels: Iterable[float], *, min_group: int = 30) -> dict:
    """Per-group conformal half-widths. A group with fewer than ``min_group``
    calibration residuals falls back to the marginal quantiles (``fallback=True``)
    rather than pretend to a conditional guarantee it cannot give.

    Returns ``{"groups": {g: {"n_calib", "quantiles", "fallback"}}, "marginal":
    {...}, "min_group": n}``.
    """
    residuals = [abs(float(x)) for x in residuals]
    groups = [str(g) for g in groups]
    marginal = calibrate(residuals, coverage_levels)
    buckets: dict[str, list[float]] = {}
    for r, g in zip(residuals, groups):
        buckets.setdefault(g, []).append(r)
    out: dict[str, dict] = {}
    for g, rs in sorted(buckets.items()):
        if len(rs) >= min_group:
            c = calibrate(rs, coverage_levels)
            c["fallback"] = False
        else:
            c = {"n_calib": len(rs), "quantiles": dict(marginal["quantiles"]), "fallback": True}
        out[g] = c
    return {"groups": out, "marginal": marginal, "min_group": int(min_group)}


def group_quantile(groups: Optional[dict], marginal_quantiles: Optional[dict],
                   group: str, coverage_str: str) -> tuple[Optional[float], bool]:
    """Half-width for ``group`` at ``coverage_str``. Returns ``(q, fallback)`` --
    fallback True when the group is unknown/too-small and the marginal was used."""
    g = (groups or {}).get(str(group))
    if g and coverage_str in (g.get("quantiles") or {}):
        return g["quantiles"][coverage_str], bool(g.get("fallback", False))
    q = (marginal_quantiles or {}).get(coverage_str)
    return q, True


def select_interval(meta: dict, is_male: bool, months: float) -> dict:
    """Pick the uncertainty half-width for a prediction from the model metadata.

    Prefers a subgroup-conditional (Mondrian) conformal quantile when the metadata
    carries ``conformal.by_group``; else the marginal conformal quantile; else a
    clearly-labelled +/-MAE approximation; else nothing. Pure -- no model needed --
    so the selection logic is unit-testable. Returns
    ``{kind, half, coverage, group, fallback}``.
    """
    mae = meta.get("val_mae_months")
    conf = meta.get("conformal") or {}
    coverage = conf.get("default_coverage", "0.90")
    quants = conf.get("quantiles_months") or {}
    by_group = conf.get("by_group")

    kind, half, group, fallback = "none", None, None, False
    if by_group:
        group = bucket(is_male, months)
        q, fb = group_quantile(by_group, quants, group, coverage)
        if isinstance(q, (int, float)):
            kind, half, fallback = "conformal_grouped", float(q), bool(fb)
    if half is None:
        q = quants.get(coverage)
        if isinstance(q, (int, float)):
            kind, half = "conformal", float(q)
        elif isinstance(mae, (int, float)):
            kind, half = "mae_approx", float(mae)
    coverage_out = coverage if kind in ("conformal", "conformal_grouped") else None
    return {"kind": kind, "half": half, "coverage": coverage_out,
            "group": group, "fallback": fallback}

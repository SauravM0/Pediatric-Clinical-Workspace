"""Dense, smooth percentile curves for chart rendering.

Builds monthly anchor points from the blended WHO/IAP reference (blend.py),
then runs them through scipy's PchipInterpolator (Fritsch-Carlson monotone
cubic Hermite interpolation) and re-samples densely for display. PCHIP
preserves the monotonicity of the anchor data, so it cannot introduce
overshoot or fake bumps the way a plain (non-shape-preserving) cubic spline
can -- this is the standard, validated implementation (scipy), not a
hand-rolled one.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import PchipInterpolator

from . import blend

STANDARD_CENTILES = (3, 10, 25, 50, 75, 90, 97)
Z_FOR_CENTILE = {3: -1.88079, 10: -1.28155, 25: -0.67449, 50: 0.0, 75: 0.67449, 90: 1.28155, 97: 1.88079}

DEFAULT_AGE_MIN = 0.0
DEFAULT_AGE_MAX = 18.0
DEFAULT_RENDER_STEP = 0.1  # years; user asked for 0.05-0.1y dense sampling
_ANCHOR_STEP_MONTHS = 1  # native monthly anchor resolution before PCHIP


@dataclass
class CentileCurve:
    centile: int
    ages: np.ndarray   # dense, years
    values: np.ndarray  # dense
    anchor_ages: np.ndarray   # sparse (monthly) inputs to PCHIP, for QA/debug
    anchor_values: np.ndarray


def _anchor_points(measure: str, sex: str, age_min: float, age_max: float, z: float) -> tuple[np.ndarray, np.ndarray]:
    months = np.arange(round(age_min * 12), round(age_max * 12) + 1, _ANCHOR_STEP_MONTHS)
    ages = months / 12.0
    raw = [(a, blend.unified_value_at_z(measure, sex, a, z)) for a in ages]
    pairs = [(a, v) for a, v in raw if v is not None]
    if not pairs:
        return np.array([]), np.array([])
    ages_out, values_out = zip(*pairs)
    return np.array(ages_out), np.array(values_out, dtype=float)


def build_centile_curve(
    measure: str,
    sex: str,
    centile: int,
    age_min: float = DEFAULT_AGE_MIN,
    age_max: float = DEFAULT_AGE_MAX,
    render_step: float = DEFAULT_RENDER_STEP,
) -> CentileCurve:
    z = Z_FOR_CENTILE[centile]
    anchor_ages, anchor_values = _anchor_points(measure, sex, age_min, age_max, z)
    if len(anchor_ages) < 3:
        return CentileCurve(centile, anchor_ages, anchor_values, anchor_ages, anchor_values)

    pchip = PchipInterpolator(anchor_ages, anchor_values)
    dense_ages = np.arange(anchor_ages[0], anchor_ages[-1], render_step)
    dense_ages = np.append(dense_ages, anchor_ages[-1])  # exact endpoint
    dense_values = pchip(dense_ages)
    return CentileCurve(centile, dense_ages, dense_values, anchor_ages, anchor_values)


def build_chart_series(
    measure: str,
    sex: str,
    age_min: float = DEFAULT_AGE_MIN,
    age_max: float = DEFAULT_AGE_MAX,
    render_step: float = DEFAULT_RENDER_STEP,
) -> dict[int, CentileCurve]:
    """All 7 standard centile curves for one measure/sex, ready to plot."""
    return {
        c: build_centile_curve(measure, sex, c, age_min, age_max, render_step)
        for c in STANDARD_CENTILES
    }


def series_to_json(series: dict[int, CentileCurve]) -> dict:
    """JSON-friendly shape for the frontend: {centile: [[age, value], ...]}."""
    return {
        str(c): [[round(float(a), 3), round(float(v), 4)] for a, v in zip(curve.ages, curve.values)]
        for c, curve in series.items()
    }

"""Growth chart API -- the only place chart data comes from. All percentile
math (LMS transform, WHO/IAP blending, PCHIP dense sampling) happens in
``backend/growth``; this router just serializes it. The frontend must not
recompute percentiles itself -- see frontend/index.html's growth section.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.growth import blend, curve_builder, validation

router = APIRouter(prefix="/api/growth", tags=["growth"])

_VALID_MEASURES = ("height", "weight", "bmi")
_VALID_SEXES = ("boys", "girls")
_UNITS = {"height": "cm", "weight": "kg", "bmi": "kg/m2"}


def _check_measure_sex(measure: str, sex: str) -> None:
    if measure not in _VALID_MEASURES:
        raise HTTPException(422, f"measure must be one of {_VALID_MEASURES}")
    if sex not in _VALID_SEXES:
        raise HTTPException(422, f"sex must be one of {_VALID_SEXES}")


@lru_cache(maxsize=None)
def _cached_series(measure: str, sex: str, age_min: float, age_max: float, render_step: float):
    # Each build is ~2-3s (WHO lookups dominate); computed once per
    # (measure, sex, range, step) combination and reused for every request.
    return curve_builder.build_chart_series(measure, sex, age_min, age_max, render_step)


@router.get("/chart")
def get_chart_series(
    measure: str = Query(...),
    sex: str = Query(...),
    age_min: float = Query(0.0, ge=0.0),
    age_max: float = Query(18.0, le=19.0),
    render_step: float = Query(0.1, ge=0.02, le=0.5),
) -> dict[str, Any]:
    """Dense (age, value) series for all 7 standard centiles, ready to plot.
    Age in years, value in the measure's clinical unit (see `unit`)."""
    _check_measure_sex(measure, sex)
    series = _cached_series(measure, sex, age_min, age_max, render_step)
    return {
        "measure": measure,
        "sex": sex,
        "unit": _UNITS[measure],
        "age_min": age_min,
        "age_max": age_max,
        "reference": "WHO (<5y) blended with IAP 2015 India (5-18y), 4.0-5.0y transition",
        "centiles": curve_builder.series_to_json(series),
    }


@router.get("/point")
def get_point_metrics(
    measure: str = Query(...),
    sex: str = Query(...),
    age: float = Query(..., ge=0.0, le=19.0),
    value: float = Query(..., gt=0.0),
) -> dict[str, Any]:
    """z-score / percentile / formatted label for one patient measurement."""
    _check_measure_sex(measure, sex)
    z = blend.unified_z_for_value(measure, sex, age, value)
    median = blend.unified_value_at_z(measure, sex, age, 0.0)
    if z is None:
        return {"available": False, "measure": measure, "sex": sex, "age": age, "value": value}

    from scipy.stats import norm

    pct = float(min(99.9, max(0.1, norm.cdf(z) * 100)))
    unit = _UNITS[measure]
    return {
        "available": True,
        "measure": measure,
        "sex": sex,
        "age": age,
        "value": value,
        "unit": unit,
        "z": round(z, 4),
        "percentile": round(pct, 1),
        "median_for_age": round(median, 3) if median is not None else None,
        "label": f"{value:.1f} {unit} @ {age:.1f} y",
    }


@router.get("/bmi-cutoffs")
def get_bmi_cutoffs(sex: str = Query(...), age: float = Query(..., ge=0.0, le=19.0)) -> dict[str, Any]:
    """IAP/IOTF adult-equivalent 23 & 27 kg/m^2 overweight/obesity cutoffs."""
    if sex not in _VALID_SEXES:
        raise HTTPException(422, f"sex must be one of {_VALID_SEXES}")
    cutoffs = blend.unified_bmi_cutoffs(sex, age)
    if cutoffs is None:
        return {"available": False, "sex": sex, "age": age}
    return {"available": True, "sex": sex, "age": age, "overweight_cutoff": round(cutoffs[0], 2), "obesity_cutoff": round(cutoffs[1], 2)}


@router.get("/reference-stats")
def get_reference_stats(measure: str = Query(...), sex: str = Query(...), age: float = Query(..., ge=0.0, le=19.0)) -> dict[str, Any]:
    """Single-point reference distribution (median + selected centiles) at one
    age -- e.g. used by the bone-age module's predicted-adult-height context
    (WHO 19y adult height), which needs a distribution summary rather than a
    scored patient measurement or a dense chart series."""
    if measure not in _VALID_MEASURES or sex not in _VALID_SEXES:
        raise HTTPException(422, "invalid measure/sex")
    out = {"measure": measure, "sex": sex, "age": age, "unit": _UNITS[measure]}
    for pct, z in curve_builder.Z_FOR_CENTILE.items():
        v = blend.unified_value_at_z(measure, sex, age, z)
        out[f"p{pct}"] = round(v, 3) if v is not None else None
    out["available"] = out["p50"] is not None
    return out


@router.get("/validate")
def get_validation_report() -> dict[str, Any]:
    """QA report: edge slope continuity, monotonic age, centile ordering,
    and IAP source-table reproduction. Used by CI/tests and available here
    for manual inspection during development."""
    report = validation.run_full_validation()
    return {"all_pass": report.all_pass, "failures": report.failures, "details": report.details}

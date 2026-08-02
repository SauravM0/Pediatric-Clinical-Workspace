"""Growth chart API -- the only place chart data comes from. All percentile
math (LMS transform, WHO/IAP blending, PCHIP dense sampling) happens in
``backend/growth``; this router just serializes it. The frontend must not
recompute percentiles itself -- see frontend/index.html's growth section.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends, APIRouter, HTTPException, Query

from backend.growth import (
    blend, curve_builder, iap_lms_reference, lms_core, measures,
    reference_data, validation,
)

from backend.security.deps import clinical_access

# Every route in this router requires an authenticated user with at least
# read access; mutating methods require write access (security phase, C.1).
# Applied at the router so a route added later is protected by construction.
router = APIRouter(prefix="/api/growth", tags=["growth"], dependencies=[Depends(clinical_access)])

# Canonical registry (M0.3) -- previously re-declared here and in five other
# modules, so a new measure could be served by the API but never validated.
_VALID_MEASURES = measures.MEASURE_KEYS
_VALID_SEXES = ("boys", "girls")
_UNITS = measures.UNITS


def _check_measure_sex(measure: str, sex: str) -> None:
    if measure not in _VALID_MEASURES:
        raise HTTPException(422, f"measure must be one of {_VALID_MEASURES}")
    if sex not in _VALID_SEXES:
        raise HTTPException(422, f"sex must be one of {_VALID_SEXES}")


@lru_cache(maxsize=256)
def _cached_series(measure: str, sex: str, age_min: float, age_max: float,
                   render_step: float, fingerprint: str):
    # Each build is ~2-3s (WHO lookups dominate); computed once per
    # (measure, sex, range, step) combination and reused for every request.
    #
    # `fingerprint` is not used in the body -- it is a CACHE KEY (M0.4). It is
    # the digest of every reference data file plus the pinned rcpchgrowth
    # version, so any change to the underlying reference data yields a
    # different key and the stale curve becomes unreachable instead of being
    # served indefinitely. Threading it through the signature makes staleness
    # structurally impossible rather than something to remember to invalidate.
    #
    # maxsize is bounded (was None): the key space grows with measures x sexes x
    # age ranges x render steps x data versions, all caller-supplied.
    return curve_builder.build_chart_series(measure, sex, age_min, age_max, render_step)


def _series(measure: str, sex: str, age_min: float, age_max: float, render_step: float):
    """Cached chart series, keyed on the current reference-data fingerprint."""
    return _cached_series(measure, sex, age_min, age_max, render_step,
                          reference_data.fingerprint())


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
    series = _series(measure, sex, age_min, age_max, render_step)
    return {
        "measure": measure,
        "sex": sex,
        "unit": _UNITS[measure],
        "age_min": age_min,
        "age_max": age_max,
        # Honest label: the 3.0-5.0y span is a PRODUCT-DERIVED composite (a
        # monotone WHO<->IAP bridge), not a published WHO or Khadilkar curve
        # (audit GC-1/GC-2). Window is 3.0-5.0y (blend.BLEND_LO..BLEND_HI).
        "reference": "Product-derived WHO/IAP composite · WHO 2006 <3y · IAP 2015 India 5–18y",
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

    # Reporting bound (M1.2). The engine returns the mathematically exact z for
    # any positive value, but far outside the reference the number stops being a
    # clinical statement -- a 40cm height for a 6-year-old scores z = -12.9,
    # which reads as a precise finding rather than a data-entry error. Clamp for
    # display and flag it, so the UI can say "outside reference range" instead.
    z_reported, out_of_range = lms_core.clamp_reportable_z(z)

    pct = float(min(99.9, max(0.1, norm.cdf(z_reported) * 100)))
    unit = _UNITS[measure]
    return {
        "available": True,
        "measure": measure,
        "sex": sex,
        "age": age,
        "value": value,
        "unit": unit,
        "z": round(z_reported, 4),
        "percentile": round(pct, 1),
        # True when the measurement fell outside the reportable range and `z`
        # was clamped: treat it as "outside reference range", not as a result.
        "out_of_reference_range": out_of_range,
        "z_reportable_range": [lms_core.Z_REPORTABLE_MIN, lms_core.Z_REPORTABLE_MAX],
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
    return {
        "all_pass": report.all_pass,
        "failures": report.failures,
        # Which reference data this verdict was produced against (M0.4). A QA
        # result is only meaningful alongside the inputs that produced it --
        # this is what makes a pass/fail attributable to a specific data version.
        "reference_data": reference_data.describe(),
        # Whether the published IAP L,M,S path is live, and if not, why (M1.1).
        # Surfaced because "which reference produced this" is the first thing a
        # reviewer needs, and the answer is currently "a fit, not the paper's
        # own parameters".
        "iap_lms": iap_lms_reference.lms_status(),
        "details": report.details,
    }

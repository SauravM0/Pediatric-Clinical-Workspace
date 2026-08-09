"""Adult height: genetic target, and predicted adult height (M5).

These are two DIFFERENT quantities and conflating them is an open audit finding
(F-1) against this product:

* **Mid-parental target height** is where a child's genetics point. It says
  nothing about whether this particular child is on track for it.
* **Predicted adult height** is where THIS child is heading, given their current
  size and maturity.

A child can be tracking perfectly toward a short target, or falling badly short
of a tall one. Presenting one under the other's name loses exactly the
information a clinician wants. They are returned as separate objects with
separate labels, and the API never merges them.

Mid-parental target is an open formula (Tanner) and works today.

Khamis-Roche -- predicted adult height from the child's height, weight and
mid-parental height, with NO radiograph -- is implemented as a gated table
loader following the same discipline as the licensed TW3 tables: the published
sex- and age-specific regression coefficients (Khamis & Roche, Pediatrics 1994)
are not bundled, so prediction stays disabled and says so rather than running on
invented numbers. Fabricating regression coefficients is precisely the failure
this project already carries in its digitized TW3 curve; it is not repeated here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

_COEFFICIENTS_PATH = Path(__file__).with_name("khamis_roche_coefficients.json")

# Khamis-Roche is validated for ages 4.0-17.5 years. Outside that it returns
# nothing rather than extrapolating.
KR_MIN_AGE_YEARS = 4.0
KR_MAX_AGE_YEARS = 17.5
# 90% of predictions fall within this of true adult height. Published WITH every
# prediction: a bare point estimate reads as far more precise than it is.
KR_INTERVAL_CM = 5.3


@dataclass(frozen=True)
class TargetHeight:
    target_cm: float
    range_low_cm: float
    range_high_cm: float
    source_quality: str          # "measured" | "reported" | "unknown"
    caveat: str


@dataclass(frozen=True)
class AdultHeightPrediction:
    available: bool
    predicted_cm: Optional[float]
    interval_cm: Optional[float]
    method: str
    status: str


def mid_parental_target(sex: str, mother_cm: Optional[float], father_cm: Optional[float],
                        *, source: Optional[str] = None) -> Optional[TargetHeight]:
    """Tanner mid-parental target height and its corridor.

    Returns None when either parental height is missing -- a target computed
    from one parent is not a target.
    """
    if not mother_cm or not father_cm:
        return None
    from .rules import T

    offset = T("mid_parental_sex_offset_cm")
    half = T("target_range_half_width_cm")
    target = ((father_cm + mother_cm) + (offset if sex == "boys" else -offset)) / 2.0

    quality = source if source in ("measured", "reported") else "unknown"
    caveat = (
        "Parental heights were MEASURED." if quality == "measured" else
        "Parental heights are self-reported and are typically over-stated, so "
        "this target is probably a little high. Measure them if the target is "
        "influencing a decision."
    )
    return TargetHeight(round(target, 1), round(target - half, 1), round(target + half, 1),
                        quality, caveat)


@lru_cache(maxsize=1)
def _coefficients() -> Optional[dict]:
    if not _COEFFICIENTS_PATH.exists():
        return None
    try:
        data = json.loads(_COEFFICIENTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if data.get("coefficients") else None


def khamis_roche_available() -> bool:
    return _coefficients() is not None


def predict_adult_height(sex: str, age_years: Optional[float], height_cm: Optional[float],
                         weight_kg: Optional[float], mother_cm: Optional[float],
                         father_cm: Optional[float]) -> AdultHeightPrediction:
    """Khamis-Roche predicted adult height, or an explanation of why not."""
    method = "Khamis-Roche (no radiograph)"

    if not khamis_roche_available():
        return AdultHeightPrediction(
            False, None, None, method,
            "Khamis-Roche coefficients are not bundled. The published sex- and "
            "age-specific regression coefficients (Khamis & Roche, Pediatrics "
            "1994;94:504-7) must be entered once into "
            "backend/clinical/khamis_roche_coefficients.json. Prediction stays "
            "disabled rather than running on invented coefficients.",
        )

    if None in (age_years, height_cm, weight_kg, mother_cm, father_cm):
        return AdultHeightPrediction(False, None, None, method,
                                     "requires age, height, weight and both parental heights")
    if not (KR_MIN_AGE_YEARS <= age_years <= KR_MAX_AGE_YEARS):
        return AdultHeightPrediction(
            False, None, None, method,
            f"validated for ages {KR_MIN_AGE_YEARS}-{KR_MAX_AGE_YEARS} only; "
            f"age {age_years:.1f} is outside that range and is not extrapolated",
        )

    table = _coefficients()["coefficients"].get(sex, {})
    key = f"{round(age_years * 2) / 2:.1f}"       # nearest half-year
    row = table.get(key)
    if row is None:
        return AdultHeightPrediction(False, None, None, method,
                                     f"no coefficient row for {sex} at age {key}")

    mid_parent = (mother_cm + father_cm) / 2.0
    predicted = (float(row["intercept"])
                 + float(row["height"]) * height_cm
                 + float(row["weight"]) * weight_kg
                 + float(row["midparent"]) * mid_parent)
    return AdultHeightPrediction(True, round(predicted, 1), KR_INTERVAL_CM, method, "ok")


def predict_from_bone_age(sex: str, height_cm: Optional[float],
                          bone_age_years: Optional[float],
                          bone_age_uncertainty_years: Optional[float] = None) -> dict:
    """TW3 percentage-of-adult-height, when a radiograph and licensed table exist.

    Kept behind this thin adapter so ``clinical`` does not grow a hard dependency
    on the TW3 package's table model -- the import is local and the failure mode
    when the table is absent is a status string, not an exception.
    """
    from backend.tw3 import adult_height as tw3_adult_height
    from backend.tw3.letters_scoring import LetterTablesError, load_letter_tables

    try:
        tables = load_letter_tables()
    except LetterTablesError as exc:
        return {"available": False, "predicted_cm": None, "range_cm": None,
                "method": "TW3 percentage of adult height attained",
                "status": f"licensed tables unreadable: {exc}"}

    r = tw3_adult_height.predict(sex, height_cm or 0.0, bone_age_years, tables,
                                 bone_age_uncertainty_years=bone_age_uncertainty_years)
    return {
        "available": r.available,
        "predicted_cm": r.predicted_cm,
        "range_cm": None if r.range_cm is None else list(r.range_cm),
        "percent_attained": r.percent_attained,
        "bone_age_years": r.bone_age_years,
        "method": r.method,
        "status": r.status,
        "caveat": r.caveat or None,
    }


def adult_height_summary(sex: str, age_years: Optional[float], height_cm: Optional[float],
                         weight_kg: Optional[float], mother_cm: Optional[float],
                         father_cm: Optional[float],
                         parental_source: Optional[str] = None,
                         bone_age_years: Optional[float] = None,
                         bone_age_uncertainty_years: Optional[float] = None) -> dict:
    """All three quantities, deliberately side by side and separately labelled.

    The third -- prediction from skeletal maturity -- was computed by
    ``backend/tw3/adult_height.py`` and surfaced nowhere until M2C's ingestion
    step. It is the only one of the three that responds to a child being early
    or late maturing, so omitting it made the licensed table pointless even once
    a clinic entered it.
    """
    target = mid_parental_target(sex, mother_cm, father_cm, source=parental_source)
    prediction = predict_adult_height(sex, age_years, height_cm, weight_kg,
                                      mother_cm, father_cm)
    from_bone_age = predict_from_bone_age(sex, height_cm, bone_age_years,
                                          bone_age_uncertainty_years)
    return {
        "from_bone_age": {
            "label": "Predicted adult height from skeletal maturity (TW3)",
            **from_bone_age,
        },
        "genetic_target": None if target is None else {
            "label": "Mid-parental target height (genetic potential)",
            "target_cm": target.target_cm,
            "range_cm": [target.range_low_cm, target.range_high_cm],
            "parental_height_source": target.source_quality,
            "caveat": target.caveat,
        },
        "predicted_adult_height": {
            "label": "Predicted adult height (this child's trajectory)",
            "available": prediction.available,
            "predicted_cm": prediction.predicted_cm,
            "interval_cm": prediction.interval_cm,
            "interval_note": (
                f"90% of predictions fall within +/-{KR_INTERVAL_CM} cm. Quote the "
                "interval, never the point estimate alone."
            ) if prediction.available else None,
            "method": prediction.method,
            "status": prediction.status,
        },
        "note": "These are three different quantities and must never be merged. "
                "The target is where genetics point. The Khamis-Roche prediction "
                "is where this child is heading, without a radiograph. The "
                "bone-age prediction uses the child's actual skeletal maturity "
                "and is the only one that responds to early or late maturing -- "
                "the most informative of the three when a film exists. A child "
                "can track perfectly toward a short target, or fall short of a "
                "tall one; never present one as the other.",
    }

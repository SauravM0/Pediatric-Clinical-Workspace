"""Blood-pressure category for a single reading (step 2).

Replaces a "mean arterial pressure" card that labelled any MAP of 70-100 mmHg
"Normal" at every age -- including children, whose normal pressures are much
lower and depend on age, sex and height.

From age 13 the adolescent and adult thresholds are the same static numbers:

  * Adolescents 13-17: Flynn JT et al. Pediatrics 2017;140:e20171904 (AAP 2017).
  * Adults >= 18: Whelton PK et al. Hypertension 2018;71:e13-e115 (ACC/AHA 2017).

    Normal     SBP < 120  and DBP < 80
    Elevated   SBP 120-129 and DBP < 80
    Stage 1    SBP 130-139 or  DBP 80-89
    Stage 2    SBP >= 140  or  DBP >= 90
    Severe     SBP >= 180  or  DBP >= 120   (urgent evaluation)

Under 13 the AAP 2017 classification is by CENTILE for age, sex and height
(normative tables 4 and 5 of the guideline). Those tables are not bundled and are
not reconstructed from memory: once a clinic installs its double-checked
transcription (``python -m backend.vitals.ingest_aap_bp``, see aap_bp_reference)
ages 1-12 are classified from it, by the child's height in cm. Until then -- and
always under 1 year, where the tables stop -- a child under 13 gets
``available: False`` with the reason instead of an adult label.

Every result is one reading. Hypertension is diagnosed on repeated readings
(three visits in children, AAP 2017), never from one measurement.
"""
from __future__ import annotations

from typing import Optional

from . import aap_bp_reference

STATIC_THRESHOLD_MIN_AGE = 13.0
ADULT_AGE = 18.0


def mean_arterial_pressure(sbp: float, dbp: float) -> float:
    return dbp + (sbp - dbp) / 3.0


def _category(sbp: float, dbp: float) -> tuple[str, str]:
    if sbp >= 180 or dbp >= 120:
        return "severe", "Severe elevation — urgent evaluation"
    if sbp >= 140 or dbp >= 90:
        return "stage2", "Stage 2 hypertension range"
    if sbp >= 130 or dbp >= 80:
        return "stage1", "Stage 1 hypertension range"
    if sbp >= 120:
        return "elevated", "Elevated"
    return "normal", "Normal"


def assess(*, age: Optional[float], sbp: Optional[float], dbp: Optional[float],
           sex: Optional[str] = None, height_cm: Optional[float] = None) -> dict:
    if age is None or sbp is None or dbp is None:
        return {"available": False, "reason": "Age, systolic and diastolic BP are required."}
    if dbp >= sbp:
        return {"available": False, "reason": "Diastolic must be lower than systolic."}

    mapp = round(mean_arterial_pressure(sbp, dbp), 1)
    single = "Single reading: hypertension is diagnosed only on repeated measurements."
    if age < STATIC_THRESHOLD_MIN_AGE:
        if age < 1.0:
            return {"available": False, "map": mapp, "reason": (
                "The AAP 2017 tables start at age 1; infant blood pressure needs "
                "neonatal/infant norms. No category is given.")}
        if not aap_bp_reference.available():
            return {"available": False, "map": mapp, "reason": (
                "Under 13, blood pressure is classified by centile for age, sex and height "
                "(AAP 2017 normative tables), which this workspace does not yet hold. "
                "No category is given rather than an adult one.")}
        if sex not in ("boys", "girls") or height_cm is None:
            return {"available": False, "map": mapp, "reason": (
                "Under 13 the category depends on sex and height: enter both.")}
        c = aap_bp_reference.classify(sex, age, height_cm, sbp, dbp)
        t = c["thresholds"]
        return {
            "available": True, "category": c["category"], "category_label": c["category_label"],
            "map": mapp, "guideline": "AAP 2017 centile tables (age 1-12, by height)",
            "citation": "Flynn JT et al. Pediatrics 2017;140:e20171904, Tables 4-5",
            "thresholds": t,
            "notes": [single,
                      f"Thresholds for age {t['age_row']} at {height_cm:g} cm: 90th "
                      f"{t['sbp_p90']:g}/{t['dbp_p90']:g}, 95th {t['sbp_p95']:g}/{t['dbp_p95']:g} mmHg "
                      "(interpolated by height in cm; the table's centile columns are CDC, not IAP)."],
        }

    code, label = _category(sbp, dbp)
    adult = age >= ADULT_AGE
    notes = [single]
    if adult:
        notes.append("Indian guidelines (and ESH/ISH) define hypertension from 140/90 mmHg; "
                     "the ACC/AHA 2017 stage 1 band (130-139/80-89) is lower.")
    return {
        "available": True, "category": code, "category_label": label, "map": mapp,
        "guideline": ("ACC/AHA 2017 (adults)" if adult
                      else "AAP 2017 (adolescents aged 13 and over)"),
        "citation": ("Whelton PK et al. Hypertension 2018;71:e13-e115" if adult
                     else "Flynn JT et al. Pediatrics 2017;140:e20171904"),
        "notes": notes,
    }

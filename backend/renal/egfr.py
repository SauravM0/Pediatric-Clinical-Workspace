"""Estimated GFR and KDIGO CKD staging (step 2: moved out of the browser).

This used to be ~20 lines inside a React component: every equation applied at
any age, KDIGO G3 not split into G3a/G3b, no albuminuria in the staging, and
"G1 Normal" printed for anyone with an eGFR >= 90 whether or not there was any
marker of kidney damage. It lives here now so there is ONE implementation, it is
tested, and every age limit is enforced rather than footnoted.

Equations (serum creatinine in mg/dL, assumed IDMS-traceable / enzymatic):

* CKD-EPI 2021 creatinine, race-free -- adults >= 18 y.
  Inker LA et al. N Engl J Med 2021;385:1737-49.
      eGFR = 142 * min(Scr/k,1)^a * max(Scr/k,1)^-1.200 * 0.9938^age * 1.012[F]
      k = 0.7 (F) / 0.9 (M);  a = -0.241 (F) / -0.302 (M)
* Bedside Schwartz -- children 1 to < 18 y.
  Schwartz GJ et al. J Am Soc Nephrol 2009;20:629-37.
      eGFR = 0.413 * height(cm) / Scr
* CKiD U25 creatinine -- ages 1 to 25 y; sex- and age-specific constant, so it
  does not overestimate in adolescent boys as bedside Schwartz does.
  Pierce CB et al. Kidney Int 2021;99:948-56.
      eGFR = K * height(m) / Scr
      K (male)   = 39.0 * 1.008^(age-12)  (<12),  39.0 * 1.045^(age-12)  (12-18),  50.8 (>=18)
      K (female) = 36.1 * 1.008^(age-12)  (<12),  36.1 * 1.023^(age-12)  (12-18),  41.4 (>=18)
* Cockcroft-Gault creatinine CLEARANCE (mL/min, not /1.73 m2) -- adults, for
  drug dosing. Cockcroft DW, Gault MH. Nephron 1976;16:31-41.
* MDRD (IDMS, 175) -- adults; legacy, superseded by CKD-EPI. Shown only as a
  comparison because older records and some drug labels still use it.

Which equation is PRIMARY is fixed here, not chosen per request: bedside
Schwartz under 18 (the equation Indian paediatric nephrology uses and the one
this product has always reported), CKD-EPI 2021 from 18. CKiD U25 is reported
beside them from 1 to 25 because it is the better-validated equation across
the adolescent / young-adult transition, where the other two disagree most.

Under 1 year no equation is returned: GFR matures over the first two years and
none of these equations was derived there. KDIGO GFR categories G1-G5 apply
from 2 years; below that a value is compared with age norms instead.
"""
from __future__ import annotations

from typing import Optional

SEXES = ("boys", "girls")

MIN_EQUATION_AGE = 1.0          # no creatinine equation below this
KDIGO_CATEGORY_MIN_AGE = 2.0    # G1-G5 are adult-derived; from 2 y only
ADULT_AGE = 18.0
U25_MAX_AGE = 25.0

# ── equations ──────────────────────────────────────────────────────────────


def ckd_epi_2021(scr: float, age: float, sex: str) -> float:
    female = sex == "girls"
    k = 0.7 if female else 0.9
    a = -0.241 if female else -0.302
    ratio = scr / k
    value = 142.0 * min(ratio, 1.0) ** a * max(ratio, 1.0) ** -1.200 * 0.9938 ** age
    return value * (1.012 if female else 1.0)


def bedside_schwartz(scr: float, height_cm: float) -> float:
    return 0.413 * height_cm / scr


def ckid_u25_k(age: float, sex: str) -> float:
    if sex == "boys":
        if age < 12:
            return 39.0 * 1.008 ** (age - 12)
        if age < 18:
            return 39.0 * 1.045 ** (age - 12)
        return 50.8
    if age < 12:
        return 36.1 * 1.008 ** (age - 12)
    if age < 18:
        return 36.1 * 1.023 ** (age - 12)
    return 41.4


def ckid_u25(scr: float, height_cm: float, age: float, sex: str) -> float:
    return ckid_u25_k(age, sex) * (height_cm / 100.0) / scr


def cockcroft_gault(scr: float, age: float, weight_kg: float, sex: str) -> float:
    value = (140.0 - age) * weight_kg / (72.0 * scr)
    return value * (0.85 if sex == "girls" else 1.0)


def mdrd_idms(scr: float, age: float, sex: str) -> float:
    value = 175.0 * scr ** -1.154 * age ** -0.203
    return value * (0.742 if sex == "girls" else 1.0)


# ── KDIGO categories ───────────────────────────────────────────────────────

# (code, lower bound inclusive, label)
_GFR_CATEGORIES = (
    ("G1", 90.0, "Normal or high"),
    ("G2", 60.0, "Mildly decreased"),
    ("G3a", 45.0, "Mildly to moderately decreased"),
    ("G3b", 30.0, "Moderately to severely decreased"),
    ("G4", 15.0, "Severely decreased"),
    ("G5", 0.0, "Kidney failure"),
)
_GFR_RANGES = {"G1": ">= 90", "G2": "60-89", "G3a": "45-59", "G3b": "30-44",
               "G4": "15-29", "G5": "< 15"}

ALBUMINURIA = {
    "A1": "Normal to mildly increased (ACR < 30 mg/g)",
    "A2": "Moderately increased (ACR 30-300 mg/g)",
    "A3": "Severely increased (ACR > 300 mg/g)",
}

# KDIGO 2012 / 2024 prognosis heat map: risk of adverse outcomes by G x A.
_HEAT_MAP = {
    "G1":  {"A1": "low",       "A2": "moderate",  "A3": "high"},
    "G2":  {"A1": "low",       "A2": "moderate",  "A3": "high"},
    "G3a": {"A1": "moderate",  "A2": "high",      "A3": "very_high"},
    "G3b": {"A1": "high",      "A2": "very_high", "A3": "very_high"},
    "G4":  {"A1": "very_high", "A2": "very_high", "A3": "very_high"},
    "G5":  {"A1": "very_high", "A2": "very_high", "A3": "very_high"},
}
RISK_LABELS = {"low": "Low risk", "moderate": "Moderately increased risk",
               "high": "High risk", "very_high": "Very high risk"}


def gfr_category(egfr: float) -> str:
    for code, lower, _ in _GFR_CATEGORIES:
        if egfr >= lower:
            return code
    return "G5"


def _category_label(code: str) -> str:
    return next(label for c, _, label in _GFR_CATEGORIES if c == code)


# ── assessment ─────────────────────────────────────────────────────────────


def _eq(name: str, value: float, unit: str, citation: str) -> dict:
    return {"equation": name, "value": round(value, 1), "unit": unit, "citation": citation}


def assess(*, age: Optional[float], sex: Optional[str], scr_mg_dl: Optional[float],
           height_cm: Optional[float] = None, weight_kg: Optional[float] = None,
           albuminuria: Optional[str] = None) -> dict:
    """eGFR by the age-appropriate equation, comparison equations, and KDIGO
    staging. Refuses (``available: False`` with a reason) rather than applying
    an equation outside the population it was derived in."""
    if sex not in SEXES:
        return {"available": False, "reason": "Biological sex is required."}
    if age is None or scr_mg_dl is None or scr_mg_dl <= 0:
        return {"available": False, "reason": "Age and serum creatinine are required."}
    if albuminuria is not None and albuminuria not in ALBUMINURIA:
        return {"available": False, "reason": f"Unknown albuminuria category {albuminuria!r}."}
    if age < MIN_EQUATION_AGE:
        return {"available": False, "reason": (
            "No creatinine eGFR equation is validated under 1 year: GFR is still "
            "maturing (and in the first days of life creatinine reflects the "
            "mother's). Compare with age-specific normal values or measure GFR.")}

    paediatric = age < ADULT_AGE
    caveats: list[str] = []
    alternatives: list[dict] = []

    if paediatric:
        if height_cm is None or height_cm <= 0:
            return {"available": False, "reason": "Height is required for paediatric eGFR (Schwartz)."}
        primary = _eq("Bedside Schwartz (2009)", bedside_schwartz(scr_mg_dl, height_cm),
                      "mL/min/1.73 m²", "Schwartz GJ et al. J Am Soc Nephrol 2009;20:629-37")
    else:
        primary = _eq("CKD-EPI 2021 (race-free)", ckd_epi_2021(scr_mg_dl, age, sex),
                      "mL/min/1.73 m²", "Inker LA et al. N Engl J Med 2021;385:1737-49")

    if age <= U25_MAX_AGE and height_cm is not None and height_cm > 0:
        alternatives.append(_eq("CKiD U25", ckid_u25(scr_mg_dl, height_cm, age, sex),
                                "mL/min/1.73 m²", "Pierce CB et al. Kidney Int 2021;99:948-56"))
    if not paediatric:
        if weight_kg is not None and weight_kg > 0:
            alternatives.append(_eq("Cockcroft-Gault creatinine clearance",
                                    cockcroft_gault(scr_mg_dl, age, weight_kg, sex), "mL/min",
                                    "Cockcroft DW, Gault MH. Nephron 1976;16:31-41"))
            caveats.append("Cockcroft-Gault uses actual body weight and is not normalised "
                           "to 1.73 m²; it is for drug dosing, not CKD staging.")
        alternatives.append(_eq("MDRD (IDMS, legacy)", mdrd_idms(scr_mg_dl, age, sex),
                                "mL/min/1.73 m²", "Levey AS et al. Clin Chem 2007;53:766-72"))

    if paediatric and age >= 12:
        caveats.append("Bedside Schwartz uses one constant for both sexes and tends to "
                       "overestimate GFR in adolescent boys; CKiD U25 is shown beside it.")
    if ADULT_AGE <= age <= U25_MAX_AGE:
        caveats.append("Between 18 and 25 the paediatric and adult equations disagree; "
                       "CKiD U25 was validated across this transition.")
    caveats.append("Assumes an IDMS-traceable (enzymatic) creatinine assay. A Jaffe "
                   "assay reads higher in children and lowers the estimate.")
    caveats.append("An eGFR assumes a steady state; it is not valid in acute kidney injury.")

    egfr = primary["value"]
    result = {"available": True, "paediatric": paediatric, "primary": primary,
              "alternatives": alternatives, "caveats": caveats}

    if age < KDIGO_CATEGORY_MIN_AGE:
        result.update({"gfr_category": None, "albuminuria_category": albuminuria,
                       "kdigo_risk": None,
                       "interpretation": ("KDIGO G1-G5 categories apply from age 2. "
                                          "Compare this value with age-specific norms.")})
        return result

    g = gfr_category(egfr)
    marker = egfr < 60 or albuminuria in ("A2", "A3")
    if albuminuria is None:
        risk = None
        interpretation = (
            f"{g} by eGFR. Albuminuria not recorded: the KDIGO risk category needs "
            "a urine albumin-to-creatinine ratio"
            + (", and CKD cannot be excluded without it." if not marker else ".")
        )
    else:
        risk = _HEAT_MAP[g][albuminuria]
        interpretation = (
            f"{g}{albuminuria}: {RISK_LABELS[risk].lower()}." if marker
            else f"{g}{albuminuria}: no marker of CKD in this measurement."
        )
    if marker:
        interpretation += (" Consistent with CKD only if persistent for more than "
                           "3 months (KDIGO); repeat to confirm chronicity.")
    elif g in ("G1", "G2"):
        # G1/G2 alone is NOT CKD. The old panel printed "Stage G1 · Normal" as a
        # CKD stage for any healthy child.
        interpretation += " G1/G2 without albuminuria or other damage markers is not CKD."

    result.update({
        "gfr_category": {"code": g, "label": _category_label(g), "range": _GFR_RANGES[g]},
        "albuminuria_category": (None if albuminuria is None
                                 else {"code": albuminuria, "label": ALBUMINURIA[albuminuria]}),
        "kdigo_risk": None if risk is None else {"level": risk, "label": RISK_LABELS[risk]},
        "ckd_marker_present": marker,
        "interpretation": interpretation,
    })
    return result

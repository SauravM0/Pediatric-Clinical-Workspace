"""QRISK3-2017 ten-year cardiovascular-risk model (Hippisley-Cox et al., BMJ 2017).

Relocated from the frontend to a single authoritative backend module (audit F-3).
Coefficients are the ClinRisk open-source release (qrisk.org, GNU LGPL), and were
verified equal to the validated CRAN `QRISK3` package's constants (survivor,
ethnicity/smoking arrays, age/BMI/diabetes coefficients, and every centering
constant) -- see tests/cvd/test_qrisk3.py.

This module ADDS the two safeguards the audit required (F-3):
  * eligibility is enforced here, not merely caveated -- QRISK3 is validated only
    for ages 25-84 (and needs sex + a computable BMI); outside that it returns
    ``available: False`` and NO score;
  * every input filled with a population default (cholesterol ratio, systolic BP,
    its SD, Townsend score) is reported in ``imputed_fields`` so a
    precise-looking risk is never silently produced from incomplete data.

QRISK3 is a UK-derived ADULT model. It is not paediatric and not India-specific;
interpret alongside Indian guidance (Lipid Association of India / ICMR).
"""
from __future__ import annotations

import math
from typing import Optional

QRISK3_ELIGIBLE_AGE = (25, 84)

# ── ClinRisk QRISK3-2017 coefficients (verified vs CRAN QRISK3) ───────────────
FEMALE = {
    "survivor": 0.988876402378082,
    "Iethrisk": [0, 0, 0.2804031433299542, 0.5629899414207540, 0.2959000085111652,
                 0.0727853798779825, -0.1707213550885732, -0.3937104331487497,
                 -0.3263249528353027, -0.1712705688324178],
    "Ismoke": [0, 0.1338683378654626, 0.5620085801243854, 0.6674959337750255, 0.8494817764483085],
    "c": {"age1": -8.1388109247726188, "age2": 0.7973337668969910,
          "bmi1": 0.2923609227546005, "bmi2": -4.1513300213837665,
          "rati": 0.1533803582080255, "sbp": 0.0131314884071034, "sbps5": 0.0078894541014586,
          "town": 0.0772237905885901, "AF": 1.5923354969269663, "atypicalantipsy": 0.2523764207011556,
          "corticosteroids": 0.5952072530460185, "migraine": 0.3012672608703450, "ra": 0.2136480343518194,
          "renal": 0.6519456949384583, "semi": 0.1255530805882018, "sle": 0.7588093865426769,
          "treatedhyp": 0.5093159368342300, "type1": 1.7267977510537347, "type2": 1.0688773244615468,
          "fh_cvd": 0.4544531902089621},
    "i1": {"s1": -4.7057161785851891, "s2": -2.7430383403573337, "s3": -0.8660808882939218, "s4": 0.9024156236971065,
           "AF": 19.9380348895465610, "corticosteroids": -0.9840804523593628, "migraine": 1.7634979587872999,
           "renal": -3.5874047731694114, "sle": 19.6903037386382920, "treatedhyp": 11.8728097339218120,
           "type1": -1.2444332714320747, "type2": 6.8652342000009599, "bmi1": 23.8026234121417420,
           "bmi2": -71.1849476920870070, "fh_cvd": 0.9946780794043513, "sbp": 0.0341318423386155, "town": -1.0301180802035639},
    "i2": {"s1": -0.0755892446431930, "s2": -0.1195119287486707, "s3": -0.1036630639757192, "s4": -0.1399185359171839,
           "AF": -0.0761826510111625, "corticosteroids": -0.1200536494674247, "migraine": -0.0655869178986999,
           "renal": -0.2268887308644251, "sle": 0.0773479496790163, "treatedhyp": 0.0009685782358817,
           "type1": -0.2872406462448895, "type2": -0.0971122525906955, "bmi1": 0.5236995893366443,
           "bmi2": 0.0457441901223238, "fh_cvd": -0.0768850516984230, "sbp": -0.0015082501423272, "town": -0.0315934146749623},
    "center": {"rati": 3.476326465606690, "sbp": 123.130012512207030, "sbps5": 9.002537727355957, "town": 0.392308831214905},
}
MALE = {
    "survivor": 0.977268040180206,
    "Iethrisk": [0, 0, 0.2771924876030828, 0.4744636071493127, 0.5296172991968937,
                 0.0351001591862990, -0.3580789966932792, -0.4005648523216514,
                 -0.4152279288983017, -0.2632134813474997],
    "Ismoke": [0, 0.1912822286338898, 0.5524158819264555, 0.6383505302750607, 0.7898381988185802],
    "c": {"age1": -17.8397816660055750, "age2": 0.0022964880605765,
          "bmi1": 2.4562776660536358, "bmi2": -8.3011122314711354,
          "rati": 0.1734019685632711, "sbp": 0.0129101265425533, "sbps5": 0.0102519142912905,
          "town": 0.0332682012772873, "AF": 0.8820923692805466, "atypicalantipsy": 0.1304687985517351,
          "corticosteroids": 0.4548539975044554, "impotence2": 0.2225185908670538, "migraine": 0.2558417807415991,
          "ra": 0.2097065801395657, "renal": 0.7185326128827438, "semi": 0.1213303988204716, "sle": 0.4401572174457522,
          "treatedhyp": 0.5165987108269547, "type1": 1.2343425521675175, "type2": 0.8594207143093222,
          "fh_cvd": 0.5405546900939016},
    "i1": {"s1": -0.2101113393351635, "s2": 0.7526867644750319, "s3": 0.9931588755640579, "s4": 2.1331163414389076,
           "AF": 3.4896675530623207, "corticosteroids": 1.1708133653489108, "impotence2": -1.5064009857454310,
           "migraine": 2.3491159871402441, "renal": -0.5065671632722369, "treatedhyp": 6.5114581098532671,
           "type1": 5.3379864878006531, "type2": 3.6461817406221311, "bmi1": 31.0049529560338860,
           "bmi2": -111.2915718439164300, "fh_cvd": 2.7808628508531887, "sbp": 0.0188585244698659, "town": -0.1007554870063731},
    "i2": {"s1": -0.0004985487027533, "s2": -0.0007987563331739, "s3": -0.0083706184266251, "s4": -0.0007840031915564,
           "AF": -0.0003499560834064, "corticosteroids": -0.0002496045095297, "impotence2": -0.0011058218441227,
           "migraine": 0.0001989644604148, "renal": -0.0018325930166499, "treatedhyp": 0.0006383805310417,
           "type1": 0.0006409780808753, "type2": -0.0024695695588868, "bmi1": 0.0050380102356322,
           "bmi2": -0.0130744830025243, "fh_cvd": -0.0002479180990740, "sbp": -0.0000127187419159, "town": -0.0000932996423233},
    "center": {"rati": 4.300998687744141, "sbp": 128.571578979492190, "sbps5": 8.756621360778809, "town": 0.526304900646210},
}

# Binary risk factors (name -> patient attribute). type1/type2 handled via `diabetes`.
_BINARY = ("AF", "atypicalantipsy", "corticosteroids", "migraine", "ra", "renal",
           "semi", "sle", "treatedhyp", "fh_cvd", "impotence2")
# Continuous inputs that fall back to a population default when absent.
_IMPUTABLE = ("cholesterol_ratio", "systolic_bp", "sbp_sd", "townsend")


def _linear_predictor(p: dict, M: dict, is_female: bool) -> float:
    age = p["age"]
    bmi = min(max(p["bmi"], 20.0), 40.0)  # QRISK3 clamps BMI to [20, 40]
    dage, dbmi = age / 10.0, bmi / 10.0

    if is_female:
        age1 = dage ** -2 - 0.053274843841791
        age2 = dage - 4.332503318786621
        bmi1 = dbmi ** -2 - 0.154946178197861
        bmi2 = dbmi ** -2 * math.log(dbmi) - 0.144462317228317
    else:
        age1 = dage ** -1 - 0.234766781330109
        age2 = dage ** 3 - 77.284080505371094
        bmi1 = dbmi ** -2 - 0.149176135659218
        bmi2 = dbmi ** -2 * math.log(dbmi) - 0.141913309693336

    ctr = M["center"]
    rati = (p["cholesterol_ratio"] if p.get("cholesterol_ratio") is not None else ctr["rati"]) - ctr["rati"]
    sbp = (p["systolic_bp"] if p.get("systolic_bp") is not None else ctr["sbp"]) - ctr["sbp"]
    sbps5 = (p["sbp_sd"] if p.get("sbp_sd") is not None else 0.0) - ctr["sbps5"]
    town = (p["townsend"] if p.get("townsend") is not None else 0.0) - ctr["town"]

    c, i1, i2 = M["c"], M["i1"], M["i2"]
    a = 0.0
    a += M["Iethrisk"][p.get("ethnicity", 1)] if 0 <= p.get("ethnicity", 1) < len(M["Iethrisk"]) else 0.0
    smoke = p.get("smoke", 0)
    a += M["Ismoke"][smoke] if 0 <= smoke < len(M["Ismoke"]) else 0.0
    a += age1 * c["age1"] + age2 * c["age2"] + bmi1 * c["bmi1"] + bmi2 * c["bmi2"]
    a += rati * c["rati"] + sbp * c["sbp"] + sbps5 * c["sbps5"] + town * c["town"]

    diabetes = p.get("diabetes", 0)
    flags = {name: bool(p.get(name)) for name in _BINARY}
    flags["type1"] = diabetes == 1
    flags["type2"] = diabetes == 2
    if is_female:
        flags["impotence2"] = False
    for name, on in flags.items():
        if on and isinstance(c.get(name), (int, float)):
            a += c[name]

    skey = ("", "s1", "s2", "s3", "s4")[smoke] if 0 <= smoke <= 4 else ""
    if skey:
        a += age1 * i1.get(skey, 0.0) + age2 * i2.get(skey, 0.0)
    a += age1 * (bmi1 * i1["bmi1"] + bmi2 * i1["bmi2"]) + age2 * (bmi1 * i2["bmi1"] + bmi2 * i2["bmi2"])
    a += age1 * (sbp * i1["sbp"]) + age2 * (sbp * i2["sbp"])
    a += age1 * (town * i1["town"]) + age2 * (town * i2["town"])
    for name, on in flags.items():
        if not on:
            continue
        if isinstance(i1.get(name), (int, float)):
            a += age1 * i1[name]
        if isinstance(i2.get(name), (int, float)):
            a += age2 * i2[name]
    return a


def qrisk3(patient: dict) -> dict:
    """Compute the QRISK3-2017 ten-year CVD risk with eligibility + imputation
    reporting. ``patient`` keys: sex ('boys'/'girls'/'male'/'female'), age (yr),
    bmi (or height_cm+weight_kg), ethnicity (1-9), smoke (0-4), diabetes (0/1/2),
    cholesterol_ratio, systolic_bp, sbp_sd, townsend, and boolean risk factors."""
    p = dict(patient)
    sex = p.get("sex")
    is_female = sex in ("girls", "female", "f")
    is_male = sex in ("boys", "male", "m")
    if not (is_female or is_male):
        return {"available": False, "reason": f"unknown sex {sex!r}"}

    if p.get("bmi") is None and p.get("height_cm") and p.get("weight_kg"):
        p["bmi"] = p["weight_kg"] / (p["height_cm"] / 100.0) ** 2
    age, bmi = p.get("age"), p.get("bmi")
    lo, hi = QRISK3_ELIGIBLE_AGE
    if not isinstance(age, (int, float)) or not (lo <= age <= hi):
        return {"available": False, "eligible": False,
                "reason": f"QRISK3 is validated only for ages {lo}-{hi} (adult); not applicable here."}
    if not isinstance(bmi, (int, float)) or bmi <= 0:
        return {"available": False, "reason": "height and weight (BMI) are required."}

    imputed = [f for f in _IMPUTABLE if p.get(f) is None]
    M = FEMALE if is_female else MALE
    a = _linear_predictor(p, M, is_female)
    risk = 100.0 * (1.0 - M["survivor"] ** math.exp(a))
    risk = max(0.0, min(100.0, risk))

    band = "high" if risk >= 20 else "moderate" if risk >= 10 else "low"
    return {
        "available": True,
        "eligible": True,
        "risk_percent": round(risk, 1),
        "band": band,
        "imputed_fields": imputed,
        "model": "QRISK3-2017 (ClinRisk, UK adult cohort)",
        "note": ("UK-derived adult model; not India-specific. Interpret alongside "
                 "Lipid Association of India / ICMR guidance."),
    }

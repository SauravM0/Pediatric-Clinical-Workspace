"""FIB-4 liver-fibrosis index (step 2: moved out of the browser).

    FIB-4 = age(y) * AST(U/L) / (platelets(10^9/L) * sqrt(ALT(U/L)))

Sterling RK et al. Hepatology 2006;43:1317-25 (derived in HIV/HCV co-infection).
The cut-offs used here are the MASLD/NAFLD ones in current guidance -- low risk
< 1.30, high risk >= 2.67 (Shah AG et al. Clin Gastroenterol Hepatol
2009;7:1104-12; AASLD 2023) -- with the lower cut-off raised to 2.0 from age 65
(McPherson S et al. Am J Gastroenterol 2017;112:740-51), because age is in the
numerator and the specificity of 1.30 collapses in older adults.

Age limits are enforced, not just footnoted:

* **Under 18 no risk category is given.** FIB-4 is not validated in children;
  age in the numerator makes a child's score small by construction, so "low
  risk" would be false reassurance. The number is still returned so a
  clinician can see it, clearly labelled.
* **18-34** a category is given with a warning: the low cut-off performs poorly
  under 35 (McPherson 2017).
"""
from __future__ import annotations

import math
from typing import Optional

LOW_CUTOFF = 1.30
LOW_CUTOFF_AGE_65 = 2.0
HIGH_CUTOFF = 2.67
MIN_VALIDATED_AGE = 18.0
RELIABLE_FROM_AGE = 35.0
OLDER_ADULT_AGE = 65.0


def fib4(age: float, ast: float, alt: float, platelets_1e9_l: float) -> float:
    return age * ast / (platelets_1e9_l * math.sqrt(alt))


def assess(*, age: Optional[float], ast: Optional[float], alt: Optional[float],
           platelets: Optional[float]) -> dict:
    """``platelets`` in 10^9/L (identical to 10^3/µL)."""
    if None in (age, ast, alt, platelets) or min(age, ast, alt, platelets) <= 0:
        return {"available": False,
                "reason": "Age, AST, ALT and platelet count are all required."}

    # Categorise on the value the clinician SEES (2 dp). On the raw float, a
    # score displayed as "2.67" can be 2.66999... and be labelled indeterminate
    # while showing the high-risk cut-off.
    score = round(fib4(age, ast, alt, platelets), 2)
    low =LOW_CUTOFF_AGE_65 if age >= OLDER_ADULT_AGE else LOW_CUTOFF
    caveats = [
        "Not a diagnosis of fibrosis. An indeterminate or high score calls for "
        "elastography (e.g. FibroScan) or specialist assessment.",
        "Unreliable in acute hepatitis and with very high transaminases; interpret "
        "only when liver enzymes are at a stable baseline.",
    ]
    base = {"available": True, "fib4": round(score, 2),
            "cutoffs": {"low_below": low, "high_at_or_above": HIGH_CUTOFF},
            "citation": "Sterling RK et al. Hepatology 2006;43:1317-25"}

    if age < MIN_VALIDATED_AGE:
        return {**base, "category": None, "category_label": "Not validated under 18",
                "caveats": ["FIB-4 is not validated in children. Age is in the numerator, "
                            "so a child's score is low by construction — do not read it as "
                            "low fibrosis risk."] + caveats}

    if score >= HIGH_CUTOFF:
        category, label = "high", "High risk of advanced fibrosis"
    elif score < low:
        category, label = "low", "Low risk of advanced fibrosis"
    else:
        category, label = "indeterminate", "Indeterminate"
    if age < RELIABLE_FROM_AGE:
        caveats.insert(0, "Under 35 the low cut-off performs poorly (McPherson 2017); "
                          "a low score is less reassuring at this age.")
    if age >= OLDER_ADULT_AGE:
        caveats.insert(0, "Age >= 65: low-risk cut-off raised from 1.30 to 2.0 (McPherson 2017).")
    return {**base, "category": category, "category_label": label, "caveats": caveats}

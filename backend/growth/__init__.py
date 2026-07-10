"""Pediatric growth calculation engine.

Combines two reference populations into one clinically-usable chart per the
"Pediatrician-friendly IAP Growth Charts for 0-18 years" approach
(Dr Bakul Parekh & Dr Vaman Khadilkar):

- WHO Child Growth Standards / Growth Reference, for age < 5 years.
- IAP 2015 (Khadilkar et al.) Indian reference, for age 5-18 years.

All LMS (Cole's Lambda-Mu-Sigma) math is delegated to ``rcpchgrowth``
(``rcpchgrowth.global_functions.z_score`` / ``measurement_for_z``), which is a
peer-reviewed, tested implementation used in a real clinical product (RCPCH,
UK). WHO's own reference values also come directly from rcpchgrowth's bundled
official WHO dataset rather than a re-derived copy. IAP has no rcpchgrowth
support (India isn't one of its bundled references), so IAP's L,M,S values are
fit locally from the paper's own published percentile tables and then run
through the same rcpchgrowth math functions -- the calculation logic is
rcpchgrowth's in both cases, only the source data differs.

Sub-modules:
    who_reference   -- WHO values/z-scores via rcpchgrowth's bundled WHO data.
    iap_reference   -- IAP 2015 LMS fit from the official published tables.
    blend           -- WHO/IAP quintic Hermite blend over a 4.0-5.0y transition.
    curve_builder   -- dense PCHIP-interpolated percentile series for charts.
    validation      -- QA: slope continuity, monotonic age, centile ordering.
"""

"""Pediatric growth calculation engine.

Combines two reference populations into one clinically-usable chart per the
"Pediatrician-friendly IAP Growth Charts for 0-18 years" approach
(Dr Bakul Parekh & Dr Vaman Khadilkar):

- WHO Child Growth Standards / Growth Reference, for age < 5 years.
- IAP 2015 (Khadilkar et al.) Indian reference, for age 5-18 years.

Cole's LMS transform lives in ``lms_core`` (bit-identical to rcpchgrowth's,
proven by tests/growth/test_lms_core_parity.py). WHO's L,M,S come from WHO's own
published tables in ``data/who_lms/`` (installed 19 Sep 2026, proven equivalent
to rcpchgrowth's bundled copy and sealed by checksum). rcpchgrowth is no longer a
runtime dependency -- only the dev-time oracle and an optional fallback. IAP's
L,M,S are fit locally from the paper's published percentile tables until the
authors' own values are installed (data/IAP-LMS-REQUEST.md).

Sub-modules:
    who_reference   -- WHO values/z-scores from data/who_lms (seam-smoothed).
    iap_reference   -- IAP 2015 LMS fit from the official published tables.
    blend           -- WHO/IAP quintic Hermite blend over a 4.0-5.0y transition.
    curve_builder   -- dense PCHIP-interpolated percentile series for charts.
    validation      -- QA: slope continuity, monotonic age, centile ordering.
"""

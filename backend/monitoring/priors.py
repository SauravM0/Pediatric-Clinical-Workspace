"""External plausibility priors from the CPP skeletal-maturation study (Plan 2 WI-6).

A SOFT sanity check: does our accumulated, clinician-confirmed TW3 bone-age
distribution look plausible against a published cohort? This is NEVER a release
gate and NEVER a patient-facing conclusion -- the study population is external
(likely not Indian) and to be confirmed. The study: a cross-sectional comparison
of central precocious puberty (n = 70) vs controls (n = 48), all about 8 years
old, on TW3 hand-wrist, SMI and CVMI. Its exact citation is still unconfirmed
(tables supplied without a reference; the design suggests a Korean orthodontic
or paediatric journal), so treat these priors as provisional.

Encodes the study's TW3 bone-age band distributions (its Table A) and its
qualitative maturity findings (SMI discriminates CPP; CVMI does not at ~8y).
Pure: feed it a band distribution, it returns a divergence + a flag, always with
the external caveat attached.
"""
from __future__ import annotations

from typing import Mapping

SOURCE = ("CPP vs control skeletal-maturation study (external cohort, population to "
          "confirm). Soft prior only — not a gate, not Indian-validated.")
EXTERNAL_CAVEAT = ("EXTERNAL prior — population unconfirmed and probably not Indian. "
                   "Use as context, never as an acceptance criterion.")

# Ordered TW3 bone-age bands (years) and each group's fraction of subjects (Table A).
TW3_BANDS = ("<6", "6-7", "7-8", "8-9", "9-10", "10-11", "11-12", "12-13", "13+")

_CPP_TW3 = {"<6": 0.043, "6-7": 0.029, "7-8": 0.057, "8-9": 0.171, "9-10": 0.371,
            "10-11": 0.157, "11-12": 0.086, "12-13": 0.057, "13+": 0.029}
_CONTROL_TW3 = {"<6": 0.062, "6-7": 0.104, "7-8": 0.229, "8-9": 0.271, "9-10": 0.229,
                "10-11": 0.062, "11-12": 0.042, "12-13": 0.0, "13+": 0.0}
_PRIORS = {"cpp": _CPP_TW3, "control": _CONTROL_TW3}

# Qualitative findings (SMI ≫ CVMI as hand-wrist maturity signals).
MATURITY_NOTES = {
    "advancement": "In CPP, hand-wrist skeletal age runs advanced (modal TW3 ~9-10y at "
                   "chronological ~8y; bone age roughly 1-2y ahead of chronological).",
    "smi": "SMI (hand-wrist) discriminates CPP and correlates moderately (r≈0.49).",
    "cvmi": "CVMI (cervical) is weak at these ages (r≈0.15, ns) — de-prioritise as a signal.",
}

DEFAULT_TV_THRESHOLD = 0.25


def expected_bands(group: str = "cpp") -> dict:
    """The published band-fraction prior for a group ('cpp' | 'control')."""
    if group not in _PRIORS:
        raise ValueError(f"unknown group {group!r}; expected one of {sorted(_PRIORS)}")
    return dict(_PRIORS[group])


def _normalise(dist: Mapping[str, float]) -> dict:
    total = sum(float(v) for v in (dist or {}).values() if v is not None)
    if total <= 0:
        return {}
    return {k: float(v) / total for k, v in dist.items() if v is not None}


def plausibility_check(observed: Mapping[str, float], group: str = "cpp",
                       *, tv_threshold: float = DEFAULT_TV_THRESHOLD) -> dict:
    """Compare an observed TW3-band distribution to the study prior (SOFT signal).

    ``observed``: ``{band: count_or_fraction}`` over ``TW3_BANDS`` (counts are
    normalised; missing bands count as 0). Returns a total-variation distance and
    a non-gating ``within_expected`` flag, always with the external caveat.
    """
    prior = expected_bands(group)
    obs = _normalise(observed)
    if not obs:
        return {"group": group, "tv_distance": None, "within_expected": None,
                "note": "no observed data to compare", "gating": False,
                "caveat": EXTERNAL_CAVEAT, "source": SOURCE}
    keys = set(prior) | set(obs)
    tv = 0.5 * sum(abs(obs.get(k, 0.0) - prior.get(k, 0.0)) for k in keys)
    within = tv <= tv_threshold
    return {
        "group": group,
        "tv_distance": round(tv, 4),
        "tv_threshold": tv_threshold,
        "within_expected": bool(within),
        "gating": False,                 # ALWAYS non-gating
        "note": (MATURITY_NOTES["advancement"] if group == "cpp" else
                 "Control cohort: skeletal age tracks chronological age more closely."),
        "caveat": EXTERNAL_CAVEAT,
        "source": SOURCE,
    }

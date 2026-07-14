"""Structured 20-bone bone-age report (directive S-BA-4).

Aligns to bone_age_product_starter_pack/report_output_schema.json. Composes the
deterministic letter engine (letters_scoring.compute_letters) into ONE
clinician-reviewed report that shows EVERY expected structure -- 13 RUS + 7
carpal -- each with its maturity stage, visibility, and (once the clinic's
licensed tables are entered) its points and share of that bone's maturity range.

Design rules honoured:
* per-bone STAGES/scores, never an invented per-bone "age": TW3 defines group
  scores/ages, not 20 independent ages (audit S1.3);
* RUS and carpal ages are reported SEPARATELY and never averaged (directive
  §15/§18);
* nothing is guessed -- scores/ages stay null until licensed tables exist;
  a bone flagged NOT_VISIBLE / NOT_SCORABLE is recorded, never graded;
* pure function: no I/O, no patient identifiers.
"""
from __future__ import annotations

from typing import Mapping, Optional

from .constants import (
    BONE_LABELS, CARPAL_BONES, CARPAL_BONE_COUNT, CARPAL_LABELS,
    LETTER_STAGES, RUS_BONES, RUS_BONE_COUNT, SEXES,
)
from .letters_scoring import LetterTables, compute_letters, load_letter_tables

REPORT_VERSION = "bone-age-report-1.0"

# Non-grading per-bone states (bone_age_product_starter_pack/bone_inventory.csv).
VISIBILITY_CODES = ("NOT_VISIBLE", "NOT_SCORABLE")

MANDATORY_DISCLAIMER = (
    "This result is decision support and is not valid as a final clinical report "
    "until reviewed and signed by a qualified clinician."
)

# 1..20 in canonical order (13 RUS then 7 carpal) -- matches bone_inventory.csv.
_DISPLAY_ORDER = {code: i + 1 for i, code in enumerate(RUS_BONES + CARPAL_BONES)}


def _visibility(stage: Optional[str]) -> str:
    if stage in (None, ""):
        return "NOT_STAGED"
    if stage in VISIBILITY_CODES:
        return stage
    return "STAGED"


def _valid_letters(stages: Mapping[str, str]) -> dict[str, str]:
    """Only real A-I letters are scored; visibility codes / blanks are dropped so
    the engine never sees an invalid stage and a NOT_VISIBLE bone simply leaves
    the group incomplete (an honest 'no age' rather than a guessed one)."""
    return {b: s for b, s in (stages or {}).items() if s in LETTER_STAGES}


def _bone_row(code: str, system: str, stage: Optional[str], pts_for_sex: dict,
              accepted: bool = False) -> dict:
    vis = _visibility(stage)
    clean_stage = stage if stage not in (None, "") else None
    row = {
        "bone_id": code.upper(),
        "bone_code": code,
        "system": system,
        "anatomical_name": BONE_LABELS.get(code) or CARPAL_LABELS.get(code) or code,
        "display_order": _DISPLAY_ORDER[code],
        "stage": clean_stage,           # kept for the existing UI
        # report_output_schema.json alignment (Plan 1 WI-5): the doctor-confirmed
        # stage, a slot for the future AI suggestion (Plan 4, null until then),
        # its confidence, and per-bone clinician acceptance.
        "manual_stage": clean_stage,
        "predicted_stage": None,
        "confidence_0_to_1": None,
        "accepted_by_clinician": bool(accepted),
        "visibility": vis,
        "scored": False,
        "points": None,
        "bone_max_points": None,
        "pct_of_bone_max": None,
    }
    if vis == "STAGED":
        by_bone = (pts_for_sex or {}).get(code) or {}
        pts = by_bone.get(stage)
        if isinstance(pts, (int, float)) and not isinstance(pts, bool):
            maxp = max(by_bone.values()) if by_bone else None
            row["scored"] = True
            row["points"] = float(pts)
            if maxp:
                row["bone_max_points"] = float(maxp)
                row["pct_of_bone_max"] = round(100.0 * pts / maxp, 1)
    return row


def _group_summary(g, system: str) -> dict:
    return {
        "system": system,
        "staged_count": g.staged_count,
        "total_bones": g.total_bones,
        "complete": g.complete,
        "points_calibrated": g.points_calibrated,
        "total_score": g.total_score if g.points_calibrated else None,
        "twii_age_years": g.twii_age_years,
        "twiii_age_years": g.twiii_age_years,
        "missing_stage": list(g.missing_stage),
    }


def _counts(codes, stages: Mapping[str, str]) -> tuple[int, int]:
    staged = sum(1 for c in codes if _visibility(stages.get(c)) == "STAGED")
    flagged = sum(1 for c in codes if stages.get(c) in VISIBILITY_CODES)
    return staged, flagged


def _age_for_curve(group, preferred_curve: str) -> Optional[float]:
    """Definitive age from the PREFERRED licensed curve edition, falling back to
    the other only if the preferred one is not calibrated (Plan 1 WI-6). TWIII is
    the default for a licensed TW3 book; TWII for a TW2 licence."""
    primary = group.twiii_age_years if preferred_curve == "twiii" else group.twii_age_years
    fallback = group.twii_age_years if preferred_curve == "twiii" else group.twiii_age_years
    return primary if primary is not None else fallback


def build_report(
    sex: str,
    rus_stages: Mapping[str, str],
    carpal_stages: Mapping[str, str],
    chronological_age_years: Optional[float] = None,
    ai_estimate_years: Optional[float] = None,
    tables: Optional[LetterTables] = None,
    preferred_curve: str = "twiii",
    accepted: Optional[Mapping[str, bool]] = None,
) -> dict:
    """Compose the structured 20-bone report. Scores/ages are present only where
    the licensed tables make them legitimate; otherwise the report is the
    doctor-confirmed staging (annotation) plus honest 'requires licensed tables'."""
    if sex not in SEXES:
        raise ValueError(f"unsupported sex {sex!r}")
    tables = tables or load_letter_tables()
    rus_stages = dict(rus_stages or {})
    carpal_stages = dict(carpal_stages or {})
    accepted = dict(accepted or {})
    preferred_curve = preferred_curve if preferred_curve in ("twiii", "twii") else "twiii"

    r = compute_letters(_valid_letters(rus_stages), _valid_letters(carpal_stages), sex, tables)

    rus_pts = tables.rus_pts.get(sex, {})
    carpal_pts = tables.carpal_pts.get(sex, {})
    per_bone = [_bone_row(c, "RUS", rus_stages.get(c), rus_pts, accepted.get(c, False))
                for c in RUS_BONES]
    per_bone += [_bone_row(c, "CARPAL", carpal_stages.get(c), carpal_pts, accepted.get(c, False))
                 for c in CARPAL_BONES]

    # A definitive RUS bone age exists only from a licensed curve, from the
    # preferred edition (TWIII by default; Plan 1 WI-6).
    rus_age = _age_for_curve(r.rus, preferred_curve)
    diff = maturation = None
    if rus_age is not None and chronological_age_years is not None:
        diff = round(rus_age - float(chronological_age_years), 2)
        maturation = "ADVANCED" if diff > 1 else "DELAYED" if diff < -1 else "WITHIN_EXPECTED_RANGE"

    rus_staged, rus_flagged = _counts(RUS_BONES, rus_stages)
    carpal_staged, carpal_flagged = _counts(CARPAL_BONES, carpal_stages)

    return {
        "report_version": REPORT_VERSION,
        "method": {
            "scoring_stream": "TW3-letters (RUS + carpal)",
            "table_version": r.table_version,
            "calculation_version": r.calculation_version,
            "scoring_enabled": tables.any_calibrated(),
            "definitive_curve": preferred_curve,   # TWIII default (Plan 1 WI-6)
            "checksum_verified": tables.checksum_verified,
        },
        "sex": sex,
        "chronological_age_years": chronological_age_years,
        "per_bone_results": per_bone,
        "completeness": {
            "rus_staged": rus_staged, "rus_total": RUS_BONE_COUNT,
            "rus_not_visible_or_scorable": rus_flagged,
            "carpal_staged": carpal_staged, "carpal_total": CARPAL_BONE_COUNT,
            "carpal_not_visible_or_scorable": carpal_flagged,
            "all_20_staged": (rus_staged + carpal_staged) == (RUS_BONE_COUNT + CARPAL_BONE_COUNT),
        },
        # RUS and carpal are ALWAYS separate -- never averaged into one number.
        "rus": _group_summary(r.rus, "RUS"),
        "carpal": _group_summary(r.carpal, "CARPAL"),
        "tw20": {
            "staged_count": r.tw20.staged_count, "total_bones": r.tw20.total_bones,
            "complete": r.tw20.complete, "points_calibrated": r.tw20.points_calibrated,
            "total_score": r.tw20.total_score if r.tw20.points_calibrated else None,
            "age_years": r.tw20.age_years,
        },
        "definitive_bone_age_years": rus_age,
        # Carpal age is reported SEPARATELY and is never averaged with RUS.
        "carpal_definitive_age_years": _age_for_curve(r.carpal, preferred_curve),
        "difference_from_chronological_years": diff,
        "maturation": maturation or "NOT_ASSIGNED",
        # The whole-image AI number is a SEPARATE screening cross-check, not TW3.
        "ai_screening_estimate_years": ai_estimate_years,
        "scoring_note": (
            None if tables.any_calibrated() else
            "RUS and carpal scores/ages require the clinic's licensed TW3 tables. "
            "Until they are entered, this report shows the doctor-confirmed 20-bone "
            "staging only (annotation). Any AI figure is a separate whole-image "
            "screening cross-check and is NOT a TW3 bone age."
        ),
        "clinician_review": {
            "required": True, "reviewer_name": "", "reviewer_role": "",
            "final_bone_age_years": None, "signed_at": "",
        },
        "mandatory_disclaimer": MANDATORY_DISCLAIMER,
    }

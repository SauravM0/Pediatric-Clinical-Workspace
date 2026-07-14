"""Label-quality activation gate for AI stage suggestions (Plan 2 WI-8).

An AI stage suggestion may be SHOWN for a bone only where the data behind it is
trustworthy -- otherwise the bone is "manual" (no suggestion). This is the
interlock between the self-learning flywheel (Plan 2) and the auto-stager
(Plan 4): a bone qualifies only when

  * every stage seen for it has >= ``min_support`` examples across DISTINCT
    patients (STAGE.md rule of thumb ~50/stage),
  * multi-rater consensus agreement for it is >= ``min_agreement`` (single-rater
    labels are 25-40% noisy -- see consensus.py), and
  * the stager's confidence calibration has been validated (softmax != calibrated).

Carpals are gated with the SAME function, independently -- they are simply harder,
so they cross the thresholds later. Pure: no DB, no model; feed it the coverage +
consensus numbers and it decides.
"""
from __future__ import annotations

from typing import Mapping, Optional

DEFAULT_MIN_SUPPORT = 50       # distinct patients per stage (STAGE.md)
DEFAULT_MIN_AGREEMENT = 0.70   # consensus agreement (weighted-kappa-adjacent)


def suggestions_allowed(
    bone: str,
    sex: str,
    *,
    support_per_stage: Mapping[str, int],
    consensus_agreement: Optional[float],
    calibration_ok: bool,
    min_support: int = DEFAULT_MIN_SUPPORT,
    min_agreement: float = DEFAULT_MIN_AGREEMENT,
) -> dict:
    """Decide whether to surface an AI stage suggestion for one bone (one sex).

    ``support_per_stage``: ``{stage: distinct_patient_count}`` for this bone.
    ``consensus_agreement``: mean multi-rater agreement (0..1) or None.
    ``calibration_ok``: whether the stager's probability calibration is validated.
    Returns ``{allowed, reasons, ...}``; ``allowed`` is True only if ALL gates pass.
    """
    counts = {s: int(n) for s, n in (support_per_stage or {}).items()}
    min_count = min(counts.values()) if counts else 0
    support_ok = bool(counts) and min_count >= min_support
    agreement_ok = isinstance(consensus_agreement, (int, float)) and consensus_agreement >= min_agreement
    calib_ok = bool(calibration_ok)

    reasons = []
    reasons.append(
        f"{'PASS' if support_ok else 'FAIL'} support: min stage has {min_count} "
        f"distinct patients (need {min_support})")
    reasons.append(
        f"{'PASS' if agreement_ok else 'FAIL'} consensus: agreement "
        f"{consensus_agreement} (need >= {min_agreement})")
    reasons.append(f"{'PASS' if calib_ok else 'FAIL'} calibration validated")

    return {
        "bone": bone,
        "sex": sex,
        "allowed": bool(support_ok and agreement_ok and calib_ok),
        "min_stage_support": min_count,
        "consensus_agreement": consensus_agreement,
        "calibration_ok": calib_ok,
        "reasons": reasons,
    }


def activation_map(
    coverage_report: Mapping,
    *,
    agreements: Optional[Mapping[str, float]] = None,
    calibrated_bones: Optional[Mapping[str, bool]] = None,
    sex: str = "all",
    min_support: int = DEFAULT_MIN_SUPPORT,
    min_agreement: float = DEFAULT_MIN_AGREEMENT,
) -> dict:
    """Per-bone activation decisions from a coverage report (export_dataset.coverage_report).

    ``coverage_report``: the dict with a ``cells`` list of
    ``{bone_code, stage, unique_total, ...}``. ``agreements`` / ``calibrated_bones``
    map bone_code -> value (defaults: no agreement, not calibrated -> not allowed).
    Returns ``{bone_code: suggestions_allowed(...)}`` plus a summary count.
    """
    per_bone_stage: dict[str, dict[str, int]] = {}
    for cell in (coverage_report or {}).get("cells", []):
        b = str(cell.get("bone_code"))
        per_bone_stage.setdefault(b, {})[str(cell.get("stage"))] = int(cell.get("unique_total", 0))

    agreements = agreements or {}
    calibrated_bones = calibrated_bones or {}
    decisions: dict[str, dict] = {}
    for bone, support in sorted(per_bone_stage.items()):
        decisions[bone] = suggestions_allowed(
            bone, sex,
            support_per_stage=support,
            consensus_agreement=agreements.get(bone),
            calibration_ok=calibrated_bones.get(bone, False),
            min_support=min_support, min_agreement=min_agreement,
        )
    n_allowed = sum(1 for d in decisions.values() if d["allowed"])
    return {"decisions": decisions, "n_bones": len(decisions), "n_allowed": n_allowed}

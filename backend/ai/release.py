"""Offline retrain -> gated release harness (Plan 2 WI-7).

The safety core of the self-learning flywheel: a "learned" model is a RELEASE
CANDIDATE, never a live weight update. This harness runs the Plan 5 release-gate
engine (leak guard -> evaluator -> beat-incumbent + no subgroup regression +
calibration + engineering gates), builds a model card, and decides the status:

  * gate FAILED                      -> rejected  (never deploys)
  * gate PASSED, no human sign-off   -> candidate (awaiting sign-off)
  * gate PASSED and signed off       -> deployed

Nothing here auto-promotes: deployment requires both a passing verdict AND a named
human signer. ``record_release`` persists the decision to the ``ModelRelease``
audit table. Pure decision logic + one DB write.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence

from backend.ai.validation.release_gate import Verdict, evaluate_candidate
from backend.config import APP_VERSION

_KINDS = {"screening", "localizer", "stager"}
CANDIDATE, DEPLOYED, REJECTED = "candidate", "deployed", "rejected"


@dataclass(frozen=True)
class ReleaseDecision:
    verdict: Verdict
    status: str
    model_card: dict


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_model_card(*, model_kind: str, version: str, incumbent_version: Optional[str],
                     dataset: str, verdict: Verdict, external: bool = False,
                     caveats: Optional[list[str]] = None) -> dict:
    """A self-describing card for a candidate: what it is, how it did, its limits."""
    return {
        "model_kind": model_kind,
        "version": version,
        "incumbent_version": incumbent_version,
        "dataset": dataset,
        "generated_at": _utcnow_iso(),
        "intended_use": ("clinician-assist screening/triage cross-check; a suggestion the "
                         "doctor verifies — NOT an autonomous diagnosis"),
        "external_validation": bool(external),
        "gate_passed": verdict.passed,
        "gate_reasons": list(verdict.reasons),
        "metrics": verdict.report,
        "caveats": caveats or [
            "An internal gate pass is NOT a clinical accuracy claim (see PLAN-5 WI-8).",
            "The screening model is Greulich-Pyle whole-image, not TW3.",
            "Deployment still requires a named human sign-off.",
        ],
    }


def decide_release(
    *,
    model_kind: str,
    version: str,
    dataset: str,
    targets: Sequence[float],
    candidate_preds: Sequence[float],
    incumbent_preds: Optional[Sequence[float]] = None,
    incumbent_version: Optional[str] = None,
    groups: Optional[Sequence[Any]] = None,
    intervals: Optional[Sequence[Sequence[float]]] = None,
    target_coverage: Optional[float] = None,
    test_registry: Optional[Any] = None,
    other_sets: Optional[Mapping[str, Mapping[str, Iterable[Any]]]] = None,
    gates: Optional[dict] = None,
    min_improvement_months: float = 0.0,
    subgroup_regression_tol_months: float = 0.0,
    signed_off_by: Optional[str] = None,
    external: bool = False,
) -> ReleaseDecision:
    """Run the gate and decide the release status (does not persist)."""
    if model_kind not in _KINDS:
        raise ValueError(f"unknown model_kind {model_kind!r}; expected one of {sorted(_KINDS)}")

    verdict = evaluate_candidate(
        targets, candidate_preds, incumbent_preds,
        groups=groups, intervals=intervals, target_coverage=target_coverage,
        test_registry=test_registry, other_sets=other_sets, gates=gates,
        min_improvement_months=min_improvement_months,
        subgroup_regression_tol_months=subgroup_regression_tol_months,
    )
    if not verdict.passed:
        status = REJECTED
    elif not signed_off_by:
        status = CANDIDATE       # passed the gate but a human has not signed off
    else:
        status = DEPLOYED
    card = build_model_card(model_kind=model_kind, version=version,
                            incumbent_version=incumbent_version, dataset=dataset,
                            verdict=verdict, external=external)
    return ReleaseDecision(verdict=verdict, status=status, model_card=card)


def record_release(db, decision: ReleaseDecision, *, model_kind: str, version: str,
                   incumbent_version: Optional[str] = None,
                   dataset_manifest_checksum: Optional[str] = None,
                   signed_off_by: Optional[str] = None,
                   model_card_path: Optional[str] = None):
    """Persist the decision to the ModelRelease audit table. Returns the row.

    ``signed_off_at`` is stamped only for a DEPLOYED release. A rejected or
    candidate release is recorded too -- every decision is auditable.
    """
    from backend.models import ModelRelease

    v = decision.verdict
    gates = (v.report or {}).get("gates") or {}
    row = ModelRelease(
        model_kind=model_kind,
        version=version,
        incumbent_version=incumbent_version,
        dataset_manifest_checksum=dataset_manifest_checksum,
        beat_incumbent=any("PASS beat-incumbent" in r for r in v.reasons),
        gates_passed=bool(gates.get("passed")),
        verdict_passed=bool(v.passed),
        status=decision.status,
        signed_off_by=(signed_off_by if decision.status == DEPLOYED else None),
        signed_off_at=(datetime.now(timezone.utc) if decision.status == DEPLOYED else None),
        metrics_json=json.dumps(v.report),
        reasons="\n".join(v.reasons),
        model_card_path=model_card_path,
        application_version=APP_VERSION,
    )
    db.add(row)
    db.flush()
    return row

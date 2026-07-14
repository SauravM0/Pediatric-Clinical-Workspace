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
from pathlib import Path
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


# ─────────────────────────────────────────────────────────────────────────────
# Offline CLI entrypoint (PLAN-0 A1).
#
# The harness never invents predictions. It consumes an EVALUATION ARTIFACT — the
# candidate's (and incumbent's) predictions on the LOCKED test set, produced by an
# offline evaluation run (Phase C/D/E) — decides the release via the Plan 5 gate,
# writes a model card, and records the decision to the ModelRelease audit table.
#
#   python -m backend.ai.release preds.json --sign-off "Dr Rao" --card-out card.json
#
# preds.json (the artifact):
#   { "model_kind": "screening", "version": "v2", "dataset": "rsna-locked-test",
#     "incumbent_version": "v1", "dataset_manifest_checksum": "sha256…",
#     "targets": [...], "candidate_preds": [...], "incumbent_preds": [...],
#     "groups": [...]?, "intervals": [[lo,hi],...]?, "target_coverage": 0.9?,
#     "min_improvement_months": 0.3?, "subgroup_regression_tol_months": 0.0?,
#     "external": false? }
# ─────────────────────────────────────────────────────────────────────────────

# Keys of the artifact forwarded verbatim to decide_release (besides sign-off,
# which comes from the CLI so a human — not a file — authorises deployment).
_SPEC_KEYS = (
    "model_kind", "version", "dataset", "incumbent_version",
    "targets", "candidate_preds", "incumbent_preds",
    "groups", "intervals", "target_coverage",
    "min_improvement_months", "subgroup_regression_tol_months", "external",
)


def decide_from_spec(spec: Mapping[str, Any], *, signed_off_by: Optional[str] = None) -> ReleaseDecision:
    """Run the gate for an evaluation artifact dict (does not persist)."""
    kwargs = {k: spec[k] for k in _SPEC_KEYS if k in spec}
    for required in ("model_kind", "version", "dataset", "targets", "candidate_preds"):
        if required not in kwargs:
            raise ValueError(f"evaluation artifact is missing required field {required!r}")
    return decide_release(signed_off_by=signed_off_by, **kwargs)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Gate + record a candidate from an evaluation artifact. Exit 1 if rejected."""
    import argparse

    ap = argparse.ArgumentParser(
        prog="python -m backend.ai.release",
        description="Offline gated-release harness: gate a candidate model against the "
                    "incumbent on the locked test set and record the decision.")
    ap.add_argument("predictions", help="path to the evaluation-artifact JSON (see module docstring)")
    ap.add_argument("--sign-off", dest="signed_off_by", default=None,
                    help="named human signer; deployment requires BOTH a passing gate and this")
    ap.add_argument("--card-out", dest="card_out", default=None,
                    help="where to write the model card JSON (default: alongside the artifact)")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the gate and write the card but do NOT record to the DB")
    args = ap.parse_args(argv)

    spec = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    decision = decide_from_spec(spec, signed_off_by=args.signed_off_by)

    card_path = Path(args.card_out) if args.card_out else Path(args.predictions).with_suffix(".card.json")
    card_path.write_text(json.dumps(decision.model_card, indent=2), encoding="utf-8")

    print(f"model_kind={spec.get('model_kind')} version={spec.get('version')}")
    print(f"verdict: {'PASS' if decision.verdict.passed else 'FAIL'}  ->  status={decision.status}")
    for reason in decision.verdict.reasons:
        print(f"  - {reason}")
    print(f"model card: {card_path}")

    if not args.dry_run:
        from backend.db import session_scope
        with session_scope() as db:
            row = record_release(
                db, decision, model_kind=spec["model_kind"], version=spec["version"],
                incumbent_version=spec.get("incumbent_version"),
                dataset_manifest_checksum=spec.get("dataset_manifest_checksum"),
                signed_off_by=args.signed_off_by, model_card_path=str(card_path))
            print(f"recorded ModelRelease id={row.id} status={row.status}")

    return 1 if decision.status == REJECTED else 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(main())

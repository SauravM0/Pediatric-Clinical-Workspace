"""Release-gate engine (Plan 5 WI-6) — the callable Plan 2 (WI-7) and Plan 3
(WI-8) invoke to decide whether a candidate model may ship.

Given candidate + incumbent predictions on the SAME locked test set, it:
  1. refuses if the test set leaked into any training/tuning/feedback set (WI-1);
  2. computes whole-hand metrics for both (evaluate.py);
  3. checks BEAT-INCUMBENT (lower MAE by a pre-registered margin);
  4. checks NO SUBGROUP REGRESSION (no subgroup worse than incumbent by > tol);
  5. checks CALIBRATION (conformal coverage meets target, when intervals given);
  6. checks the ENGINEERING GATES (gates.py).

Returns a :class:`Verdict` (passed + reasons + full report). It does NOT persist
anything or capture sign-off -- that is Plan 2's ``ModelRelease``/release.py. Pure
and deterministic so a release decision is reproducible and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

from backend.ai.evaluate import evaluate_age
from backend.ai.validation import gates as _gates
from backend.ai.validation import leak_guard as _leak


# How a candidate may be compared with the incumbent (M4.4).
#
# The existing gate assumes like-for-like: same method, same dataset, so "beat
# the incumbent's MAE" is meaningful. Adopting digiBONE breaks that assumption --
# it is a different METHOD (segmental Greulich-Pyle) whose value proposition is
# accuracy on INDIAN children, evaluated against an incumbent measured on RSNA.
# Requiring it to beat the incumbent on RSNA would either block a better model or
# force someone to weaken the gate, and a loosened gate is a permanent loss of a
# safety property.
#
# So cross-method adoption gets its own basis: it is held to ABSOLUTE thresholds
# plus a written rationale and human sign-off, instead of a delta.
SAME_METHOD_SAME_DATASET = "same-method-same-dataset"
CROSS_METHOD_ADOPTION = "cross-method-adoption"
COMPARISON_BASES = (SAME_METHOD_SAME_DATASET, CROSS_METHOD_ADOPTION)


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reasons: tuple[str, ...]
    report: dict = field(repr=False, default_factory=dict)


def _mae(preds: Sequence[float], targets: Sequence[float]) -> float:
    return evaluate_age(preds, targets, bootstrap=0)["mae_months"]


def _subgroup_regressions(targets, cand, inc, groups, tol: float) -> list[dict]:
    """Per-subgroup candidate-vs-incumbent MAE; flag any subgroup the candidate
    makes worse by more than ``tol`` months."""
    buckets: dict[str, list[int]] = {}
    for i, gkey in enumerate(groups):
        buckets.setdefault(str(gkey), []).append(i)
    out: list[dict] = []
    for key, idx in sorted(buckets.items()):
        c = _mae([cand[i] for i in idx], [targets[i] for i in idx])
        p = _mae([inc[i] for i in idx], [targets[i] for i in idx])
        if c > p + tol:
            out.append({"group": key, "n": len(idx), "candidate_mae": c,
                        "incumbent_mae": p, "delta": round(c - p, 3)})
    return out


def evaluate_candidate(
    targets: Sequence[float],
    candidate_preds: Sequence[float],
    incumbent_preds: Optional[Sequence[float]] = None,
    *,
    groups: Optional[Sequence[Any]] = None,
    intervals: Optional[Sequence[Sequence[float]]] = None,
    target_coverage: Optional[float] = None,
    test_registry: Optional["_leak.TestRegistry"] = None,
    other_sets: Optional[Mapping[str, Mapping[str, Iterable[Any]]]] = None,
    gates: Optional[dict] = None,
    min_improvement_months: float = 0.0,
    subgroup_regression_tol_months: float = 0.0,
    comparison_basis: str = SAME_METHOD_SAME_DATASET,
    adoption_rationale: Optional[str] = None,
) -> Verdict:
    """Decide whether ``candidate_preds`` may replace ``incumbent_preds``.

    All prediction arrays are aligned by case to ``targets`` (months). ``groups``
    (one subgroup key per case) enables the no-regression check. Provide
    ``test_registry`` + ``other_sets`` to enforce the leak guard first.
    """
    reasons: list[str] = []

    if comparison_basis not in COMPARISON_BASES:
        return Verdict(False, (f"unknown comparison_basis {comparison_basis!r}; "
                               f"expected one of {COMPARISON_BASES}",), {})
    cross_method = comparison_basis == CROSS_METHOD_ADOPTION
    if cross_method and not (adoption_rationale or "").strip():
        return Verdict(False, ("cross-method adoption requires a written "
                               "adoption_rationale: the beat-incumbent check does "
                               "not apply, so the reason for adopting must be "
                               "recorded for sign-off",), {})

    # 1. Leak guard — refuse before computing anything if the test set leaked.
    if test_registry is not None and other_sets is not None:
        _leak.assert_disjoint(test_registry, other_sets)  # raises LeakError

    n = len(targets)
    if n == 0 or len(candidate_preds) != n:
        return Verdict(False, ("no aligned test predictions to evaluate",), {})

    cand = evaluate_age(candidate_preds, targets, intervals=intervals,
                        target_coverage=target_coverage)
    report: dict = {"candidate": cand}

    # 3. Beat incumbent -- only meaningful for a like-for-like comparison.
    beat = True
    if cross_method:
        if incumbent_preds is not None:
            inc = evaluate_age(incumbent_preds, targets)
            report["incumbent"] = inc
            report["incumbent_comparison_is_informational"] = True
            reasons.append(
                f"INFO cross-method: candidate MAE {cand['mae_months']} vs incumbent "
                f"{inc['mae_months']} on this dataset -- reported, NOT gated. The "
                "candidate uses a different method and its claim rests on a "
                "different population."
            )
        reasons.append("SKIP beat-incumbent: cross-method adoption is gated on "
                       "absolute thresholds plus written rationale and sign-off")
        report["adoption_rationale"] = adoption_rationale
    elif incumbent_preds is not None:
        inc = evaluate_age(incumbent_preds, targets)
        report["incumbent"] = inc
        beat = cand["mae_months"] <= inc["mae_months"] - min_improvement_months
        reasons.append(
            f"{'PASS' if beat else 'FAIL'} beat-incumbent: candidate MAE "
            f"{cand['mae_months']} vs incumbent {inc['mae_months']} "
            f"(margin {min_improvement_months} mo)"
        )
    else:
        reasons.append("SKIP beat-incumbent: no incumbent supplied")

    # 4. No subgroup regression. Also delta-based, so it is informational under
    # cross-method adoption -- the absolute per-subgroup gate still applies below.
    no_regression = True
    worst_subgroup_mae = None
    if groups is not None:
        regressions = (
            _subgroup_regressions(list(targets), list(candidate_preds),
                                  list(incumbent_preds), list(groups),
                                  subgroup_regression_tol_months)
            if incumbent_preds is not None and not cross_method else []
        )
        report["subgroup_regressions"] = regressions
        no_regression = not regressions
        # worst candidate subgroup MAE (for the subgroup gate)
        buckets: dict[str, list[int]] = {}
        for i, g in enumerate(groups):
            buckets.setdefault(str(g), []).append(i)
        maes = [_mae([candidate_preds[i] for i in idx], [targets[i] for i in idx])
                for idx in buckets.values()]
        worst_subgroup_mae = max(maes) if maes else None
        report["worst_subgroup_mae_months"] = worst_subgroup_mae
        reasons.append(
            f"{'PASS' if no_regression else 'FAIL'} no-subgroup-regression: "
            f"{len(regressions)} regressed subgroup(s)"
        )

    # 5. Calibration (coverage meets target), when intervals were provided.
    calibration_ok = True
    if intervals is not None and target_coverage is not None:
        calibration_ok = bool(cand.get("coverage", {}).get("meets_target"))
        reasons.append(
            f"{'PASS' if calibration_ok else 'FAIL'} calibration: empirical coverage "
            f"{cand.get('coverage', {}).get('empirical')} vs target {target_coverage}"
        )

    # 6. Engineering gates.
    gate_report = _gates.evaluate_gates(cand, worst_subgroup_mae_months=worst_subgroup_mae,
                                        gates=gates)
    report["gates"] = gate_report
    reasons.append(
        f"{'PASS' if gate_report['passed'] else 'FAIL'} engineering-gates: "
        f"{gate_report['n_fail']} failed, {gate_report['n_not_measured']} not measured"
    )

    passed = beat and no_regression and calibration_ok and gate_report["passed"]
    report["comparison_basis"] = comparison_basis
    if cross_method:
        reasons.append("REQUIRES human sign-off: cross-method adoption is never "
                       "auto-deployed (see release.py)")
        report["requires_human_signoff"] = True
    report["passed"] = passed
    return Verdict(passed=passed, reasons=tuple(reasons), report=report)

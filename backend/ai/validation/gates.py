"""Encoded engineering gates (Plan 5 WI-5).

Turns validation_protocol.md §6 from prose into machine-checkable pass/fail, with
the measured value beside every threshold. Thresholds live in the versioned
``gates.json`` so a change is a reviewed, logged event -- never an inline tweak.

Pure: takes already-computed metrics (from evaluate.py) and returns a gate report.
A gate whose input was not provided is ``not_measured`` (surfaced, never silently
passed); the release engine decides which gates are mandatory for a given model.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

_GATES_PATH = Path(__file__).with_name("gates.json")

PASS, FAIL, NOT_MEASURED = "pass", "fail", "not_measured"


def load_gates(path: Path = _GATES_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _gate(name: str, measured, threshold, comparator: str) -> dict:
    """comparator '<=' means measured must be <= threshold; '>=' the reverse."""
    if not _num(measured):
        status = NOT_MEASURED
    elif comparator == "<=":
        status = PASS if measured <= threshold else FAIL
    else:  # ">="
        status = PASS if measured >= threshold else FAIL
    return {"gate": name, "measured": measured, "threshold": threshold,
            "comparator": comparator, "status": status}


def evaluate_gates(
    age_metrics: Optional[dict] = None,
    *,
    worst_subgroup_mae_months: Optional[float] = None,
    staging: Optional[dict] = None,
    gates: Optional[dict] = None,
) -> dict:
    """Evaluate every gate the provided inputs allow.

    ``age_metrics``: an :func:`backend.ai.evaluate.evaluate_age` result.
    ``worst_subgroup_mae_months``: worst sufficient subgroup MAE (from
    ``evaluate_by_subgroup``). ``staging``: optional dict with
    ``overall_weighted_kappa`` and ``min_bone_weighted_kappa`` (Plan 4/WI-4).

    Returns ``{protocol_version, gates:[...], passed, n_fail, n_not_measured}``;
    ``passed`` is True iff no gate FAILED (unmeasured gates do not fail here).
    """
    g = gates or load_gates()
    wh = g.get("whole_hand", {})
    st = g.get("staging", {})
    am = age_metrics or {}
    pct12 = (am.get("pct_within_months") or {}).get("12")

    results = [
        _gate("whole_hand.mae", am.get("mae_months"), wh.get("max_mae_months"), "<="),
        _gate("whole_hand.subgroup_mae", worst_subgroup_mae_months,
              wh.get("max_subgroup_mae_months"), "<="),
        _gate("whole_hand.pct_within_12mo", pct12, wh.get("min_pct_within_12mo"), ">="),
    ]
    if staging is not None:
        results.append(_gate("staging.overall_weighted_kappa",
                             staging.get("overall_weighted_kappa"),
                             st.get("min_overall_weighted_kappa"), ">="))
        results.append(_gate("staging.min_bone_weighted_kappa",
                             staging.get("min_bone_weighted_kappa"),
                             st.get("min_bone_weighted_kappa"), ">="))
    else:
        for name, thr in (("staging.overall_weighted_kappa", st.get("min_overall_weighted_kappa")),
                          ("staging.min_bone_weighted_kappa", st.get("min_bone_weighted_kappa"))):
            results.append({"gate": name, "measured": None, "threshold": thr,
                            "comparator": ">=", "status": NOT_MEASURED})

    n_fail = sum(1 for r in results if r["status"] == FAIL)
    n_nm = sum(1 for r in results if r["status"] == NOT_MEASURED)
    return {
        "protocol_version": g.get("protocol_version", "unknown"),
        "gates": results,
        "passed": n_fail == 0,
        "n_fail": n_fail,
        "n_not_measured": n_nm,
    }

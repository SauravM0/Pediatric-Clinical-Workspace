"""First baseline ValidationReport for the shipped screening model (PLAN-0 C2).

Runs the shipped ONNX over the LOCKED internal test (the RSNA validation set, never
seen in training/tuning/calibration — leak-guarded before any prediction), computes
whole-hand + subgroup metrics and conformal coverage on truly held-out data,
evaluates the engineering gates, and writes a ValidationReport (JSON + human HTML).

This is the honest held-out baseline every future candidate must beat through the
release gate. It evaluates the REAL inference path (boneage.predict_months), not a
reimplementation.

    python -m backend.ai.validation.baseline_report
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend.ai import boneage
from backend.ai.evaluate import age_band_years, evaluate_age, evaluate_by_subgroup
from backend.ai.validation import gates as _gates
from backend.ai.validation import rsna_data
from backend.ai.validation.leak_guard import assert_disjoint, load_registry
from backend.ai.validation.report import build_validation_report, write_report

REPORTS_DIR = Path(__file__).with_name("reports")


def run() -> dict:
    reg = load_registry()                       # verifies the frozen checksum
    if reg.is_empty:
        raise SystemExit("locked_test.json is empty — run carve_locked_test first.")

    # Leak guard BEFORE any prediction: refuse if the test set overlaps training.
    assert_disjoint(reg, {"train": {"patient_ids": rsna_data.read_training_ids()}})

    labels = [r for r in rsna_data.read_validation_labels() if r["id"] in reg.patient_ids]
    if not labels:
        raise SystemExit("no locked-test images resolved on disk.")

    records: list[dict] = []
    intervals: list[list[float]] = []
    for r in labels:
        pred = boneage.predict_months(r["path"].read_bytes(), r["is_male"])
        m = float(pred["bone_age_months"])
        half = pred.get("uncertainty_months")
        records.append({"pred": m, "target": r["age_months"],
                        "sex": "boys" if r["is_male"] else "girls",
                        "age_band": age_band_years(r["age_months"] / 12.0)})
        intervals.append([m - half, m + half] if half is not None else [m, m])

    preds = [r["pred"] for r in records]
    targets = [r["target"] for r in records]
    meta = boneage.model_metadata() or {}
    cov = (meta.get("conformal") or {}).get("default_coverage")
    target_cov = float(cov) if cov else None

    age = evaluate_age(preds, targets, intervals=intervals, target_coverage=target_cov)
    subs = evaluate_by_subgroup(records, by=["sex", "age_band"])
    worst = (subs.get("worst_subgroup") or {}).get("mae_months")
    gate_report = _gates.evaluate_gates(age, worst_subgroup_mae_months=worst)

    provenance = {
        "model_version": meta.get("model_version"),
        "model_file": boneage.MODEL_PATH.name,
        "trained_on": meta.get("trained_on"),
        "locked_test_dataset": reg.dataset,
        "locked_test_source": reg.source,
        "locked_test_checksum": reg.raw.get("checksum"),
        "locked_test_frozen_at": reg.frozen_at,
        "n_test": len(records),
        "leak_guard": "passed — locked test disjoint from training",
    }
    report = build_validation_report(
        model_version=meta.get("model_version", "boneage-gp-unknown"),
        dataset=reg.dataset, age_metrics=age, subgroups=subs,
        gate_report=gate_report, provenance=provenance)

    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    base = REPORTS_DIR / f"baseline_screening_{stamp}"
    write_report(report, base.with_suffix(".json"), base.with_suffix(".html"))
    return {"report": report, "path_stem": str(base)}


def main() -> int:
    if not boneage.model_available():
        print("No shipped ONNX model at backend/ai/models/boneage_gp.onnx.")
        return 1
    if not rsna_data.data_available():
        print("RSNA validation data not present — cannot run the baseline report.")
        return 1
    r = run()
    h = r["report"]["headline"]
    print(f"Baseline on locked test: MAE {h['mae_months']} mo · "
          f"%within12mo {h['pct_within_12mo']} · gates_passed={h['gates_passed']}")
    print(f"Wrote {r['path_stem']}.json / .html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

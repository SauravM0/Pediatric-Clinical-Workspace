"""Evaluate the screening model on the LOCAL dual-read Indian cohort (M2C 2.13).

    python -m backend.ai.validation.local_cohort_report

Counterpart to ``baseline_report``, which evaluates on the frozen RSNA split.
That number says the model works on the population it was trained on; it says
nothing about the children walking into this clinic. This one produces the
number that does -- and it is the asset that turns "we think it works here" into
a measurement.

Why a separate module rather than a flag on baseline_report
------------------------------------------------------------
The two draw from different worlds. The RSNA report reads label CSVs and image
files from a dataset directory. This cohort lives in the database: films are
``Radiograph`` rows, and the reference standard is the CONSENSUS of at least two
independent ``TW3Assessment`` reads. Sharing one function would have meant a
parameter switching almost every line.

Without this module the carve was inert. ``carve_local_cohort`` could survey and
freeze, and nothing could then evaluate against what it froze -- the fifth time
in this project that a prepared asset had no consumer, so there is a test for it.

The inter-reader floor, which is the point most easily missed
--------------------------------------------------------------
Bone age has no ground truth. The reference standard here is an expert reading,
and two radiologists routinely differ by 0.5-1.0 year on the same film. So a
model MAE quoted on its own overstates what "good" means: if the readers
disagree by 0.6y, a model at 0.5y is already at the noise floor of the
measurement, and chasing 0.3y is chasing the readers' own variance.

:func:`reader_disagreement` therefore reports the inter-reader spread beside the
model's error, and the report refuses to call a result "better than the readers"
-- it can only say the model is within the band where the reference itself is
uncertain.

Greulich-Pyle vs TW3
--------------------
The screening model is Greulich-Pyle; the stored consensus is whatever method
the readers used, recorded on the assessment. Comparing across methods is a
category error, so films whose consensus method does not match the model's scale
are EXCLUDED and counted, never silently compared.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai import active_model, boneage
from backend.ai.evaluate import age_band_years, evaluate_age, evaluate_by_subgroup
from backend.ai.validation import carve_local_cohort as carve
from backend.ai.validation.leak_guard import (
    LeakError, RegistryError, assert_disjoint, load_registry, registry_path,
)
from backend.ai.validation.report import build_validation_report, write_report
from backend.models import Patient, Radiograph, TW3Assessment

REPORTS_DIR = Path(__file__).with_name("reports")

# Published Indian comparison: TW3 was best overall but WORST of three methods in
# pubertal boys. That is the subgroup a headline MAE hides, so it is reported
# separately and the carve refuses to freeze without it.
CRITICAL_STRATUM = "boys:pubertal"


class CohortReportError(RuntimeError):
    """The local cohort cannot be evaluated as requested."""


def _image_bytes(rg: Radiograph) -> Optional[bytes]:
    if not rg.internal_file_path:
        return None
    path = Path(rg.internal_file_path)
    try:
        return path.read_bytes()
    except OSError:
        return None


def reader_disagreement(db: Session, radiograph_ids: list[int]) -> dict[str, Any]:
    """Spread between independent readers on the same films.

    This is the floor on any achievable model error, and reporting a model MAE
    without it invites the reader to treat the consensus as truth. Computed only
    over films that actually carry two or more scored reads.
    """
    spreads: list[float] = []
    per_film: list[dict[str, Any]] = []
    for rid in radiograph_ids:
        ages = [
            a.bone_age_months for a in db.execute(
                select(TW3Assessment).where(TW3Assessment.radiograph_id == rid)
            ).scalars().all()
            if a.bone_age_months is not None and a.reader_id
        ]
        if len(ages) < 2:
            continue
        spread = float(max(ages) - min(ages))
        spreads.append(spread)
        per_film.append({"radiograph_id": rid, "n_reads": len(ages),
                         "spread_months": round(spread, 1)})

    if not spreads:
        return {"available": False, "n_films": 0,
                "note": ("no film carries two scored reads, so the reference "
                         "standard's own uncertainty is unknown — a model error "
                         "cannot be interpreted without it")}
    return {
        "available": True,
        "n_films": len(spreads),
        "mean_spread_months": round(statistics.fmean(spreads), 2),
        "median_spread_months": round(statistics.median(spreads), 2),
        "max_spread_months": round(max(spreads), 1),
        "worst_films": sorted(per_film, key=lambda f: -f["spread_months"])[:5],
        "note": ("Mean absolute difference between independent readers on the same "
                 "film. A model error at or below this is at the noise floor of the "
                 "reference standard, not evidence of superiority."),
    }


def collect(db: Session) -> dict[str, Any]:
    """Run the real inference path over every frozen film. Read-only."""
    path = registry_path(carve.DATASET)
    try:
        reg = load_registry(path)
    except RegistryError as exc:
        raise CohortReportError(
            f"{exc}\nFreeze the cohort first: "
            "python -m backend.ai.validation.carve_local_cohort --freeze"
        ) from exc
    if reg.is_empty:
        raise CohortReportError(f"{path.name} is frozen but empty.")
    if reg.dataset != carve.DATASET:
        raise CohortReportError(
            f"{path.name} holds {reg.dataset!r}, not {carve.DATASET!r}")

    spec = active_model.active_spec()
    if spec is None or not spec.available:
        raise CohortReportError(
            "no screening model is installed, so there is nothing to evaluate")

    records: list[dict[str, Any]] = []
    intervals: list[list[float]] = []
    excluded = {"no_image": [], "no_consensus": [], "method_mismatch": [],
                "unknown_stratum": []}
    used_ids: list[int] = []

    for film_key in sorted(reg.patient_ids, key=lambda v: (len(v), v)):
        try:
            rid = int(film_key)
        except ValueError:
            continue
        rg = db.get(Radiograph, rid)
        if rg is None:
            excluded["no_image"].append(film_key)
            continue

        reads = db.execute(
            select(TW3Assessment).where(TW3Assessment.radiograph_id == rid)
        ).scalars().all()
        scored = [a for a in reads if a.bone_age_months is not None and a.reader_id]
        if len(scored) < carve.MIN_READERS:
            excluded["no_consensus"].append(film_key)
            continue

        blob = _image_bytes(rg)
        if blob is None:
            excluded["no_image"].append(film_key)
            continue

        patient = db.get(Patient, rg.patient_id)
        if patient is None:
            excluded["no_image"].append(film_key)
            continue
        pubertal = carve._is_pubertal(db, patient.id)
        stratum = carve._stratum(patient.sex_at_birth, pubertal)
        if stratum is None:
            excluded["unknown_stratum"].append(film_key)
            continue

        pred = boneage.predict_months(blob, is_male=(patient.sex_at_birth == "boys"))
        if pred is None:
            excluded["no_image"].append(film_key)
            continue
        # A Greulich-Pyle estimate must never be scored against a TW3 consensus
        # as though they were the same quantity.
        if pred.get("is_tw3_scale"):
            excluded["method_mismatch"].append(film_key)
            continue

        # True median, matching carve.survey -- see the note there. The upper-of-two
        # rule biased every dual-read label toward the higher reader.
        target = float(statistics.median(a.bone_age_months for a in scored))
        months = float(pred["bone_age_months"])
        half = pred.get("uncertainty_months")
        records.append({
            "pred": months, "target": target,
            "sex": patient.sex_at_birth,
            "stratum": stratum,
            "age_band": age_band_years(target / 12.0),
        })
        intervals.append([months - half, months + half] if half is not None else
                         [months, months])
        used_ids.append(rid)

    return {"registry": reg, "records": records, "intervals": intervals,
            "excluded": excluded, "used_ids": used_ids, "spec": spec}


def run(db: Session, *, training_sets: Optional[dict] = None) -> dict[str, Any]:
    collected = collect(db)
    reg = collected["registry"]

    # Leak guard BEFORE any conclusion is drawn. A cohort that fed training,
    # tuning, feedback or calibration cannot measure anything.
    assert_disjoint(reg, training_sets or {})

    records = collected["records"]
    if not records:
        raise CohortReportError(
            "no frozen film could be evaluated: "
            + ", ".join(f"{k}={len(v)}" for k, v in collected["excluded"].items())
        )

    preds = [r["pred"] for r in records]
    targets = [r["target"] for r in records]
    age = evaluate_age(preds, targets, intervals=collected["intervals"])
    # Two separate breakdowns, not one cross-product. `stratum` already encodes
    # sex, so passing both to a single call multiplies the cells and leaves each
    # one too small to read -- with a 200-film target that is the difference
    # between a usable subgroup MAE and noise.
    by_stratum = evaluate_by_subgroup(records, by=["stratum"])
    by_age = evaluate_by_subgroup(records, by=["sex", "age_band"])
    subs = {"by_stratum": by_stratum, "by_sex_and_age_band": by_age,
            "overall": by_stratum.get("overall"),
            "worst_subgroup": by_stratum.get("worst_subgroup")}
    readers = reader_disagreement(db, collected["used_ids"])

    mae = age.get("mae_months")
    floor = readers.get("mean_spread_months") if readers.get("available") else None
    spec = collected["spec"]

    interpretation = []
    if floor is not None and mae is not None:
        if mae <= floor:
            interpretation.append(
                f"Model MAE ({mae} mo) is at or below the inter-reader spread "
                f"({floor} mo). The model is within the band where the reference "
                "standard is itself uncertain; this is NOT evidence that it beats "
                "the readers, because there is no ground truth to beat them against."
            )
        else:
            interpretation.append(
                f"Model MAE ({mae} mo) exceeds the inter-reader spread ({floor} mo), "
                "so the error is larger than the reference standard's own noise and "
                "is attributable to the model."
            )
    critical = next(
        (cell for cell in (by_stratum.get("subgroups") or [])
         if (cell.get("group") or {}).get("stratum") == CRITICAL_STRATUM),
        None,
    )
    if critical:
        interpretation.append(
            f"{CRITICAL_STRATUM}: MAE {critical.get('mae_months')} mo over "
            f"{critical.get('n')} films. Published Indian data show TW3 is worst of "
            "three methods in this subgroup, so it is reported separately rather "
            "than left inside a headline average."
        )
    else:
        interpretation.append(
            f"{CRITICAL_STRATUM} is absent from the evaluated films, so the "
            "subgroup published as the weakest for TW3 in Indian children is "
            "unmeasured here. The headline figure does not cover it."
        )

    provenance = {
        "model_id": spec.model_id,
        "model_method": spec.method,
        "model_population": spec.population,
        "cohort_dataset": reg.dataset,
        "cohort_source": reg.source,
        "cohort_checksum": reg.raw.get("checksum"),
        "cohort_frozen_at": reg.frozen_at,
        "n_frozen": len(reg.patient_ids),
        "n_evaluated": len(records),
        "excluded": {k: len(v) for k, v in collected["excluded"].items()},
        "min_readers": carve.MIN_READERS,
        "leak_guard": "passed — cohort disjoint from the supplied training sets",
        "reference_standard": (
            "Consensus of >= 2 independent expert reads, NOT ground truth. "
            "Interpret every figure against the inter-reader spread below."
        ),
    }
    report = build_validation_report(
        model_version=spec.model_id, dataset=reg.dataset,
        age_metrics=age, subgroups=subs, gate_report={}, provenance=provenance,
        # This IS the external validation: a different population, a different
        # institution, and labels this project's model never saw.
        external=True)
    report["reader_disagreement"] = readers
    report["interpretation"] = interpretation
    return report


def main(argv=None) -> int:  # pragma: no cover - thin CLI
    import json

    from backend.db import init_db, session_scope

    init_db()
    try:
        with session_scope() as db:
            report = run(db)
    except (CohortReportError, LeakError) as exc:
        print(str(exc))
        return 1

    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    base = REPORTS_DIR / f"local_cohort_{stamp}"
    write_report(report, base.with_suffix(".json"), base.with_suffix(".html"))

    head = report["headline"]
    print(f"Local Indian cohort: MAE {head.get('mae_months')} mo over "
          f"{report['provenance']['n_evaluated']} films")
    readers = report["reader_disagreement"]
    if readers.get("available"):
        print(f"Inter-reader spread: {readers['mean_spread_months']} mo "
              f"(the floor this number should be read against)")
    for line in report["interpretation"]:
        print(f"  - {line}")
    print(json.dumps(report["provenance"]["excluded"], indent=2))
    print(f"Wrote {base}.json / .html")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

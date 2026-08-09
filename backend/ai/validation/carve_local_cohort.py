"""Freeze a LOCAL (Indian) dual-read validation cohort (M2C / item 2.13).

Counterpart to ``carve_locked_test``, which freezes the RSNA validation split.
That set proves the model works on the population it was trained on; it says
nothing about Indian children, and published work shows bone-age method bias
varies by sex and pubertal status in exactly this population. **No amount of
model work substitutes for this cohort.** It is the asset that converts
"we think it works here" into a number.

Two readers, not one
--------------------
Bone age has no ground truth -- the reference standard is itself an expert
reading, and two radiologists routinely differ by 0.5-1.0 year on the same film.
A cohort labelled by one reader measures agreement with that reader, not
accuracy. So a film is only admitted once at least ``MIN_READERS`` independent
reads exist, and the label is their consensus (``tw3.consensus``), with
disagreements routed to adjudication rather than averaged.

Stratification is enforced, not hoped for
-----------------------------------------
The published Indian comparison found TW3 best overall but **worst of three
methods in pubertal boys**. A cohort that happens to be mostly prepubertal girls
would hide precisely the subgroup where the method is weakest, so the carve
refuses to freeze until every stratum has a minimum count.

Freezing is one-way. Once registered, these films are off-limits to training,
tuning, feedback and calibration -- ``leak_guard`` enforces that, and a set you
can quietly re-carve after seeing a result is not a test set.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Patient, Radiograph, TW3Assessment
from backend.tw3 import consensus as _consensus

DATASET = "local-indian-bone-age-cohort"
SOURCE = "external-india"

MIN_READERS = 2
# Target from the roadmap. Below this the confidence interval on a subgroup MAE
# is too wide to support any claim, so the carve reports rather than freezes.
TARGET_SIZE = 200
MIN_PER_STRATUM = 15

# Sex x pubertal status -- the two axes the published bias actually varies on.
PUBERTAL_STRATA = ("prepubertal", "pubertal")


class CohortError(ValueError):
    """The cohort cannot be frozen as requested."""


@dataclass
class FilmRecord:
    film_key: str
    patient_id: int
    sex: str
    stratum: str
    n_readers: int
    consensus_bone_age_months: Optional[int]
    disputed_bones: tuple[str, ...] = ()


@dataclass
class CohortReport:
    eligible: list[FilmRecord] = field(default_factory=list)
    rejected: dict[str, list[str]] = field(default_factory=dict)
    strata: dict[str, int] = field(default_factory=dict)
    ready_to_freeze: bool = False
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": DATASET,
            "source": SOURCE,
            "n_eligible": len(self.eligible),
            "target_size": TARGET_SIZE,
            "strata": self.strata,
            "min_per_stratum": MIN_PER_STRATUM,
            "rejected": {k: len(v) for k, v in self.rejected.items()},
            "rejected_examples": {k: v[:5] for k, v in self.rejected.items()},
            "ready_to_freeze": self.ready_to_freeze,
            "reasons": self.reasons,
        }


def _stratum(sex: str, pubertal: Optional[bool]) -> Optional[str]:
    if pubertal is None:
        return None
    return f"{sex}:{'pubertal' if pubertal else 'prepubertal'}"


def _is_pubertal(db: Session, patient_id: int) -> Optional[bool]:
    """Pubertal status from the most recent Tanner assessment (M2).

    None when never staged -- and a film with unknown pubertal status is
    EXCLUDED rather than guessed into a stratum, because the whole reason for
    stratifying is that this variable changes the answer.
    """
    from backend.models import PubertyAssessment

    row = db.execute(
        select(PubertyAssessment).where(PubertyAssessment.patient_id == patient_id)
        .order_by(PubertyAssessment.assessed_at.desc()).limit(1)
    ).scalars().first()
    if row is None:
        return None
    if row.testicular_volume_ml is not None:
        return row.testicular_volume_ml >= 4.0
    for stage in (row.breast_stage, row.genital_stage):
        if stage is not None:
            return stage >= 2
    return None


def survey(db: Session) -> CohortReport:
    """Which stored films qualify, and what is still missing. Read-only."""
    report = CohortReport()
    rejected: dict[str, list[str]] = {
        "too_few_readers": [], "no_consensus_age": [],
        "pubertal_status_unknown": [], "no_approved_assessment": [],
    }

    by_film: dict[int, list[TW3Assessment]] = {}
    for a in db.execute(
        select(TW3Assessment).where(TW3Assessment.radiograph_id.isnot(None))
    ).scalars().all():
        by_film.setdefault(a.radiograph_id, []).append(a)

    for radiograph_id, assessments in sorted(by_film.items()):
        rg = db.get(Radiograph, radiograph_id)
        if rg is None:
            continue
        key = str(radiograph_id)

        # Distinct readers only: one person reading twice is not two reads.
        readers = {a.reader_id for a in assessments if a.reader_id}
        if len(readers) < MIN_READERS:
            rejected["too_few_readers"].append(key)
            continue

        scored = [a for a in assessments if a.bone_age_months is not None]
        if not scored:
            rejected["no_consensus_age"].append(key)
            continue

        patient = db.get(Patient, rg.patient_id)
        if patient is None:
            continue
        pubertal = _is_pubertal(db, patient.id)
        stratum = _stratum(patient.sex_at_birth, pubertal)
        if stratum is None:
            rejected["pubertal_status_unknown"].append(key)
            continue

        # Consensus of the independent reads, not a mean of their ages.
        stagings = [
            {b.bone_code: b.confirmed_stage for b in a.bones if b.confirmed_stage}
            for a in assessments
        ]
        disputed: tuple[str, ...] = ()
        if stagings and all(stagings):
            result = _consensus.consensus(
                stagings, sorted({k for s in stagings for k in s}),
                min_readers=MIN_READERS)
            disputed = tuple(getattr(result, "disputed", ()) or ())

        median_months = sorted(a.bone_age_months for a in scored)[len(scored) // 2]
        report.eligible.append(FilmRecord(
            film_key=key, patient_id=patient.id, sex=patient.sex_at_birth,
            stratum=stratum, n_readers=len(readers),
            consensus_bone_age_months=median_months, disputed_bones=disputed,
        ))
        report.strata[stratum] = report.strata.get(stratum, 0) + 1

    report.rejected = rejected

    reasons: list[str] = []
    if len(report.eligible) < TARGET_SIZE:
        reasons.append(
            f"{len(report.eligible)} eligible films, target {TARGET_SIZE}. Below "
            "this the confidence interval on a subgroup MAE is too wide to support "
            "an accuracy claim."
        )
    for sex in ("boys", "girls"):
        for phase in PUBERTAL_STRATA:
            name = f"{sex}:{phase}"
            have = report.strata.get(name, 0)
            if have < MIN_PER_STRATUM:
                reasons.append(
                    f"stratum {name}: {have}/{MIN_PER_STRATUM}. Published Indian "
                    "data show TW3 is WORST of three methods in pubertal boys, so a "
                    "cohort thin in any stratum hides the subgroup that matters most."
                )
    report.reasons = reasons
    report.ready_to_freeze = not reasons
    return report


def freeze(db: Session, *, content_hashes: Optional[dict[str, str]] = None,
           force: bool = False) -> dict[str, Any]:
    """Register the cohort as a leak-guarded locked test set.

    One-way by design. ``force`` exists for a deliberate re-carve after a
    documented decision, never as a convenience.
    """
    from .leak_guard import save_registry

    report = survey(db)
    if not report.ready_to_freeze and not force:
        raise CohortError(
            "cohort is not ready to freeze:\n  - " + "\n  - ".join(report.reasons)
            + "\nFreezing early produces a test set that cannot support the claim "
              "it exists to support. Pass force=True only with a recorded rationale."
        )

    ids = [f.film_key for f in report.eligible]
    hashes = [
        (content_hashes or {}).get(f.film_key)
        or (db.get(Radiograph, int(f.film_key)).image_hash or "")
        for f in report.eligible
    ]
    if any(not h for h in hashes):
        raise CohortError(
            "every film needs a content hash before freezing — the registry "
            "identifies films by content, so a missing hash means the same image "
            "could later re-enter training undetected"
        )

    save_registry(ids, hashes, dataset=DATASET, source=SOURCE)
    return {
        "frozen": True, "n": len(ids), "dataset": DATASET, "source": SOURCE,
        "strata": report.strata,
        "note": "These films are now off-limits to training, tuning, feedback and "
                "calibration. leak_guard enforces it.",
    }


def main(argv=None) -> int:  # pragma: no cover - thin CLI over survey/freeze
    """Report readiness, or freeze.

    Survey is the default and freezing needs an explicit flag, because freezing
    is one-way: once registered, these films are off-limits to training, tuning,
    feedback and calibration for good. ``--force`` additionally requires a
    written rationale, so an early carve leaves a record of who decided it.
    """
    import argparse
    import json

    from backend.db import init_db, session_scope

    p = argparse.ArgumentParser(description="Survey or freeze the local dual-read cohort.")
    p.add_argument("--freeze", action="store_true", help="register the cohort (one-way)")
    p.add_argument("--force", action="store_true",
                   help="freeze despite an unready cohort; requires --rationale")
    p.add_argument("--rationale", default="", help="recorded reason for a forced carve")
    args = p.parse_args(argv)

    # Idempotent, and required: against a fresh deployment the survey otherwise
    # dies with a raw "no such table: tw3_assessment" traceback, when the honest
    # answer is "no films are stored yet, here is what is still needed".
    init_db()

    with session_scope() as db:
        if not args.freeze:
            print(json.dumps(survey(db).to_dict(), indent=2))
            return 0
        if args.force and not args.rationale.strip():
            print("--force requires --rationale: a deliberate early carve must "
                  "leave a record of why.", file=sys.stderr)
            return 2
        try:
            result = freeze(db, force=args.force)
        except CohortError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if args.rationale.strip():
            result["forced_rationale"] = args.rationale.strip()
        print(json.dumps(result, indent=2))
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

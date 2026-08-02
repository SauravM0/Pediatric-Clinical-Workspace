"""Build a PatientSnapshot from the database and run the engine (M5).

The persistence boundary for ``backend/clinical``, exactly as ``growth_service``
is for ``backend/growth`` and ``assessment_service`` is for ``backend/tw3``. All
the database access lives here; the reasoning package receives one frozen value
object and returns findings.

This is also where SDS actually gets computed — the engine reasons about SDS but
must not know how a z-score is derived, or it would acquire a dependency on the
whole growth reference stack.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import growth_service
from backend.clinical import prediction, referral, rules
from backend.clinical.snapshot import Measurement, PatientSnapshot
from backend.growth import blend
from backend.models import Patient, PubertyAssessment, TW3Assessment


def _sds(measure: str, sex: str, age_years: float, value: float) -> Optional[float]:
    try:
        return blend.unified_z_for_value(measure, sex, age_years, value)
    except Exception:
        return None


def _latest(points: list[tuple[float, float]]) -> Optional[tuple[float, float]]:
    return points[-1] if points else None


def build_snapshot(db: Session, patient_id: int) -> PatientSnapshot:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise growth_service.GrowthRecordError(f"patient {patient_id} not found")

    sex = patient.sex_at_birth
    heights = growth_service.series_for(db, patient_id, "height")
    weights = growth_service.series_for(db, patient_id, "weight")
    bmis = growth_service.series_for(db, patient_id, "bmi")
    spans = growth_service.series_for(db, patient_id, "arm_span")
    sitting = growth_service.series_for(db, patient_id, "sitting_height")

    def measure(measure_key: str, points: list[tuple[float, float]]) -> Optional[Measurement]:
        latest = _latest(points)
        if latest is None:
            return None
        age, value = latest
        return Measurement(age, value, _sds(measure_key, sex, age, value))

    height_history = tuple(
        Measurement(age, value, _sds("height", sex, age, value)) for age, value in heights
    )

    raw_velocities = growth_service.velocities_for(db, patient_id, "height")
    velocities = tuple(
        (v["from_age_years"], v["to_age_years"], v["velocity_per_year"])
        for v in raw_velocities
        if v["available"] and v["velocity_per_year"] is not None
    )
    # SDS for the most recent interval that could actually be scored (M1.3).
    scored = [v for v in raw_velocities if v.get("velocity_sds") is not None]
    latest_velocity_sds = scored[-1]["velocity_sds"] if scored else None

    # Current age: the most recent measurement's age is the honest "as of", since
    # a snapshot describes the last time the child was actually seen.
    latest_height = _latest(heights)
    age_years = latest_height[0] if latest_height else None

    puberty = db.execute(
        select(PubertyAssessment).where(PubertyAssessment.patient_id == patient_id)
        .order_by(PubertyAssessment.assessed_at.desc()).limit(1)
    ).scalars().first()

    assessment = db.execute(
        select(TW3Assessment).where(TW3Assessment.patient_id == patient_id)
        .where(TW3Assessment.bone_age_months.isnot(None))
        .order_by(TW3Assessment.updated_at.desc()).limit(1)
    ).scalars().first()

    # The mid-parental target expressed as an ADULT height SDS, so the rule can
    # compare like with like. Adult reference age 19 is the same point the
    # frontend's adult-height projection already uses.
    target = prediction.mid_parental_target(
        sex, patient.mother_height_cm, patient.father_height_cm,
        source=patient.parental_height_source)
    target_sds = (
        _sds("height", sex, 19.0, target.target_cm) if target is not None else None
    )

    return PatientSnapshot(
        sex=sex,
        age_years=age_years,
        height=measure("height", heights),
        weight=measure("weight", weights),
        bmi=measure("bmi", bmis),
        height_history=height_history,
        height_velocities=velocities,
        latest_velocity_sds=latest_velocity_sds,
        mother_height_cm=patient.mother_height_cm,
        father_height_cm=patient.father_height_cm,
        parental_height_source=patient.parental_height_source,
        target_height_sds=target_sds,
        gestational_age_weeks=patient.gestational_age_weeks,
        birth_weight_g=patient.birth_weight_g,
        breast_stage=puberty.breast_stage if puberty else None,
        genital_stage=puberty.genital_stage if puberty else None,
        pubic_hair_stage=puberty.pubic_hair_stage if puberty else None,
        testicular_volume_ml=puberty.testicular_volume_ml if puberty else None,
        menarche_reached=bool(puberty.menarche_date) if puberty else None,
        bone_age_years=(assessment.bone_age_months / 12.0) if assessment else None,
        bone_age_method=assessment.assessment_method if assessment else None,
        arm_span_cm=_latest(spans)[1] if spans else None,
        sitting_height_cm=_latest(sitting)[1] if sitting else None,
    )


def assess(db: Session, patient_id: int, *, include_parent_summary: bool = False) -> dict[str, Any]:
    """Full clinical assessment for one patient."""
    snapshot = build_snapshot(db, patient_id)
    findings = rules.evaluate(snapshot)
    t = referral.triage(findings)

    body: dict[str, Any] = {
        "patient_id": patient_id,
        "as_of_age_years": round(snapshot.age_years, 2) if snapshot.age_years else None,
        "findings": [f.to_dict() for f in findings],
        "triage": {
            "level": t.level,
            "reason": t.reason,
            "guidance": t.guidance,
            "specialties": list(t.specialties),
            "driving_findings": list(t.driving_findings),
            "not_assessed": list(t.not_assessed),
        },
        "adult_height": prediction.adult_height_summary(
            snapshot.sex, snapshot.age_years,
            snapshot.height.value if snapshot.height else None,
            snapshot.weight.value if snapshot.weight else None,
            snapshot.mother_height_cm, snapshot.father_height_cm,
            snapshot.parental_height_source,
        ),
        "disclaimer": (
            "Decision support for a qualified clinician. Findings are observations "
            "from anthropometry, not diagnoses, and the absence of a finding does "
            "not exclude disease."
        ),
    }
    if include_parent_summary:
        body["parent_summary"] = referral.parent_summary(findings, t)
    return body

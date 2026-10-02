"""Longitudinal record endpoints (M2).

Thin HTTP layer over ``growth_service``. Router-level ``clinical_access``
applies the usual floor: reads need READ_CLINICAL, writes need WRITE_CLINICAL,
so an assistant can record measurements (which is their job) while an admin
cannot.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import growth_service as svc
from backend.db import get_db
from backend.growth import observations
from backend.models import User
from backend.security.deps import clinical_access

router = APIRouter(
    prefix="/api/patients",
    tags=["longitudinal"],
    dependencies=[Depends(clinical_access)],
)


def _fail(exc: Exception) -> HTTPException:
    detail = str(exc)
    return HTTPException(404 if "not found" in detail else 422, detail)


class ObservationBody(BaseModel):
    obs_type: str = Field(..., description=f"one of {observations.OBSERVATION_KEYS}")
    value: float
    observed_at: Optional[datetime] = None
    unit: Optional[str] = None
    method: Optional[str] = None
    encounter_id: Optional[int] = None
    note: Optional[str] = None
    allow_implausible_change: bool = Field(
        False, description="override the implausible-decrease guard (records a warning)")


class CorrectionBody(BaseModel):
    new_value: float
    reason: str = Field(min_length=1)


class DobBody(BaseModel):
    date_of_birth: datetime


class EncounterBody(BaseModel):
    occurred_at: Optional[datetime] = None
    reason: Optional[str] = None
    note: Optional[str] = None


class PubertyBody(BaseModel):
    assessed_at: Optional[datetime] = None
    breast_stage: Optional[int] = None
    genital_stage: Optional[int] = None
    pubic_hair_stage: Optional[int] = None
    testicular_volume_ml: Optional[float] = None
    menarche_date: Optional[datetime] = None
    encounter_id: Optional[int] = None


class PatientCreateBody(BaseModel):
    patient_code: str = Field(..., min_length=1, max_length=64, description="clinic MRN")
    sex: str = Field(..., description="boys | girls")
    date_of_birth: Optional[datetime] = None
    name: Optional[str] = Field(None, max_length=200)
    mother_height_cm: Optional[float] = None
    father_height_cm: Optional[float] = None
    parental_height_source: Optional[str] = None
    gestational_age_weeks: Optional[float] = None
    birth_weight_g: Optional[float] = None


class PatientContextBody(BaseModel):
    mother_height_cm: Optional[float] = None
    father_height_cm: Optional[float] = None
    parental_height_source: Optional[str] = None
    gestational_age_weeks: Optional[float] = None
    birth_weight_g: Optional[float] = None


class VisitBody(BaseModel):
    observed_at: datetime
    height: Optional[float] = None
    weight: Optional[float] = None
    head_circumference: Optional[float] = None
    sitting_height: Optional[float] = None
    arm_span: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    allow_implausible_change: bool = False


# ── patient registry (step 3) ───────────────────────────────────────────────

class LookupBody(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


@router.post("/lookup")
def find_patient(body: LookupBody, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Exact lookup by MRN. A POST so the MRN travels in the body, not in a URL
    that lands in access logs and browser history. There is deliberately no
    name search: names are encrypted at rest."""
    patient = svc.find_patient_by_code(db, body.code)
    if patient is None:
        raise HTTPException(404, "no patient with this code")
    return svc.patient_summary(patient)


@router.post("", status_code=201)
def create_patient(body: PatientCreateBody, db: Session = Depends(get_db),
                   actor: User = Depends(clinical_access)) -> dict[str, Any]:
    fields = body.model_dump()
    try:
        patient = svc.create_patient(
            db, patient_code=fields.pop("patient_code"), sex=fields.pop("sex"),
            date_of_birth=fields.pop("date_of_birth"), name=fields.pop("name"),
            actor=actor.username, **fields)
    except svc.GrowthRecordError as exc:
        raise HTTPException(409 if "already exists" in str(exc) else 422, str(exc)) from exc
    return svc.patient_summary(patient)


@router.patch("/{patient_id}")
def update_patient(patient_id: int, body: PatientContextBody, db: Session = Depends(get_db),
                   actor: User = Depends(clinical_access)) -> dict[str, Any]:
    """Only the fields actually sent are changed (a PATCH), so clearing a value
    is an explicit null rather than an omission."""
    try:
        patient = svc.update_patient_context(db, patient_id, actor=actor.username,
                                             **body.model_dump(exclude_unset=True))
    except svc.GrowthRecordError as exc:
        raise _fail(exc) from exc
    return svc.patient_summary(patient)


@router.post("/{patient_id}/visits", status_code=201)
def record_visit(patient_id: int, body: VisitBody, db: Session = Depends(get_db),
                 actor: User = Depends(clinical_access)) -> dict[str, Any]:
    """One visit's measurements, all-or-nothing; BMI derived server-side."""
    values = body.model_dump(exclude={"observed_at", "allow_implausible_change"})
    try:
        return svc.record_visit_measurements(
            db, patient_id=patient_id, observed_at=body.observed_at, values=values,
            allow_implausible_change=body.allow_implausible_change, actor=actor.username)
    except (svc.GrowthRecordError, observations.ObservationError) as exc:
        raise _fail(exc) from exc


@router.get("/observation-types")
def observation_types() -> dict[str, Any]:
    return {
        "types": [
            {"key": o.key, "label": o.label, "unit": o.unit,
             "plausible_range": [o.min_value, o.max_value],
             "charted": o.charted, "monotonic": o.monotonic}
            for o in observations.OBSERVATION_TYPES.values()
        ],
        "note": "Ranges reject data-entry errors (metres for centimetres, grams "
                "for kilograms). A clinically extreme but real value is inside them.",
    }


@router.post("/{patient_id}/observations", status_code=201)
def record_observation(patient_id: int, body: ObservationBody,
                       db: Session = Depends(get_db),
                       actor: User = Depends(clinical_access)) -> dict[str, Any]:
    try:
        row, warnings = svc.record_observation(
            db, patient_id=patient_id, obs_type=body.obs_type, value=body.value,
            observed_at=body.observed_at, unit=body.unit, method=body.method,
            encounter_id=body.encounter_id, note=body.note,
            allow_implausible_change=body.allow_implausible_change,
            actor=actor.username,
        )
    except (svc.GrowthRecordError, observations.ObservationError) as exc:
        raise _fail(exc) from exc
    return {
        "id": row.id, "obs_type": row.obs_type, "value": row.value, "unit": row.unit,
        "observed_at": row.observed_at.isoformat(),
        "age_years": round(row.age_months / 12, 3) if row.age_months is not None else None,
        "warnings": warnings,
    }


@router.post("/observations/{observation_id}/correct")
def correct_observation(observation_id: int, body: CorrectionBody,
                        db: Session = Depends(get_db),
                        actor: User = Depends(clinical_access)) -> dict[str, Any]:
    try:
        row = svc.correct_observation(db, observation_id, new_value=body.new_value,
                                      reason=body.reason, actor=actor.username)
    except (svc.GrowthRecordError, observations.ObservationError) as exc:
        raise _fail(exc) from exc
    return {"id": row.id, "corrects": observation_id, "value": row.value,
            "note": "the original is retained and marked 'corrected'"}


@router.get("/{patient_id}/timeline")
def timeline(patient_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Everything recorded for one patient — the single-screen view."""
    try:
        return svc.timeline(db, patient_id)
    except svc.GrowthRecordError as exc:
        raise _fail(exc) from exc


@router.get("/{patient_id}/series/{obs_type}")
def series(patient_id: int, obs_type: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        observations.get(obs_type)
        points = svc.series_for(db, patient_id, obs_type)
    except (svc.GrowthRecordError, observations.ObservationError) as exc:
        raise _fail(exc) from exc
    return {"patient_id": patient_id, "obs_type": obs_type,
            "points": [{"age_years": a, "value": v} for a, v in points]}


@router.get("/{patient_id}/velocity/{obs_type}")
def velocity(patient_id: int, obs_type: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        observations.get(obs_type)
        results = svc.velocities_for(db, patient_id, obs_type)
    except (svc.GrowthRecordError, observations.ObservationError) as exc:
        raise _fail(exc) from exc
    return {
        "patient_id": patient_id, "obs_type": obs_type, "intervals": results,
        "sds_note": "Velocity SDS needs a published velocity reference (Khadilkar "
                    "et al., Indian Pediatr 2019). Until it is bundled, the rate is "
                    "reported without a centile rather than against an invented one.",
    }


@router.put("/{patient_id}/date-of-birth")
def set_date_of_birth(patient_id: int, body: DobBody, db: Session = Depends(get_db),
                      actor: User = Depends(clinical_access)) -> dict[str, Any]:
    """Correcting a date of birth recomputes every stored age in the same call —
    otherwise all historical z-scores silently become wrong."""
    try:
        n = svc.set_date_of_birth(db, patient_id, body.date_of_birth, actor=actor.username)
    except svc.GrowthRecordError as exc:
        raise _fail(exc) from exc
    return {"patient_id": patient_id, "observations_recomputed": n}


@router.post("/{patient_id}/encounters", status_code=201)
def create_encounter(patient_id: int, body: EncounterBody, db: Session = Depends(get_db),
                     actor: User = Depends(clinical_access)) -> dict[str, Any]:
    try:
        row = svc.create_encounter(db, patient_id=patient_id, occurred_at=body.occurred_at,
                                   reason=body.reason, note=body.note,
                                   seen_by_user_id=actor.id or None)
    except svc.GrowthRecordError as exc:
        raise _fail(exc) from exc
    return {"id": row.id, "occurred_at": row.occurred_at.isoformat(), "reason": row.reason}


@router.post("/{patient_id}/puberty", status_code=201)
def record_puberty(patient_id: int, body: PubertyBody, db: Session = Depends(get_db),
                   actor: User = Depends(clinical_access)) -> dict[str, Any]:
    try:
        row = svc.record_puberty(
            db, patient_id=patient_id, assessed_at=body.assessed_at,
            breast_stage=body.breast_stage, genital_stage=body.genital_stage,
            pubic_hair_stage=body.pubic_hair_stage,
            testicular_volume_ml=body.testicular_volume_ml,
            menarche_date=body.menarche_date, encounter_id=body.encounter_id,
            actor=actor.username)
    except svc.GrowthRecordError as exc:
        raise _fail(exc) from exc
    return {"id": row.id, "assessed_at": row.assessed_at.isoformat()}

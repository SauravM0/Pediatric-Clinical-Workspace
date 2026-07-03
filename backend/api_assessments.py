"""Assessment lifecycle API (directive §21).

Thin HTTP layer over ``assessment_service``. Scoring/approval logic lives in the
service; this module only validates request bodies and maps errors to status
codes. All routes are local and touch only the local SQLite database.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import assessment_service as svc
from backend import radiograph_service as rgsvc
from backend.db import get_db
from backend.imaging import ImagingError

router = APIRouter(prefix="/api/bone-age", tags=["assessments"])


def _handle(exc: svc.AssessmentError) -> HTTPException:
    msg = str(exc)
    if "not found" in msg:
        return HTTPException(status_code=404, detail=msg)
    if "immutable" in msg or "approved" in msg or "superseded" in msg or "cannot" in msg:
        return HTTPException(status_code=409, detail=msg)
    return HTTPException(status_code=422, detail=msg)


def _years_to_months(years: Optional[float]) -> Optional[int]:
    return None if years is None else round(years * 12)


class CreateAssessmentReq(BaseModel):
    patient_code: str = Field(..., min_length=1, max_length=64)
    sex: str = Field(..., description="'boys' or 'girls'")
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    chronological_age_years: Optional[float] = Field(None, ge=0, le=30)


class SetGradeReq(BaseModel):
    stage: Optional[str] = Field(None, description="grade 1-8, or null to clear")
    reason: Optional[str] = None


class ApproveReq(BaseModel):
    approved_by: str = Field(..., min_length=1, max_length=120)


class ReasonReq(BaseModel):
    actor: str = Field("local-user", max_length=120)
    reason: Optional[str] = None


@router.post("/assessments", status_code=201)
def create_assessment(req: CreateAssessmentReq, db: Session = Depends(get_db)) -> dict:
    dob = datetime(req.date_of_birth.year, req.date_of_birth.month,
                   req.date_of_birth.day, tzinfo=timezone.utc) if req.date_of_birth else None
    try:
        a = svc.create_assessment(
            db, patient_code=req.patient_code, sex=req.sex, name=req.name,
            date_of_birth=dob,
            chronological_age_months=_years_to_months(req.chronological_age_years),
        )
        return svc.assessment_to_dict(db, a)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.get("/assessments")
def list_assessments(patient_code: Optional[str] = Query(None),
                     db: Session = Depends(get_db)) -> list[dict]:
    from sqlalchemy import select
    from backend.models import Patient, TW3Assessment
    stmt = select(TW3Assessment).order_by(TW3Assessment.created_at.desc())
    if patient_code:
        stmt = stmt.join(Patient).where(Patient.patient_code == patient_code)
    rows = db.execute(stmt).scalars().all()
    return [svc.assessment_to_dict(db, a) for a in rows]


@router.get("/assessments/{assessment_id}")
def read_assessment(assessment_id: int, include_audit: bool = Query(False),
                    db: Session = Depends(get_db)) -> dict:
    try:
        a = svc.get_assessment(db, assessment_id)
        return svc.assessment_to_dict(db, a, include_audit=include_audit)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.put("/assessments/{assessment_id}/bones/{bone_code}")
def update_bone(assessment_id: int, bone_code: str, req: SetGradeReq,
                db: Session = Depends(get_db)) -> dict:
    try:
        a = svc.set_bone_stage(db, assessment_id, bone_code, req.stage, reason=req.reason)
        return svc.assessment_to_dict(db, a)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.post("/assessments/{assessment_id}/calculate")
def calculate(assessment_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        a = svc.calculate(db, assessment_id)
        return svc.assessment_to_dict(db, a)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.post("/assessments/{assessment_id}/approve")
def approve(assessment_id: int, req: ApproveReq, db: Session = Depends(get_db)) -> dict:
    try:
        a = svc.approve(db, assessment_id, approved_by=req.approved_by)
        return svc.assessment_to_dict(db, a)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.post("/assessments/{assessment_id}/reject")
def reject(assessment_id: int, req: ReasonReq, db: Session = Depends(get_db)) -> dict:
    if not req.reason:
        raise HTTPException(status_code=422, detail="a reason is required to reject")
    try:
        a = svc.reject(db, assessment_id, actor=req.actor, reason=req.reason)
        return svc.assessment_to_dict(db, a)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.post("/assessments/{assessment_id}/revise", status_code=201)
def revise(assessment_id: int, req: ReasonReq, db: Session = Depends(get_db)) -> dict:
    try:
        a = svc.revise(db, assessment_id, actor=req.actor, reason=req.reason)
        return svc.assessment_to_dict(db, a)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.post("/assessments/{assessment_id}/image", status_code=201)
async def upload_image(assessment_id: int, file: UploadFile = File(...),
                       db: Session = Depends(get_db)) -> dict:
    raw = await file.read()
    try:
        return rgsvc.attach_image(db, assessment_id, raw, file.filename or "")
    except ImagingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.get("/assessments/{assessment_id}/report", response_class=HTMLResponse)
def report(assessment_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    try:
        return HTMLResponse(content=svc.report_html(db, assessment_id))
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc


@router.get("/radiographs/{radiograph_id}/{kind}")
def get_radiograph_image(radiograph_id: int, kind: str,
                         db: Session = Depends(get_db)) -> FileResponse:
    if kind not in ("thumbnail", "analysis"):
        raise HTTPException(status_code=404, detail="unknown image kind")
    try:
        path = rgsvc.radiograph_file(db, radiograph_id, kind)
    except svc.AssessmentError as exc:
        raise _handle(exc) from exc
    return FileResponse(path, media_type="image/png")

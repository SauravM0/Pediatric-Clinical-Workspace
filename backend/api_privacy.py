"""Data-principal rights endpoints (DPDP Act 2023 — security phase, C.3).

Thin HTTP layer over ``privacy_service``. Everything here requires
MANAGE_DATA_RIGHTS, which doctors and admins carry and assistants do not:
exporting a whole record or erasing a patient is not front-desk work.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import privacy_service as svc
from backend.db import get_db
from backend.models import User
from backend.security import roles
from backend.security.deps import require

router = APIRouter(
    prefix="/api/privacy",
    tags=["privacy"],
    dependencies=[Depends(require(roles.MANAGE_DATA_RIGHTS))],
)


def _fail(exc: svc.PrivacyError) -> HTTPException:
    detail = str(exc)
    return HTTPException(404 if "not found" in detail else 422, detail)


class ConsentBody(BaseModel):
    purpose: str = Field(..., description=f"one of {svc.PURPOSES}")
    granted: bool
    given_by: Optional[str] = Field(None, description="parent/guardian for a minor")
    relationship: Optional[str] = Field(None, description="e.g. 'mother', 'self'")
    notice_version: Optional[str] = None
    note: Optional[str] = None


class ErasureBody(BaseModel):
    requested_by: Optional[str] = None
    reason: Optional[str] = None


class ExecuteErasureBody(BaseModel):
    mode: str = Field("pseudonymise", description="'pseudonymise' (default) or 'delete'")


@router.get("/purposes")
def purposes() -> dict[str, Any]:
    """The closed set of purposes data may be processed for."""
    return {
        "purposes": list(svc.PURPOSES),
        "default_granted": sorted(svc.DEFAULT_GRANTED),
        "note": "Consent is recorded per purpose. Absence of a record means NOT granted.",
    }


@router.post("/patients/{patient_id}/consent", status_code=201)
def record_consent(patient_id: int, body: ConsentBody, db: Session = Depends(get_db),
                   actor: User = Depends(require(roles.MANAGE_DATA_RIGHTS))) -> dict[str, Any]:
    """Record consent OR its withdrawal. Withdrawal is `granted: false` on the
    same endpoint -- DPDP requires withdrawal to be as easy as giving."""
    try:
        row = svc.record_consent(
            db, patient_id=patient_id, purpose=body.purpose, granted=body.granted,
            given_by=body.given_by, relationship=body.relationship,
            notice_version=body.notice_version, note=body.note,
            actor_user_id=actor.id or None,
        )
    except svc.PrivacyError as exc:
        raise _fail(exc) from exc
    return {"id": row.id, "purpose": row.purpose, "granted": row.granted,
            "recorded_at": row.recorded_at.isoformat()}


@router.get("/patients/{patient_id}/consent")
def get_consent(patient_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    return svc.consent_state(db, patient_id)


@router.get("/patients/{patient_id}/export")
def export_patient(patient_id: int, db: Session = Depends(get_db),
                   actor: User = Depends(require(roles.MANAGE_DATA_RIGHTS))) -> dict[str, Any]:
    """Right of access: everything held about this patient."""
    try:
        return svc.export_patient(db, patient_id, actor_username=actor.username)
    except svc.PrivacyError as exc:
        raise _fail(exc) from exc


@router.post("/patients/{patient_id}/erasure", status_code=201)
def request_erasure(patient_id: int, body: ErasureBody,
                    db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        row = svc.request_erasure(db, patient_id=patient_id,
                                  requested_by=body.requested_by, reason=body.reason)
    except svc.PrivacyError as exc:
        raise _fail(exc) from exc
    return {"id": row.id, "patient_id": row.patient_id, "status": row.status,
            "requested_at": row.requested_at.isoformat()}


@router.post("/erasure/{request_id}/execute")
def execute_erasure(request_id: int, body: ExecuteErasureBody,
                    db: Session = Depends(get_db),
                    actor: User = Depends(require(roles.MANAGE_DATA_RIGHTS))) -> dict[str, Any]:
    try:
        outcome = svc.execute_erasure(db, request_id, mode=body.mode,
                                      actor_user_id=actor.id or None,
                                      actor_username=actor.username)
    except svc.PrivacyError as exc:
        raise _fail(exc) from exc
    return {"request_id": request_id, **outcome.__dict__}


@router.get("/retention")
def retention(db: Session = Depends(get_db)) -> dict[str, Any]:
    return svc.retention_review(db)

"""Consent, access, erasure and retention (DPDP Act 2023 — security phase, C.3).

India's Digital Personal Data Protection Act 2023 gives a data principal rights
this product previously had no way to honour: to know what is held, to withdraw
consent as easily as it was given, and to have data erased. A paediatric record
adds a wrinkle -- the data principal is a child, so consent is given by a parent
or guardian and must be recorded as such.

Two design decisions worth defending:

**Consent is per purpose, and withdrawal is a new row.** Agreeing to clinical
care is not agreeing to have your child's radiograph used to train a model. One
boolean cannot express that, and overwriting a consent row destroys the evidence
of what was agreed and when -- which is exactly what a regulator asks for.

**Erasure pseudonymises by default rather than deleting.** A clinical record has
retention obligations that outlive a deletion request, and silently hard-deleting
an assessment that a treatment decision rested on creates a different kind of
harm. So the identifying layer is destroyed (name, and the link back to a person)
while the de-identified clinical rows are retained, and the outcome is written
down. Full deletion remains available and is recorded as such when chosen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    BoneAssessment,
    ConsentRecord,
    ErasureRequest,
    Patient,
    Radiograph,
    TW3Assessment,
)
from backend.security.sessions import record_security_event

# Purposes the product actually processes data for. A purpose that is not on
# this list cannot be consented to, which is what stops "consent" drifting into
# a blanket permission (DPDP: purpose limitation).
PURPOSES: tuple[str, ...] = (
    "clinical_care",     # the treating clinician's own use
    "model_training",    # de-identified crops used to improve the AI
    "research",          # aggregate analysis / publication
    "quality_audit",     # internal accuracy monitoring
)

# Consent for clinical care is what makes treatment possible; the others are
# genuinely optional and must default to NOT granted.
DEFAULT_GRANTED: frozenset[str] = frozenset()

# Retention: how long a record is kept after its last clinical activity.
# Indian medical-record guidance for minors is conservative -- the clock is
# usually taken from majority, not from the visit. Encoded here so it is a
# reviewable number rather than an assumption buried in code.
RETENTION_YEARS_AFTER_LAST_ACTIVITY = 8
RETENTION_NOTE = (
    "Retained for 8 years after last clinical activity. For a minor, Indian "
    "medical-record guidance commonly runs from the age of majority; review "
    "this against your own centre's policy and the treating clinician's advice."
)


class PrivacyError(ValueError):
    """Invalid privacy operation (maps to 4xx at the API layer)."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── consent ─────────────────────────────────────────────────────────────────

def record_consent(db: Session, *, patient_id: int, purpose: str, granted: bool,
                   given_by: str | None = None, relationship: str | None = None,
                   notice_version: str | None = None, note: str | None = None,
                   actor_user_id: int | None = None) -> ConsentRecord:
    if purpose not in PURPOSES:
        raise PrivacyError(f"purpose must be one of {PURPOSES}")
    if db.get(Patient, patient_id) is None:
        raise PrivacyError(f"patient {patient_id} not found")

    row = ConsentRecord(
        patient_id=patient_id, purpose=purpose, granted=granted,
        given_by=given_by, relationship=relationship,
        notice_version=notice_version, note=note,
        recorded_by_user_id=actor_user_id,
    )
    db.add(row)
    record_security_event(
        db, event_type="consent_recorded", patient_id=patient_id,
        detail=f"purpose={purpose} granted={granted} by={given_by or 'unspecified'}",
    )
    db.flush()
    return row


def consent_state(db: Session, patient_id: int) -> dict[str, Any]:
    """Current consent per purpose = the most recent row for that purpose.

    History is preserved (rows are appended, never edited), so this is a
    projection rather than the stored truth.
    """
    rows = db.execute(
        select(ConsentRecord).where(ConsentRecord.patient_id == patient_id)
        .order_by(ConsentRecord.recorded_at, ConsentRecord.id)
    ).scalars().all()

    latest: dict[str, ConsentRecord] = {}
    for row in rows:
        latest[row.purpose] = row

    return {
        "patient_id": patient_id,
        "purposes": {
            purpose: {
                "granted": bool(latest[purpose].granted) if purpose in latest
                           else (purpose in DEFAULT_GRANTED),
                "recorded_at": latest[purpose].recorded_at.isoformat() if purpose in latest else None,
                "given_by": latest[purpose].given_by if purpose in latest else None,
                "relationship": latest[purpose].relationship if purpose in latest else None,
                "explicitly_recorded": purpose in latest,
            }
            for purpose in PURPOSES
        },
        "history_count": len(rows),
        "note": "Absence of a record is treated as NOT granted (DPDP: consent must be affirmative).",
    }


def has_consent(db: Session, patient_id: int, purpose: str) -> bool:
    state = consent_state(db, patient_id)["purposes"].get(purpose)
    return bool(state and state["granted"])


# ── right of access ─────────────────────────────────────────────────────────

def export_patient(db: Session, patient_id: int, *, actor_username: str | None = None) -> dict[str, Any]:
    """Everything held about one patient, for the data principal (DPDP s.11).

    Deliberately a complete dump including the identifying fields: this is the
    subject's own data being returned to them, so redacting it would defeat the
    right. The export itself is logged, because handing over a full record is an
    event a centre should be able to account for.
    """
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise PrivacyError(f"patient {patient_id} not found")

    assessments = db.execute(
        select(TW3Assessment).where(TW3Assessment.patient_id == patient_id)
    ).scalars().all()
    radiographs = db.execute(
        select(Radiograph).where(Radiograph.patient_id == patient_id)
    ).scalars().all()

    def bones_for(assessment_id: int) -> list[dict[str, Any]]:
        rows = db.execute(
            select(BoneAssessment).where(BoneAssessment.assessment_id == assessment_id)
        ).scalars().all()
        return [{"bone_code": b.bone_code, "group": b.bone_group,
                 "confirmed_stage": b.confirmed_stage,
                 "score": b.sex_specific_score} for b in rows]

    record_security_event(
        db, event_type="data_export", patient_id=patient_id, username=actor_username,
        detail=f"full record export: {len(assessments)} assessment(s), "
               f"{len(radiographs)} radiograph(s)",
    )

    return {
        "exported_at": _utcnow().isoformat(),
        "patient": {
            "patient_code": patient.patient_code,
            "name": patient.name,
            "sex_at_birth": patient.sex_at_birth,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "created_at": patient.created_at.isoformat(),
        },
        "consent": consent_state(db, patient_id),
        "assessments": [
            {
                "id": a.id, "created_at": a.created_at.isoformat(),
                "method": a.assessment_method, "status": a.assessment_status,
                "total_rus_score": a.total_rus_score,
                "bone_age_months": a.bone_age_months,
                "approved_by": a.approved_by,
                "bones": bones_for(a.id),
            } for a in assessments
        ],
        "radiographs": [
            {"id": r.id, "study_date": r.study_date.isoformat() if r.study_date else None,
             "source_format": r.source_format, "quality_status": r.quality_status,
             "consent_status": r.consent_status,
             "anonymisation_status": r.anonymisation_status}
            for r in radiographs
        ],
        "retention": {"policy_years": RETENTION_YEARS_AFTER_LAST_ACTIVITY,
                      "note": RETENTION_NOTE},
    }


# ── right to erasure ────────────────────────────────────────────────────────

@dataclass
class ErasureOutcome:
    mode: str
    identifiers_removed: bool
    assessments_retained: int
    radiographs_retained: int
    rows_deleted: int
    rationale: str


def request_erasure(db: Session, *, patient_id: int, requested_by: str | None,
                    reason: str | None = None) -> ErasureRequest:
    if db.get(Patient, patient_id) is None:
        raise PrivacyError(f"patient {patient_id} not found")
    row = ErasureRequest(patient_id=patient_id, requested_by=requested_by, reason=reason)
    db.add(row)
    record_security_event(db, event_type="erasure_requested", patient_id=patient_id,
                          detail=f"requested by {requested_by or 'unspecified'}")
    db.flush()
    return row


def execute_erasure(db: Session, request_id: int, *, mode: str = "pseudonymise",
                    actor_user_id: int | None = None,
                    actor_username: str | None = None) -> ErasureOutcome:
    """Carry out an erasure request.

    ``pseudonymise`` (default) destroys the identifying layer and keeps the
    de-identified clinical rows. ``delete`` removes everything. The default is
    the conservative one because a clinical record carries retention duties that
    a deletion request does not automatically override -- and because destroying
    an assessment a treatment decision rested on is its own harm. Choosing
    ``delete`` is a deliberate act and is recorded as one.
    """
    if mode not in ("pseudonymise", "delete"):
        raise PrivacyError("mode must be 'pseudonymise' or 'delete'")

    req = db.get(ErasureRequest, request_id)
    if req is None:
        raise PrivacyError(f"erasure request {request_id} not found")
    if req.status != "pending":
        raise PrivacyError(f"request is already {req.status}")

    patient = db.get(Patient, req.patient_id)
    if patient is None:
        raise PrivacyError("patient no longer exists")

    assessments = db.execute(
        select(TW3Assessment).where(TW3Assessment.patient_id == patient.id)
    ).scalars().all()
    radiographs = db.execute(
        select(Radiograph).where(Radiograph.patient_id == patient.id)
    ).scalars().all()

    deleted = 0
    if mode == "pseudonymise":
        patient.name = None
        patient.date_of_birth = None
        patient.patient_code = f"ERASED-{patient.id}"
        for r in radiographs:
            r.original_filename = None
            r.consent_status = "withheld"  # never reaches a training export again
        outcome = ErasureOutcome(
            mode=mode, identifiers_removed=True,
            assessments_retained=len(assessments),
            radiographs_retained=len(radiographs), rows_deleted=0,
            rationale=("Identifying layer destroyed; de-identified clinical rows "
                       "retained under the medical-record retention policy. The "
                       "data can no longer be attributed to a person."),
        )
    else:
        for a in assessments:
            for b in db.execute(
                select(BoneAssessment).where(BoneAssessment.assessment_id == a.id)
            ).scalars().all():
                db.delete(b)
                deleted += 1
            db.delete(a)
            deleted += 1
        for r in radiographs:
            db.delete(r)
            deleted += 1
        patient.name = None
        patient.date_of_birth = None
        patient.patient_code = f"ERASED-{patient.id}"
        outcome = ErasureOutcome(
            mode=mode, identifiers_removed=True, assessments_retained=0,
            radiographs_retained=0, rows_deleted=deleted,
            rationale=("Full erasure at the data principal's request. Clinical "
                       "rows were destroyed; stored image files must be removed "
                       "from disk separately."),
        )

    req.status = "completed"
    req.decided_by_user_id = actor_user_id
    req.decided_at = _utcnow()
    req.outcome_json = json.dumps(outcome.__dict__)

    record_security_event(
        db, event_type="erasure", severity="warn", patient_id=patient.id,
        username=actor_username, detail=f"mode={mode}; {outcome.rationale}",
    )
    db.flush()
    return outcome


# ── retention ───────────────────────────────────────────────────────────────

def retention_review(db: Session) -> dict[str, Any]:
    """Patients whose last activity is older than the retention period.

    Reports only -- deletion stays a human decision. An automatic purge of
    paediatric clinical records would be the wrong default.
    """
    cutoff = _utcnow() - timedelta(days=365 * RETENTION_YEARS_AFTER_LAST_ACTIVITY)
    overdue: list[dict[str, Any]] = []
    for patient in db.execute(select(Patient)).scalars().all():
        if str(patient.patient_code).startswith("ERASED-"):
            continue
        last = db.execute(
            select(TW3Assessment.updated_at).where(TW3Assessment.patient_id == patient.id)
            .order_by(TW3Assessment.updated_at.desc()).limit(1)
        ).scalar_one_or_none() or patient.created_at
        if last < cutoff:
            overdue.append({"patient_id": patient.id,
                            "patient_code": patient.patient_code,
                            "last_activity": last.isoformat()})
    return {
        "policy_years": RETENTION_YEARS_AFTER_LAST_ACTIVITY,
        "note": RETENTION_NOTE,
        "cutoff": cutoff.isoformat(),
        "overdue": overdue,
        "action": "Review is reported, never automatic -- deletion of a paediatric "
                  "clinical record is a human decision.",
    }

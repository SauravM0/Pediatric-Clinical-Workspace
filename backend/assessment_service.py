"""Assessment lifecycle service (directive §16, §17, §19).

Pure DB logic, kept out of the HTTP layer. Enforces:
* one Patient per patient_code,
* exactly 13 bone rows per assessment,
* legal state transitions (draft → ready_for_review → approved/rejected;
  approved → superseded via a new revision),
* immutability of approved assessments (edits create a new revision),
* an audit trail for every meaningful action.

Scoring is delegated entirely to the deterministic engine (backend.tw3).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import APP_VERSION
from backend.models import AuditEvent, BoneAssessment, Patient, Radiograph, TW3Assessment
from backend.tw3 import (
    AssessmentStatus,
    DEFAULT_STAGE_SYSTEM,
    LETTER_STAGES,
    ScoringError,
    StageSystem,
    bone_group,
    bones_for_system,
    calculate_strict,
    compute,
    load_tables,
    scoring_enabled,
)


class AssessmentError(ValueError):
    """Invalid lifecycle operation (maps to HTTP 409/422 at the API layer)."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _audit(db: Session, *, assessment_id: Optional[int], patient_id: Optional[int],
           event_type: str, actor: str, previous=None, new=None,
           reason: Optional[str] = None, model_version: Optional[str] = None) -> None:
    db.add(AuditEvent(
        assessment_id=assessment_id, patient_id=patient_id, event_type=event_type,
        actor=actor, previous_value=None if previous is None else json.dumps(previous),
        new_value=None if new is None else json.dumps(new), reason=reason,
        application_version=APP_VERSION, model_version=model_version,
    ))


def get_or_create_patient(db: Session, *, patient_code: str, sex: str,
                          name: Optional[str] = None,
                          date_of_birth: Optional[datetime] = None) -> Patient:
    patient = db.execute(
        select(Patient).where(Patient.patient_code == patient_code)
    ).scalar_one_or_none()
    if patient is None:
        patient = Patient(patient_code=patient_code, sex_at_birth=sex,
                          name=name, date_of_birth=date_of_birth)
        db.add(patient)
        db.flush()
    return patient


def create_assessment(db: Session, *, patient_code: str, sex: str,
                      name: Optional[str] = None,
                      date_of_birth: Optional[datetime] = None,
                      chronological_age_months: Optional[int] = None,
                      stage_system: str = DEFAULT_STAGE_SYSTEM,
                      reader_id: Optional[str] = None, read_round: int = 1,
                      actor: str = "local-user") -> TW3Assessment:
    if sex not in ("boys", "girls"):
        raise AssessmentError(f"unsupported sex: {sex!r}")
    if stage_system not in (s.value for s in StageSystem):
        raise AssessmentError(f"unknown stage system: {stage_system!r}")
    patient = get_or_create_patient(db, patient_code=patient_code, sex=sex,
                                    name=name, date_of_birth=date_of_birth)
    assessment = TW3Assessment(
        patient_id=patient.id, sex_at_birth=sex,
        chronological_age_months=chronological_age_months,
        stage_system=stage_system,
        reader_id=reader_id, read_round=read_round,
        assessment_status=AssessmentStatus.DRAFT.value,
        application_version=APP_VERSION,
    )
    db.add(assessment)
    db.flush()
    # Create one bone row per bone in this system: 13 RUS (tw3c-rus) or 13 RUS +
    # 7 carpals (tw3-letters) — directive §9.4, §15.
    for bone in bones_for_system(stage_system):
        db.add(BoneAssessment(assessment_id=assessment.id, bone_code=bone,
                              bone_group=bone_group(bone)))
    _audit(db, assessment_id=assessment.id, patient_id=patient.id, event_type="create",
           actor=actor, new={"status": "draft", "sex": sex, "stage_system": stage_system})
    db.flush()
    return assessment


def get_assessment(db: Session, assessment_id: int) -> TW3Assessment:
    a = db.get(TW3Assessment, assessment_id)
    if a is None:
        raise AssessmentError(f"assessment {assessment_id} not found")
    return a


def _confirmed_stages(a: TW3Assessment) -> dict[str, str]:
    return {b.bone_code: b.confirmed_stage for b in a.bones if b.confirmed_stage}


def _letter_stage_groups(a: TW3Assessment) -> tuple[dict[str, str], dict[str, str]]:
    """Split confirmed stages into (rus_stages, carpal_stages) for the letter engine."""
    rus, carpal = {}, {}
    for b in a.bones:
        if not b.confirmed_stage:
            continue
        (carpal if b.bone_group == "carpal" else rus)[b.bone_code] = b.confirmed_stage
    return rus, carpal


def _letters_block(a: TW3Assessment) -> dict:
    """Live original-TW3 letter result (RUS + carpal, independent) for display.
    Everything is None/'—' until the clinic's licensed letter tables are entered."""
    from backend.tw3.letters_scoring import compute_letters, load_letter_tables

    t = load_letter_tables()
    rus_stages, carpal_stages = _letter_stage_groups(a)
    r = compute_letters(rus_stages, carpal_stages, a.sex_at_birth, t)

    def group(g) -> dict:
        return {
            "total_score": g.total_score if g.complete else None,
            "staged_count": g.staged_count, "total_bones": g.total_bones,
            "complete": g.complete,
            "points_calibrated": g.points_calibrated,
            "twii_age_years": g.twii_age_years,
            "twiii_age_years": g.twiii_age_years,
            "missing_stage": list(g.missing_stage),
        }

    return {
        "table_version": t.version,
        "any_calibrated": t.any_calibrated(),
        "rus": group(r.rus),
        "carpal": group(r.carpal),
        "tw20": {
            "total_score": r.tw20.total_score if r.tw20.complete else None,
            "age_years": r.tw20.age_years, "complete": r.tw20.complete,
            "staged_count": r.tw20.staged_count, "total_bones": r.tw20.total_bones,
            "points_calibrated": r.tw20.points_calibrated,
        },
    }


def set_bone_stage(db: Session, assessment_id: int, bone_code: str, stage: Optional[str],
                   *, actor: str = "local-user", reason: Optional[str] = None,
                   rater_id: Optional[str] = None) -> TW3Assessment:
    a = get_assessment(db, assessment_id)
    if a.assessment_status == AssessmentStatus.APPROVED.value:
        raise AssessmentError("assessment is approved and immutable; open a revision to edit")
    if a.assessment_status == AssessmentStatus.SUPERSEDED.value:
        raise AssessmentError("assessment is superseded; edit the current revision")
    if bone_code not in bones_for_system(a.stage_system):
        raise AssessmentError(f"unknown bone code {bone_code!r} for {a.stage_system}")

    if stage is not None:
        if a.stage_system == StageSystem.TW3_LETTERS.value:
            if stage not in LETTER_STAGES:
                raise AssessmentError(f"invalid letter stage {stage!r} for {bone_code}")
        else:
            tables = load_tables()
            if stage not in tables.stages_for(bone_code):
                raise AssessmentError(f"invalid grade {stage!r} for {bone_code}")

    row = next((b for b in a.bones if b.bone_code == bone_code), None)
    if row is None:  # defensive; creation guarantees 13 rows
        row = BoneAssessment(assessment_id=a.id, bone_code=bone_code)
        db.add(row)
    previous = row.confirmed_stage
    row.doctor_stage = stage
    row.confirmed_stage = stage
    if rater_id is not None:
        row.rater_id = rater_id
    if row.ai_suggested_stage and stage and stage != row.ai_suggested_stage:
        row.doctor_modified_ai_result = True
        row.modification_reason = reason

    # Editing after a calculation invalidates it: return to draft.
    if a.assessment_status == AssessmentStatus.READY_FOR_REVIEW.value:
        a.assessment_status = AssessmentStatus.DRAFT.value
        a.total_rus_score = a.bone_age_years = a.bone_age_months = None
        a.bone_age_difference_months = None

    event = "stage_modification" if previous else "stage_assignment"
    _audit(db, assessment_id=a.id, patient_id=a.patient_id, event_type=event, actor=actor,
           previous={bone_code: previous}, new={bone_code: stage}, reason=reason)
    db.flush()
    return a


def calculate(db: Session, assessment_id: int, *, actor: str = "local-user") -> TW3Assessment:
    a = get_assessment(db, assessment_id)
    if a.assessment_status == AssessmentStatus.APPROVED.value:
        raise AssessmentError("assessment is approved; open a revision to recalculate")

    if a.stage_system == StageSystem.TW3_LETTERS.value:
        return _calculate_letters(db, a, actor=actor)

    tables = load_tables()
    stages = _confirmed_stages(a)
    try:
        result = calculate_strict(stages, a.sex_at_birth, tables)
    except ScoringError as exc:
        raise AssessmentError(str(exc)) from exc

    # Persist per-bone scores.
    score_by_bone = {b.bone_code: b.score for b in result.bones}
    for row in a.bones:
        row.sex_specific_score = score_by_bone.get(row.bone_code)

    a.total_rus_score = result.total_rus_score
    a.bone_age_months = result.bone_age_months
    a.bone_age_years = result.bone_age_years
    a.scoring_table_version = result.table_version
    a.assessment_method = result.method
    if a.chronological_age_months is not None and result.bone_age_months is not None:
        a.bone_age_difference_months = result.bone_age_months - a.chronological_age_months
    a.assessment_status = AssessmentStatus.READY_FOR_REVIEW.value

    _audit(db, assessment_id=a.id, patient_id=a.patient_id, event_type="calculation",
           actor=actor, new={"total_rus_score": result.total_rus_score,
                             "bone_age_months": result.bone_age_months,
                             "table_version": result.table_version})
    db.flush()
    return a


def _calculate_letters(db: Session, a: TW3Assessment, *, actor: str) -> TW3Assessment:
    """Original-TW3 letter calculation. Requires the clinic's licensed tables to be
    entered AND to reproduce the reference cases (accuracy gate) before it will run."""
    from backend.tw3.letters_scoring import (
        compute_letters, load_letter_tables, validate_reference_cases)

    t = load_letter_tables()
    if not t.any_calibrated():
        raise AssessmentError(
            "original-TW3 letter scoring is not enabled: the clinic's licensed TW3 "
            "point/age tables have not been entered yet (backend/tw3/letters_tables.json). "
            "Staging is saved; scores appear once the tables are supplied (Gate 1).")
    validation = validate_reference_cases(t)
    if not validation["all_passed"]:
        raise AssessmentError(
            "original-TW3 letter scoring is blocked by the accuracy gate: the entered "
            "tables do not reproduce the clinic's reference case(s). Fix the table values "
            "or the reference cases before scoring (accuracy is paramount).")

    rus_stages, carpal_stages = _letter_stage_groups(a)
    r = compute_letters(rus_stages, carpal_stages, a.sex_at_birth, t)
    if not r.rus.complete:
        raise AssessmentError(
            f"incomplete: {len(r.rus.missing_stage)} of {r.rus.total_bones} RUS bones unstaged")
    if r.rus.twiii_age_months is None:
        raise AssessmentError("RUS score→age (TWIII) curve is not entered for this sex")

    # Persist per-bone scores (RUS + carpal).
    by_bone = {}
    for grp, stages, table in (("rus", rus_stages, t.rus_pts), ("carpal", carpal_stages, t.carpal_pts)):
        pts = table.get(a.sex_at_birth, {})
        for bone, letter in stages.items():
            by_bone[bone] = (pts.get(bone) or {}).get(letter)
    for row in a.bones:
        row.sex_specific_score = by_bone.get(row.bone_code)

    a.total_rus_score = r.rus.total_score
    a.bone_age_months = r.rus.twiii_age_months            # primary = TWIII-RUS
    a.bone_age_years = r.rus.twiii_age_years
    a.total_carpal_score = r.carpal.total_score if r.carpal.complete else None
    a.carpal_bone_age_months = r.carpal.twiii_age_months
    a.scoring_table_version = t.version
    a.assessment_method = t.method
    if a.chronological_age_months is not None and r.rus.twiii_age_months is not None:
        a.bone_age_difference_months = r.rus.twiii_age_months - a.chronological_age_months
    a.assessment_status = AssessmentStatus.READY_FOR_REVIEW.value

    _audit(db, assessment_id=a.id, patient_id=a.patient_id, event_type="calculation",
           actor=actor, new={"total_rus_score": r.rus.total_score,
                             "twiii_rus_age_months": r.rus.twiii_age_months,
                             "total_carpal_score": a.total_carpal_score,
                             "table_version": t.version})
    db.flush()
    return a


def approve(db: Session, assessment_id: int, *, approved_by: str) -> TW3Assessment:
    a = get_assessment(db, assessment_id)
    if a.assessment_status != AssessmentStatus.READY_FOR_REVIEW.value:
        raise AssessmentError(
            f"cannot approve from status '{a.assessment_status}'; calculate first")
    a.doctor_approved = True
    a.approved_by = approved_by
    a.approved_at = _utcnow()
    a.assessment_status = AssessmentStatus.APPROVED.value
    _audit(db, assessment_id=a.id, patient_id=a.patient_id, event_type="approval",
           actor=approved_by, new={"status": "approved", "bone_age_months": a.bone_age_months})
    db.flush()
    return a


def reject(db: Session, assessment_id: int, *, actor: str, reason: str) -> TW3Assessment:
    a = get_assessment(db, assessment_id)
    if a.assessment_status == AssessmentStatus.APPROVED.value:
        raise AssessmentError("approved assessment cannot be rejected; open a revision")
    a.assessment_status = AssessmentStatus.REJECTED.value
    _audit(db, assessment_id=a.id, patient_id=a.patient_id, event_type="rejection",
           actor=actor, reason=reason, new={"status": "rejected"})
    db.flush()
    return a


def revise(db: Session, assessment_id: int, *, actor: str,
           reason: Optional[str] = None) -> TW3Assessment:
    """Create a new draft revision from an existing (usually approved) assessment,
    copying the patient, sex, chronological age and bone grades. The original is
    marked superseded and never overwritten (directive §19)."""
    old = get_assessment(db, assessment_id)
    new = TW3Assessment(
        patient_id=old.patient_id, radiograph_id=old.radiograph_id,
        sex_at_birth=old.sex_at_birth,
        chronological_age_months=old.chronological_age_months,
        stage_system=old.stage_system,
        assessment_method=old.assessment_method,
        assessment_status=AssessmentStatus.DRAFT.value,
        revision=old.revision + 1, supersedes_id=old.id,
        application_version=APP_VERSION,
    )
    db.add(new)
    db.flush()
    for b in old.bones:
        db.add(BoneAssessment(
            assessment_id=new.id, bone_code=b.bone_code, bone_group=b.bone_group,
            doctor_stage=b.doctor_stage, confirmed_stage=b.confirmed_stage,
            ai_suggested_stage=b.ai_suggested_stage,
        ))
    old.assessment_status = AssessmentStatus.SUPERSEDED.value
    _audit(db, assessment_id=old.id, patient_id=old.patient_id, event_type="reopening",
           actor=actor, reason=reason, new={"superseded_by_revision": new.revision})
    _audit(db, assessment_id=new.id, patient_id=new.patient_id, event_type="create",
           actor=actor, reason=reason, previous={"revision": old.revision},
           new={"revision": new.revision})
    db.flush()
    return new


def localize_assessment(db: Session, assessment_id: int) -> dict:
    """Run the PEA localizer on the assessment's attached film → per-bone boxes +
    image dimensions. Honest degradation if no film or no model is installed."""
    from PIL import Image

    from backend.ai import localize as loc

    a = get_assessment(db, assessment_id)
    if not a.radiograph_id:
        raise AssessmentError("attach a film first, then auto-locate the bones")
    from backend import radiograph_service as rgsvc  # local import avoids a cycle
    path = rgsvc.radiograph_file(db, a.radiograph_id, "analysis")
    with Image.open(path) as img:
        width, height = img.size
        if not loc.model_available():
            return {"available": False, "image_width": width, "image_height": height,
                    "boxes": [], "message": "No localizer model installed — draw boxes "
                    "manually, or train one (see backend/ai/LOCALIZE.md)."}
        result = loc.predict_boxes(img.copy()) or {}
    return {"available": True, "image_width": width, "image_height": height,
            "model_version": result.get("model_version"), "boxes": result.get("boxes", [])}


def set_bone_box(db: Session, assessment_id: int, bone_code: str, box, *,
                 confidence: Optional[float] = None, actor: str = "local-user") -> TW3Assessment:
    """Persist (or clear) a bone's localisation box [x0,y0,x1,y1] in image pixels."""
    a = get_assessment(db, assessment_id)
    if a.assessment_status in (AssessmentStatus.APPROVED.value, AssessmentStatus.SUPERSEDED.value):
        raise AssessmentError("assessment is locked; open a revision to change boxes")
    if bone_code not in bones_for_system(a.stage_system):
        raise AssessmentError(f"unknown bone code {bone_code!r} for {a.stage_system}")
    row = next((b for b in a.bones if b.bone_code == bone_code), None)
    if row is None:
        raise AssessmentError(f"bone {bone_code!r} not on this assessment")
    previous = row.localisation_box
    if box is None:
        row.localisation_box = None
        row.localisation_confidence = None
    else:
        if not (isinstance(box, (list, tuple)) and len(box) == 4):
            raise AssessmentError("box must be [x0, y0, x1, y1]")
        x0, y0, x1, y1 = (float(v) for v in box)
        if x1 <= x0 or y1 <= y0:
            raise AssessmentError("box must have positive width and height")
        row.localisation_box = json.dumps([round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)])
        if confidence is not None:
            row.localisation_confidence = float(confidence)
    _audit(db, assessment_id=a.id, patient_id=a.patient_id, event_type="localisation",
           actor=actor, previous={bone_code: previous}, new={bone_code: row.localisation_box})
    db.flush()
    return a


def report_html(db: Session, assessment_id: int, *, actor: str = "local-user") -> str:
    """Render the English TW3-C report; requires a calculated assessment (§20)."""
    a = get_assessment(db, assessment_id)
    if a.bone_age_months is None:
        raise AssessmentError("cannot generate report: assessment is not calculated")
    from backend.reports import render_report_html
    data = assessment_to_dict(db, a)
    rg = db.get(Radiograph, a.radiograph_id) if a.radiograph_id else None
    html = render_report_html(a, data, rg)
    _audit(db, assessment_id=a.id, patient_id=a.patient_id,
           event_type="report_generation", actor=actor,
           new={"status": a.assessment_status})
    db.flush()
    return html


# ── AI stage-suggestion activation gate (Plan 2 WI-8 wiring) ────────────────────

def suggestion_activation(db: Session, *, sex: str = "all") -> dict:
    """Per-bone: may an AI stage suggestion be shown? (label-quality gate.)

    Cheap short-circuit until an auto-stager model exists — with no model, every
    bone is "manual" and no coverage query runs. Once Plan 4 installs a stager, the
    full gate applies: support (distinct patients/stage) ^ consensus agreement ^
    validated calibration (backend.ai.suggestion_gate). Never fabricates a
    suggestion; the doctor still confirms every bone.
    """
    from backend.ai import stage_classifier
    from backend.ai.suggestion_gate import activation_map

    installed = list(stage_classifier.available_bones() or [])
    if not installed:
        return {"any_model_installed": False, "n_allowed": 0, "decisions": {},
                "note": "auto-staging model not installed — all bones manual"}

    from backend.tw3.pipeline.export_dataset import coverage_report
    calibrated = {b: bool((stage_classifier.model_metadata(b) or {}).get("calibrated"))
                  for b in installed}
    amap = activation_map(coverage_report(db), calibrated_bones=calibrated, sex=sex)
    return {"any_model_installed": True, **amap}


def _bone_suggestion_status(activation: dict, bone_code: str) -> dict:
    """Compact per-bone read of the activation decision for the serializer."""
    dec = (activation.get("decisions") or {}).get(bone_code)
    if not activation.get("any_model_installed"):
        return {"status": "manual", "reason": "auto-staging model not installed"}
    if dec is None:
        return {"status": "manual", "reason": "no coverage for this bone yet"}
    return {"status": "eligible" if dec["allowed"] else "manual",
            "reason": None if dec["allowed"] else "; ".join(dec["reasons"])}


# ── Serialization ─────────────────────────────────────────────────────────────

def assessment_to_dict(db: Session, a: TW3Assessment, *, include_audit: bool = False) -> dict:
    # Deterministic scoring only runs for a stage system that has verified tables.
    # For the letter (annotation-only) system, compute() would choke on letters
    # and carpal codes, so we count completion directly instead.
    scored = scoring_enabled(a.stage_system)
    live = compute(_confirmed_stages(a), a.sex_at_birth, load_tables()) if (scored and a.bones) else None

    order = {code: i for i, code in enumerate(bones_for_system(a.stage_system))}
    bones_sorted = sorted(a.bones, key=lambda x: order.get(x.bone_code, len(order)))
    rus_done = sum(1 for b in a.bones if b.bone_group == "rus" and b.confirmed_stage)
    carpal_done = sum(1 for b in a.bones if b.bone_group == "carpal" and b.confirmed_stage)
    activation = suggestion_activation(db, sex=a.sex_at_birth or "all")

    data = {
        "id": a.id,
        "patient_id": a.patient_id,
        "patient_code": a.patient.patient_code if a.patient else None,
        "sex_at_birth": a.sex_at_birth,
        "chronological_age_months": a.chronological_age_months,
        "assessment_method": a.assessment_method,
        "stage_system": a.stage_system,
        "scoring_enabled": scored,
        "assessment_status": a.assessment_status,
        "revision": a.revision,
        "supersedes_id": a.supersedes_id,
        "total_rus_score": a.total_rus_score,
        "total_carpal_score": a.total_carpal_score,
        "carpal_bone_age_months": a.carpal_bone_age_months,
        "bone_age_years": a.bone_age_years,
        "bone_age_months": a.bone_age_months,
        "bone_age_difference_months": a.bone_age_difference_months,
        "scoring_table_version": a.scoring_table_version,
        "quality_status": a.quality_status,
        "radiograph_id": a.radiograph_id,
        "doctor_approved": a.doctor_approved,
        "approved_by": a.approved_by,
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
        "application_version": a.application_version,
        "staged_count": live.staged_count if live else (rus_done + carpal_done),
        "rus_staged_count": rus_done,
        "carpal_staged_count": carpal_done,
        "live_status": live.status if live else None,
        "bones": [
            {
                "bone_code": b.bone_code,
                "bone_group": b.bone_group,
                "confirmed_stage": b.confirmed_stage,
                "ai_suggested_stage": b.ai_suggested_stage,
                "ai_suggestion_status": _bone_suggestion_status(activation, b.bone_code),
                "sex_specific_score": b.sex_specific_score,
                "doctor_modified_ai_result": b.doctor_modified_ai_result,
                "localisation_box": json.loads(b.localisation_box) if b.localisation_box else None,
                "localisation_confidence": b.localisation_confidence,
            }
            for b in bones_sorted
        ],
    }
    if a.stage_system == StageSystem.TW3_LETTERS.value:
        data["letters"] = _letters_block(a)
    if include_audit:
        events = db.execute(
            select(AuditEvent).where(AuditEvent.assessment_id == a.id)
            .order_by(AuditEvent.timestamp)
        ).scalars().all()
        data["audit"] = [
            {"event_type": e.event_type, "actor": e.actor,
             "timestamp": e.timestamp.isoformat(), "reason": e.reason,
             "previous_value": e.previous_value, "new_value": e.new_value,
             "application_version": e.application_version}
            for e in events
        ]
    return data

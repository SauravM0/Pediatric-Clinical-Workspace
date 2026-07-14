"""SQLAlchemy ORM models — the canonical local data model (directive §9).

One authoritative database. Entities: Patient, Radiograph, TW3Assessment,
BoneAssessment, AuditEvent, plus a SchemaVersion row for reproducibility.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend.config import DB_SCHEMA_VERSION


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Patient(Base):
    __tablename__ = "patient"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sex_at_birth: Mapped[str] = mapped_column(String(8), nullable=False)  # boys | girls
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    assessments: Mapped[list["TW3Assessment"]] = relationship(back_populates="patient")


class Radiograph(Base):
    __tablename__ = "radiograph"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False)
    study_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    internal_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bit_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    laterality: Mapped[str | None] = mapped_column(String(8), nullable=True)
    modality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quality_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Doctor-confirmable acquisition domain (directive §16): digital_diagnostic |
    # compressed | film_photo | unknown. Defaults to an inferred value on upload;
    # the doctor can correct it. Drives per-domain evaluation and warnings.
    source_domain: Mapped[str | None] = mapped_column(String(24), nullable=True)
    anonymisation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Consent for using de-identified crops in offline training (Plan 2 WI-9):
    # unknown | consented | research_ok | withheld. 'withheld' is ALWAYS excluded
    # from export; strict positive-consent is opt-in via export require_consent.
    consent_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class TW3Assessment(Base):
    __tablename__ = "tw3_assessment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False)
    radiograph_id: Mapped[int | None] = mapped_column(ForeignKey("radiograph.id"), nullable=True)
    sex_at_birth: Mapped[str] = mapped_column(String(8), nullable=False)
    chronological_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Which maturity vocabulary this assessment is staged in (see StageSystem).
    # 'tw3c-rus' (grades 1-8, 13 RUS, scoring on) or 'tw3-letters' (A-I, 20 bones,
    # scoring off until licensed tables exist).
    stage_system: Mapped[str] = mapped_column(String(24), default="tw3c-rus", nullable=False)
    # Reader attribution (Plan 2 WI-1): who produced this read, and which
    # independent-read round it is for the same film — enables multi-reader
    # consensus + adjudication computed from real assessments, not just feedback.
    reader_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    read_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    assessment_method: Mapped[str] = mapped_column(String(32), default="TW3-C-RUS")
    assessment_status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    total_rus_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Carpal is scored and aged SEPARATELY from RUS (never averaged; directive §15/§18).
    total_carpal_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    carpal_bone_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bone_age_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    bone_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bone_age_difference_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scoring_table_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    doctor_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(ForeignKey("tw3_assessment.id"), nullable=True)
    application_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="assessments")
    bones: Mapped[list["BoneAssessment"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class BoneAssessment(Base):
    __tablename__ = "bone_assessment"
    __table_args__ = (UniqueConstraint("assessment_id", "bone_code", name="uq_assessment_bone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("tw3_assessment.id"), nullable=False)
    bone_code: Mapped[str] = mapped_column(String(16), nullable=False)
    bone_group: Mapped[str] = mapped_column(String(8), default="rus", nullable=False)  # rus | carpal
    doctor_stage: Mapped[str | None] = mapped_column(String(4), nullable=True)
    rater_id: Mapped[str | None] = mapped_column(String(120), nullable=True)  # who staged (Plan 2 WI-1)
    ai_suggested_stage: Mapped[str | None] = mapped_column(String(4), nullable=True)
    ai_stage_probabilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_stage: Mapped[str | None] = mapped_column(String(4), nullable=True)
    sex_specific_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    localisation_box: Mapped[str | None] = mapped_column(Text, nullable=True)
    localisation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    stage_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    doctor_modified_ai_result: Mapped[bool] = mapped_column(Boolean, default=False)
    modification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    assessment: Mapped["TW3Assessment"] = relationship(back_populates="bones")


class AuditEvent(Base):
    __tablename__ = "audit_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("tw3_assessment.id"), nullable=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patient.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), default="local-user")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


class BoneAgeFeedback(Base):
    """Clinician correction of a bone-age estimate — the training-data intake valve.

    This is an *evidence log*, NOT a clinical result: a row here never becomes the
    patient's reported bone age. It captures what the AI said, what an expert says is
    correct, which method they used, how sure they are, who they are, and on what image
    quality — the minimum provenance needed to (a) monitor AI-vs-human accuracy over
    time and (b) later de-noise labels via multi-rater consensus and retrain.

    Deliberately separate from TW3Assessment so feedback accumulates freely without
    touching the approval-gated clinical record. ``image_hash`` links a correction to
    an image even in the stateless top-of-page estimate flow (no persisted radiograph).
    """

    __tablename__ = "bone_age_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    radiograph_id: Mapped[int | None] = mapped_column(ForeignKey("radiograph.id"), nullable=True)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("tw3_assessment.id"), nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sex: Mapped[str | None] = mapped_column(String(8), nullable=True)  # boys | girls
    chronological_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # What the AI estimated (for AI-vs-human error monitoring).
    ai_estimate_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # The clinician's corrected bone age (the label). Required.
    corrected_age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    # How the clinician decided it — keeps incompatible scales from being mixed.
    # tw3-rus | greulich-pyle | clinical | other
    method: Mapped[str] = mapped_column(String(24), default="clinical", nullable=False)
    confidence: Mapped[str] = mapped_column(String(8), default="medium", nullable=False)  # low|medium|high
    rater_id: Mapped[str | None] = mapped_column(String(120), nullable=True)  # precondition for consensus
    image_domain: Mapped[str | None] = mapped_column(String(24), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ModelRelease(Base):
    """Audit record of a gated model release (Plan 2 WI-7).

    A "learned" model is a RELEASE CANDIDATE, never a live mutation. It ships only
    when the Plan 5 release-gate engine passes (beat incumbent, no subgroup
    regression, calibrated, engineering gates) AND a human signs off. Every
    candidate — deployed, rejected, or awaiting sign-off — is recorded here so a
    model change is always auditable and reproducible.
    """

    __tablename__ = "model_release"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_kind: Mapped[str] = mapped_column(String(16), nullable=False)  # screening|localizer|stager
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    incumbent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dataset_manifest_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    beat_incumbent: Mapped[bool] = mapped_column(Boolean, default=False)
    gates_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    verdict_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    # candidate (passed gate, awaiting sign-off) | deployed | rejected
    status: Mapped[str] = mapped_column(String(16), default="candidate", nullable=False)
    signed_off_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    signed_off_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_card_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    application_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AdjudicationItem(Base):
    """A bone whose independent reads disagree, queued for a senior read (Plan 2 WI-4).

    Multi-rater staging of the SAME film is reduced to consensus (consensus.py); a
    bone with no clear majority is NOT silently averaged — it lands here for a
    qualified reviewer to resolve. The resolved label then takes precedence when the
    training dataset is exported. ``film_key`` is a radiograph id or image hash (as a
    string), so this works for both persisted and stateless-upload flows.
    """

    __tablename__ = "adjudication_item"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    film_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_system: Mapped[str] = mapped_column(String(24), nullable=False)
    bone_code: Mapped[str] = mapped_column(String(16), nullable=False)
    votes_json: Mapped[str | None] = mapped_column(Text, nullable=True)   # {stage: count}
    n_readers: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False)  # open | resolved
    resolved_stage: Mapped[str | None] = mapped_column(String(4), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


def ensure_schema_version(engine: Engine) -> None:
    """Record the current schema version once."""
    from backend.db import SessionLocal  # local import to avoid cycle at import time

    with SessionLocal() as db:
        existing = db.execute(select(SchemaVersion)).first()
        if existing is None:
            db.add(SchemaVersion(version=DB_SCHEMA_VERSION))
            db.commit()

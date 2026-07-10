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


def ensure_schema_version(engine: Engine) -> None:
    """Record the current schema version once."""
    from backend.db import SessionLocal  # local import to avoid cycle at import time

    with SessionLocal() as db:
        existing = db.execute(select(SchemaVersion)).first()
        if existing is None:
            db.add(SchemaVersion(version=DB_SCHEMA_VERSION))
            db.commit()

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
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend.config import DB_SCHEMA_VERSION
from backend.security.crypto import EncryptedString


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
    # patient_code is the clinic's own MRN. Left in clear on purpose: it is the
    # join key an operator types to find a record, and encrypting it would make
    # lookup impossible without decrypting every row. It is a pseudonym -- the
    # thing that turns it into an identity is `name`, which is encrypted below.
    patient_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Encrypted at rest (C.2). Storage grows (~2.5x, base64 + nonce + tag), hence
    # the wider column; service code still reads and writes a plain string.
    name: Mapped[str | None] = mapped_column(
        EncryptedString(600, context="patient.name"), nullable=True
    )
    sex_at_birth: Mapped[str] = mapped_column(String(8), nullable=False)  # boys | girls
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Clinical context (M2) ────────────────────────────────────────────────
    # Needed once and reused at every visit. Previously the clinician retyped
    # parental heights each time, or simply went without them.
    mother_height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    father_height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    # measured | reported. Parental heights are very often self-reported and
    # biased upward; mid-parental target height is only as good as its inputs,
    # and presenting a reported-derived target as if measured overstates it.
    parental_height_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gestational_age_weeks: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_weight_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_length_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conditions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    assessments: Mapped[list["TW3Assessment"]] = relationship(back_populates="patient")


class Encounter(Base):
    """One visit. Groups the observations and assessments made on a day (M2).

    Thin on purpose: it exists so "what happened at the March visit" is
    answerable, not to model scheduling or billing.
    """

    __tablename__ = "encounter"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    seen_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Observation(Base):
    """A single measurement of one thing, at one moment (M2).

    THE gap this closes: before it, no growth measurement was stored anywhere.
    /api/growth/point took age and value as query parameters, returned a
    z-score, and discarded both. A single height is nearly uninformative -- a
    child who has always been on the 3rd centile is probably a short child, one
    who has fallen from the 50th to the 3rd is an urgent endocrine work-up, and
    the product could not tell those apart. The trajectory is the diagnosis.

    Append-only with soft correction: a mistyped height is a typo rather than a
    superseded clinical judgement, so full revisioning (as TW3Assessment uses)
    would be over-engineered -- but silently mutating a clinical value in place
    would lose the audit trail. So a correction inserts a new row and marks the
    old one `corrected`, which mirrors `supersedes_id` without the lifecycle.
    """

    __tablename__ = "observation"
    __table_args__ = (
        Index("ix_observation_patient_type_time", "patient_id", "obs_type", "observed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False, index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Derived from observed_at - date_of_birth and CACHED for query speed. It is
    # a cache, not the truth: correcting a date of birth must recompute every
    # one of these (growth_service.recompute_ages), or every historical z-score
    # silently becomes wrong.
    age_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    obs_type: Mapped[str] = mapped_column(String(24), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(12), nullable=False)
    method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    measured_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # active | corrected | erroneous
    status: Mapped[str] = mapped_column(String(12), default="active", nullable=False)
    corrected_by_id: Mapped[int | None] = mapped_column(ForeignKey("observation.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PubertyAssessment(Base):
    """Tanner staging (M2).

    The missing variable that makes velocity, bone age and height prediction
    interpretable: the same height velocity is reassuring in a child mid-puberty
    and alarming in one who has not started.
    """

    __tablename__ = "puberty_assessment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False, index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Tanner 1-5. Breast (girls) / genital (boys) staged separately from pubic
    # hair because adrenarche and gonadarche can dissociate -- collapsing them
    # into one "Tanner stage" hides precocious adrenarche.
    breast_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genital_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubic_hair_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    testicular_volume_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    menarche_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assessed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


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


class User(Base):
    """A named human operator (security phase, C.1).

    Before this the app had no notion of who was using it: every audit row said
    "local-user", `reader_id` was free text, and any request reached any
    endpoint. That was tolerable only while the product was stateless for growth
    and single-user for bone age. A clinical record needs attributable actions.

    Passwords are stored only as scrypt hashes (see security/passwords.py).
    """

    __tablename__ = "app_user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    # admin | doctor | assistant -- see security.roles
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="assistant")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Forces a change at next login (used for admin-reset passwords).
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class UserSession(Base):
    """A logged-in browser session.

    Only the SHA-256 of the session token is stored, never the token itself --
    same reasoning as passwords: a leaked database must not yield usable
    credentials. Sessions carry both an absolute expiry and an idle timeout, so
    an unattended clinic workstation stops being logged in.
    """

    __tablename__ = "user_session"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    client_host: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ConsentRecord(Base):
    """Consent captured per patient per purpose (DPDP Act 2023, C.3).

    India's DPDP Act requires consent to be free, specific, informed and
    unconditional, and to be as easy to withdraw as to give. Consent is
    therefore recorded PER PURPOSE rather than as one blanket flag: agreeing to
    clinical care is not agreeing to have your child's radiograph used for model
    training. Withdrawal is a new row, never an edit, so the history of what was
    agreed and when survives.
    """

    __tablename__ = "consent_record"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False, index=True)
    # clinical_care | model_training | research | quality_audit
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Who consented: the patient (adult) or a parent/guardian for a minor.
    given_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    relationship: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Free-text record of exactly what the person was told.
    notice_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recorded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ErasureRequest(Base):
    """A data-principal erasure request and what was done about it (C.3).

    Erasure cannot be a silent hard DELETE: some records must be retained for
    medical-legal reasons, and a regulator may ask what was removed and what was
    kept. This records the request, the decision, and the outcome.
    """

    __tablename__ = "erasure_request"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), nullable=False, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    # pending | completed | refused
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SecurityEvent(Base):
    """Security-relevant events, including the breach log (C.3).

    Kept separate from AuditEvent: that table records clinical actions on an
    assessment, this one records authentication, authorisation failures, data
    export, erasure and suspected breaches. Mixing them makes both harder to
    review, and a breach notification has a statutory clock attached to it.
    """

    __tablename__ = "security_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # login_success | login_failure | lockout | logout | authz_denied |
    # data_export | erasure | breach_suspected | breach_notified
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(8), default="info", nullable=False)  # info|warn|critical
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patient.id"), nullable=True)
    client_host: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    application_version: Mapped[str | None] = mapped_column(String(16), nullable=True)


def ensure_schema_version(engine: Engine) -> None:
    """Record the current schema version, appending a row whenever it changes.

    Previously this inserted only when the table was empty, so DB_SCHEMA_VERSION
    was written once at first init and never again -- every subsequent schema
    change left the recorded version stale. Verified at runtime: a DB created at
    version "3" still reported "3" after the constant was bumped and init_db()
    re-run. That silently falsified config.py's contract ("versions are recorded
    ... so old results stay reproducible"), because the version stamped on the
    database no longer described the schema actually in use.

    History is APPENDED, never updated in place: reproducing an approved
    assessment requires knowing which schema was live when it was created, not
    merely which one is live now. The latest row (highest id) is the current
    version; earlier rows are the upgrade trail.
    """
    from backend.db import SessionLocal  # local import to avoid cycle at import time

    with SessionLocal() as db:
        latest = db.execute(
            select(SchemaVersion).order_by(SchemaVersion.id.desc())
        ).scalars().first()
        if latest is None or latest.version != DB_SCHEMA_VERSION:
            db.add(SchemaVersion(version=DB_SCHEMA_VERSION))
            db.commit()


def current_schema_version(engine: Engine) -> str | None:
    """The most recently recorded schema version, or None on an empty DB."""
    from backend.db import SessionLocal

    with SessionLocal() as db:
        latest = db.execute(
            select(SchemaVersion).order_by(SchemaVersion.id.desc())
        ).scalars().first()
        return None if latest is None else latest.version

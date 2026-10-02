"""Longitudinal growth record: persistence and orchestration (M2).

Follows the same split ``backend/tw3`` already uses. ``backend/growth/*`` stays
pure and receives PLAIN VALUES; this module is the only place that touches the
database, computes ages, writes audit rows and enforces lifecycle rules.

That boundary is the point. The obvious implementation of "velocity" is to pass
a Session into the growth package and let it fetch history, which would end its
testability and reuse. ``tests/growth/test_domain_purity.py`` fails if
``backend/growth`` ever imports sqlalchemy or backend.models.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.assessment_service import _audit
from backend.growth import observations, velocity as vel
from backend.models import Encounter, Observation, Patient, PubertyAssessment

DAYS_PER_YEAR = 365.2425
MONTHS_PER_YEAR = 12.0
# Two measurements closer together than this are the same clinical event for
# velocity purposes; pairing them produces noise, not a growth rate.
MIN_VELOCITY_GAP_DAYS = 30


class GrowthRecordError(ValueError):
    """Invalid observation or lifecycle operation (maps to 4xx)."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


# One day of slack for time zones: the exam date typed in India can be "tomorrow"
# in UTC for a few hours.
_FUTURE_TOLERANCE = timedelta(days=1)


def _not_future(when: datetime, what: str) -> datetime:
    """Refuse a clinical date in the future. A mistyped year (2062 for 2026)
    otherwise stores silently and corrupts every velocity computed across it."""
    when = _naive(when)
    if when > _utcnow() + _FUTURE_TOLERANCE:
        raise GrowthRecordError(f"{what} {when.date().isoformat()} is in the future")
    return when


def age_months_at(patient: Patient, when: datetime) -> Optional[float]:
    """Decimal age in months, or None when the date of birth is unknown."""
    if patient.date_of_birth is None:
        return None
    delta = _naive(when) - _naive(patient.date_of_birth)
    return round(delta.days / DAYS_PER_YEAR * MONTHS_PER_YEAR, 4)


def _require_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise GrowthRecordError(f"patient {patient_id} not found")
    return patient


# ── recording ───────────────────────────────────────────────────────────────

def record_observation(db: Session, *, patient_id: int, obs_type: str, value: float,
                       observed_at: Optional[datetime] = None,
                       unit: Optional[str] = None, method: Optional[str] = None,
                       measured_by: Optional[str] = None,
                       encounter_id: Optional[int] = None,
                       note: Optional[str] = None,
                       allow_implausible_change: bool = False,
                       actor: str = "local-user") -> tuple[Observation, list[str]]:
    """Store one measurement. Returns (row, warnings).

    Warnings are advisory (a same-day repeat is legitimate). An implausible
    *change* is different: it blocks unless explicitly overridden, because a
    mistyped height silently destroys every velocity computed from it, and the
    moment of entry is the only cheap opportunity to catch it.
    """
    patient = _require_patient(db, patient_id)
    obs = observations.validate(obs_type, value, unit)
    when = _not_future(observed_at or _utcnow(), "measurement date")

    if patient.date_of_birth is not None and when < _naive(patient.date_of_birth):
        raise GrowthRecordError("observation predates the patient's date of birth")

    warnings: list[str] = []
    history = _active_rows(db, patient_id, obs_type)

    same_day = [r for r in history if r.observed_at.date() == when.date()]
    if same_day:
        # Not blocked: a repeat measurement on the same visit is good practice.
        warnings.append(f"duplicate_same_day: {len(same_day)} existing {obs_type} on this date")

    prior = [r for r in history if r.observed_at <= when]
    if prior and obs.monotonic:
        last = max(prior, key=lambda r: r.observed_at)
        drop = last.value - value
        if drop > vel.PLAUSIBLE_HEIGHT_LOSS_CM:
            message = (
                f"implausible_decrease: {obs.label} fell {drop:.1f} {obs.unit} since "
                f"{last.observed_at.date().isoformat()} ({last.value} -> {value}). "
                "This is the most common data-entry error in a growth clinic and it "
                "corrupts every velocity derived from it."
            )
            if not allow_implausible_change:
                raise GrowthRecordError(message + " Re-check, or resubmit with "
                                                  "allow_implausible_change=true.")
            warnings.append(message)

    row = Observation(
        patient_id=patient_id, encounter_id=encounter_id, observed_at=when,
        age_months=age_months_at(patient, when), obs_type=obs.key, value=float(value),
        unit=obs.unit, method=method, measured_by=measured_by or actor, note=note,
    )
    db.add(row)
    db.flush()
    _audit(db, assessment_id=None, patient_id=patient_id, event_type="observation_recorded",
           actor=actor, new={"id": row.id, "type": obs.key, "value": value,
                             "observed_at": when.isoformat(), "warnings": warnings})
    return row, warnings


def correct_observation(db: Session, observation_id: int, *, new_value: float,
                        reason: str, actor: str = "local-user") -> Observation:
    """Append a corrected row and mark the original `corrected`.

    Never edits in place: the original value is what earlier reports were built
    from, and losing it makes an old printout unexplainable.
    """
    original = db.get(Observation, observation_id)
    if original is None:
        raise GrowthRecordError(f"observation {observation_id} not found")
    if original.status != "active":
        raise GrowthRecordError(f"observation is already {original.status}")
    if not reason:
        raise GrowthRecordError("a reason is required to correct a measurement")

    obs = observations.validate(original.obs_type, new_value)
    patient = _require_patient(db, original.patient_id)

    replacement = Observation(
        patient_id=original.patient_id, encounter_id=original.encounter_id,
        observed_at=original.observed_at,
        age_months=age_months_at(patient, original.observed_at),
        obs_type=original.obs_type, value=float(new_value), unit=obs.unit,
        method=original.method, measured_by=actor,
        note=f"correction of #{original.id}: {reason}",
    )
    db.add(replacement)
    db.flush()

    original.status = "corrected"
    original.corrected_by_id = replacement.id
    _audit(db, assessment_id=None, patient_id=original.patient_id,
           event_type="observation_corrected", actor=actor,
           previous={"id": original.id, "value": original.value},
           new={"id": replacement.id, "value": new_value}, reason=reason)
    db.flush()
    return replacement


def recompute_ages(db: Session, patient_id: int, *, actor: str = "local-user") -> int:
    """Recompute cached ages after a date-of-birth correction.

    ``Observation.age_months`` is a cache. Correcting a date of birth without
    this leaves every stored age -- and therefore every z-score and velocity
    derived from it -- silently wrong, with nothing to indicate it.
    """
    patient = _require_patient(db, patient_id)
    rows = db.execute(
        select(Observation).where(Observation.patient_id == patient_id)
    ).scalars().all()
    for row in rows:
        row.age_months = age_months_at(patient, row.observed_at)
    _audit(db, assessment_id=None, patient_id=patient_id, event_type="ages_recomputed",
           actor=actor, new={"observations": len(rows),
                             "date_of_birth": patient.date_of_birth.isoformat()
                             if patient.date_of_birth else None})
    db.flush()
    return len(rows)


def set_date_of_birth(db: Session, patient_id: int, date_of_birth: datetime, *,
                      actor: str = "local-user") -> int:
    """Correct a date of birth and recompute every dependent age in one step."""
    patient = _require_patient(db, patient_id)
    new_dob = _not_future(date_of_birth, "date of birth")
    # A birth date after a recorded measurement gives that measurement a negative
    # age, and every centile computed from it is meaningless.
    earliest = db.execute(
        select(Observation.observed_at).where(Observation.patient_id == patient_id)
        .where(Observation.status == "active").order_by(Observation.observed_at).limit(1)
    ).scalar_one_or_none()
    if earliest is not None and new_dob > earliest:
        raise GrowthRecordError(
            f"date of birth {new_dob.date().isoformat()} is after a recorded "
            f"measurement ({earliest.date().isoformat()})")
    previous = patient.date_of_birth
    patient.date_of_birth = new_dob
    _audit(db, assessment_id=None, patient_id=patient_id, event_type="dob_corrected",
           actor=actor,
           previous={"date_of_birth": previous.isoformat() if previous else None},
           new={"date_of_birth": patient.date_of_birth.isoformat()})
    return recompute_ages(db, patient_id, actor=actor)


# ── reading ─────────────────────────────────────────────────────────────────

def _active_rows(db: Session, patient_id: int, obs_type: str) -> list[Observation]:
    return list(db.execute(
        select(Observation)
        .where(Observation.patient_id == patient_id)
        .where(Observation.obs_type == obs_type)
        .where(Observation.status == "active")
        .order_by(Observation.observed_at)
    ).scalars().all())


def series_for(db: Session, patient_id: int, obs_type: str) -> list[tuple[float, float]]:
    """Ascending ``(age_years, value)`` pairs.

    THE BOUNDARY: plain tuples, never ORM objects. Everything in
    ``backend/growth`` consumes this shape, which is what keeps that package
    free of persistence. Rows without an age (no date of birth) are omitted --
    an age-less point cannot be plotted or used for velocity.
    """
    return [
        (round(r.age_months / MONTHS_PER_YEAR, 4), r.value)
        for r in _active_rows(db, patient_id, obs_type)
        if r.age_months is not None
    ]


def velocities_for(db: Session, patient_id: int, obs_type: str) -> list[dict[str, Any]]:
    """Velocity between consecutive measurements, with too-close pairs dropped."""
    obs = observations.get(obs_type)
    rows = [r for r in _active_rows(db, patient_id, obs_type) if r.age_months is not None]

    usable: list[Observation] = []
    for row in rows:
        if usable and (row.observed_at - usable[-1].observed_at).days < MIN_VELOCITY_GAP_DAYS:
            continue  # same clinical event, not a growth interval
        usable.append(row)

    points = [(r.age_months / MONTHS_PER_YEAR, r.value) for r in usable]
    patient = _require_patient(db, patient_id)
    # Score against the published velocity reference when one is installed
    # (M1.3); it withholds with a reason otherwise.
    results = vel.series_velocities(
        points, unit=obs.unit, monotonic=obs.monotonic,
        sex=patient.sex_at_birth, score=(obs_type == "height"))
    return [
        {"available": r.available, "velocity_per_year": r.velocity_per_year,
         "unit": r.unit, "interval_years": r.interval_years,
         "from_age_years": round(r.from_age_years, 3),
         "to_age_years": round(r.to_age_years, 3),
         "status": r.status, "flags": list(r.flags),
         "velocity_sds": r.velocity_sds, "sds_status": r.sds_status}
        for r in results
    ]


def timeline(db: Session, patient_id: int) -> dict[str, Any]:
    """Everything recorded for one patient, grouped for a single screen."""
    patient = _require_patient(db, patient_id)
    by_type: dict[str, list[dict[str, Any]]] = {}
    for key in observations.OBSERVATION_KEYS:
        rows = _active_rows(db, patient_id, key)
        if rows:
            by_type[key] = [
                {"id": r.id, "observed_at": r.observed_at.isoformat(),
                 "age_years": round(r.age_months / MONTHS_PER_YEAR, 3)
                 if r.age_months is not None else None,
                 "value": r.value, "unit": r.unit, "method": r.method}
                for r in rows
            ]

    puberty = db.execute(
        select(PubertyAssessment).where(PubertyAssessment.patient_id == patient_id)
        .order_by(PubertyAssessment.assessed_at)
    ).scalars().all()

    return {
        "patient": {
            "id": patient.id, "patient_code": patient.patient_code,
            "name": patient.name, "sex_at_birth": patient.sex_at_birth,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "mother_height_cm": patient.mother_height_cm,
            "father_height_cm": patient.father_height_cm,
            "parental_height_source": patient.parental_height_source,
            "gestational_age_weeks": patient.gestational_age_weeks,
            "birth_weight_g": patient.birth_weight_g,
            "conditions": json.loads(patient.conditions_json or "[]"),
            "medications": json.loads(patient.medications_json or "[]"),
        },
        "observations": by_type,
        "velocities": {
            key: velocities_for(db, patient_id, key)
            for key in by_type if observations.get(key).monotonic
        },
        "puberty": [
            {"assessed_at": p.assessed_at.isoformat(), "breast_stage": p.breast_stage,
             "genital_stage": p.genital_stage, "pubic_hair_stage": p.pubic_hair_stage,
             "testicular_volume_ml": p.testicular_volume_ml,
             "menarche_date": p.menarche_date.isoformat() if p.menarche_date else None}
            for p in puberty
        ],
    }


# ── encounters and puberty ──────────────────────────────────────────────────

def create_encounter(db: Session, *, patient_id: int, occurred_at: Optional[datetime] = None,
                     reason: Optional[str] = None, note: Optional[str] = None,
                     seen_by_user_id: Optional[int] = None) -> Encounter:
    _require_patient(db, patient_id)
    row = Encounter(patient_id=patient_id, occurred_at=_naive(occurred_at or _utcnow()),
                    reason=reason, note=note, seen_by_user_id=seen_by_user_id)
    db.add(row)
    db.flush()
    return row


def record_puberty(db: Session, *, patient_id: int, assessed_at: Optional[datetime] = None,
                   breast_stage: Optional[int] = None, genital_stage: Optional[int] = None,
                   pubic_hair_stage: Optional[int] = None,
                   testicular_volume_ml: Optional[float] = None,
                   menarche_date: Optional[datetime] = None,
                   encounter_id: Optional[int] = None,
                   actor: str = "local-user") -> PubertyAssessment:
    _require_patient(db, patient_id)
    for name, stage in (("breast_stage", breast_stage), ("genital_stage", genital_stage),
                        ("pubic_hair_stage", pubic_hair_stage)):
        if stage is not None and not (1 <= stage <= 5):
            raise GrowthRecordError(f"{name} must be Tanner 1-5, got {stage}")
    if testicular_volume_ml is not None and not (0 < testicular_volume_ml <= 40):
        raise GrowthRecordError("testicular_volume_ml must be between 0 and 40")
    # Sex-specific staging. A menarche date on a boy or a testicular volume on a
    # girl is an entry error (usually the wrong record open), and the puberty
    # rules would read it as a clinical fact.
    patient = _require_patient(db, patient_id)
    if patient.sex_at_birth == "boys" and (breast_stage is not None or menarche_date is not None):
        raise GrowthRecordError("breast stage and menarche are recorded for girls; "
                                "this record is male")
    if patient.sex_at_birth == "girls" and (genital_stage is not None
                                           or testicular_volume_ml is not None):
        raise GrowthRecordError("genital stage and testicular volume are recorded for "
                                "boys; this record is female")

    assessed_at = _not_future(assessed_at or _utcnow(), "assessment date")
    if menarche_date is not None:
        _not_future(menarche_date, "menarche date")
    row = PubertyAssessment(
        patient_id=patient_id, encounter_id=encounter_id,
        assessed_at=assessed_at, breast_stage=breast_stage,
        genital_stage=genital_stage, pubic_hair_stage=pubic_hair_stage,
        testicular_volume_ml=testicular_volume_ml,
        menarche_date=_naive(menarche_date) if menarche_date else None,
        assessed_by=actor,
    )
    db.add(row)
    db.flush()
    _audit(db, assessment_id=None, patient_id=patient_id, event_type="puberty_recorded",
           actor=actor, new={"id": row.id, "assessed_at": row.assessed_at.isoformat()})
    return row


# ── patient registry (step 3) ───────────────────────────────────────────────
#
# Until step 3 a patient could only come into existence as a side effect of
# saving a bone-age assessment, so the longitudinal record, the rules engine and
# triage -- all keyed by patient -- were unreachable from the workspace.

PARENT_HEIGHT_RANGE_CM = (100.0, 230.0)
GESTATIONAL_AGE_RANGE_WEEKS = (22.0, 44.0)
BIRTH_WEIGHT_RANGE_G = (300.0, 6500.0)
PARENTAL_SOURCES = ("measured", "reported")
SEXES = ("boys", "girls")


def patient_summary(patient: Patient) -> dict[str, Any]:
    return {
        "id": patient.id, "patient_code": patient.patient_code, "name": patient.name,
        "sex_at_birth": patient.sex_at_birth,
        "date_of_birth": patient.date_of_birth.date().isoformat() if patient.date_of_birth else None,
        "mother_height_cm": patient.mother_height_cm,
        "father_height_cm": patient.father_height_cm,
        "parental_height_source": patient.parental_height_source,
        "gestational_age_weeks": patient.gestational_age_weeks,
        "birth_weight_g": patient.birth_weight_g,
    }


def find_patient_by_code(db: Session, patient_code: str) -> Optional[Patient]:
    code = (patient_code or "").strip()
    if not code:
        return None
    return db.execute(select(Patient).where(Patient.patient_code == code)).scalar_one_or_none()


def _check_range(name: str, value: Optional[float], bounds: tuple[float, float]) -> None:
    if value is not None and not (bounds[0] <= value <= bounds[1]):
        raise GrowthRecordError(f"{name} must be between {bounds[0]:g} and {bounds[1]:g}")


def _validate_context(fields: dict[str, Any]) -> None:
    _check_range("mother_height_cm", fields.get("mother_height_cm"), PARENT_HEIGHT_RANGE_CM)
    _check_range("father_height_cm", fields.get("father_height_cm"), PARENT_HEIGHT_RANGE_CM)
    _check_range("gestational_age_weeks", fields.get("gestational_age_weeks"),
                 GESTATIONAL_AGE_RANGE_WEEKS)
    _check_range("birth_weight_g", fields.get("birth_weight_g"), BIRTH_WEIGHT_RANGE_G)
    src = fields.get("parental_height_source")
    if src is not None and src not in PARENTAL_SOURCES:
        raise GrowthRecordError(f"parental_height_source must be one of {PARENTAL_SOURCES}")


def create_patient(db: Session, *, patient_code: str, sex: str,
                   date_of_birth: Optional[datetime] = None, name: Optional[str] = None,
                   actor: str = "local-user", **context: Any) -> Patient:
    code = (patient_code or "").strip()
    if not code or len(code) > 64:
        raise GrowthRecordError("patient_code (MRN) is required, at most 64 characters")
    if sex not in SEXES:
        raise GrowthRecordError(f"sex must be one of {SEXES}")
    if find_patient_by_code(db, code) is not None:
        raise GrowthRecordError(f"a patient with code {code!r} already exists")
    if date_of_birth is not None:
        _not_future(date_of_birth, "date of birth")
    _validate_context(context)
    patient = Patient(patient_code=code, sex_at_birth=sex, name=(name or None),
                      date_of_birth=_naive(date_of_birth) if date_of_birth else None,
                      **{k: v for k, v in context.items() if v is not None})
    db.add(patient)
    db.flush()
    _audit(db, assessment_id=None, patient_id=patient.id, event_type="patient_created",
           actor=actor, new={"patient_code": code, "sex": sex})
    return patient


CONTEXT_FIELDS = ("mother_height_cm", "father_height_cm", "parental_height_source",
                  "gestational_age_weeks", "birth_weight_g")


def update_patient_context(db: Session, patient_id: int, *, actor: str = "local-user",
                           **fields: Any) -> Patient:
    """Set clinical context. Sex and date of birth are NOT editable here: sex
    drives every z-score, and a date of birth change must recompute stored ages
    (see set_date_of_birth)."""
    patient = _require_patient(db, patient_id)
    unknown = set(fields) - set(CONTEXT_FIELDS)
    if unknown:
        raise GrowthRecordError(f"not editable here: {sorted(unknown)}")
    _validate_context(fields)
    previous = {k: getattr(patient, k) for k in fields}
    for k, v in fields.items():
        setattr(patient, k, v)
    db.flush()
    _audit(db, assessment_id=None, patient_id=patient_id, event_type="patient_context_updated",
           actor=actor, previous=previous, new=fields)
    return patient


# Measurements a clinician takes at one visit. BMI is NOT accepted from the
# client: it is derived here from the same visit's height and weight, so it can
# never disagree with them.
VISIT_FIELDS = ("height", "weight", "head_circumference", "sitting_height",
                "arm_span", "systolic_bp", "diastolic_bp")


def record_visit_measurements(db: Session, *, patient_id: int, observed_at: datetime,
                              values: dict[str, Optional[float]],
                              allow_implausible_change: bool = False,
                              actor: str = "local-user") -> dict[str, Any]:
    """Record one visit's measurements ALL-OR-NOTHING.

    Any invalid value raises and, because the request session rolls back on
    error, nothing from the visit is stored -- a height saved without its weight
    would leave a BMI gap and a half-recorded visit.
    """
    patient = _require_patient(db, patient_id)
    if patient.date_of_birth is None:
        raise GrowthRecordError(
            "the record has no date of birth: ages (and so every centile and "
            "velocity) cannot be computed. Set it first.")
    entered = {k: v for k, v in values.items() if v is not None}
    unknown = set(entered) - set(VISIT_FIELDS)
    if unknown:
        raise GrowthRecordError(f"unknown measurement(s): {sorted(unknown)}")
    if not entered:
        raise GrowthRecordError("no measurement entered")
    if ("systolic_bp" in entered) != ("diastolic_bp" in entered):
        raise GrowthRecordError("record systolic and diastolic BP together")
    if "systolic_bp" in entered and entered["diastolic_bp"] >= entered["systolic_bp"]:
        raise GrowthRecordError("diastolic BP must be lower than systolic")

    encounter = create_encounter(db, patient_id=patient_id, occurred_at=observed_at,
                                 reason="measurements")
    saved, warnings = [], []
    for key in VISIT_FIELDS:
        if key not in entered:
            continue
        row, w = record_observation(
            db, patient_id=patient_id, obs_type=key, value=entered[key],
            observed_at=observed_at, encounter_id=encounter.id,
            allow_implausible_change=allow_implausible_change, actor=actor)
        saved.append({"obs_type": key, "value": row.value, "unit": row.unit})
        warnings += w
    if "height" in entered and "weight" in entered:
        bmi = entered["weight"] / (entered["height"] / 100.0) ** 2
        row, w = record_observation(
            db, patient_id=patient_id, obs_type="bmi", value=round(bmi, 2),
            observed_at=observed_at, encounter_id=encounter.id, method="derived",
            note="derived from same-visit height and weight", actor=actor)
        saved.append({"obs_type": "bmi", "value": row.value, "unit": row.unit, "derived": True})
        warnings += w
    return {"encounter_id": encounter.id, "saved": saved, "warnings": warnings}

"""Inputs and outputs of the reasoning engine (M5).

Pure: no database, no HTTP, no I/O. ``clinical_service`` builds a
:class:`PatientSnapshot` from the ORM and hands it in; everything downstream
works on this frozen value. Same boundary ``backend/growth`` and ``backend/tw3``
keep, and for the same reason -- a rules engine that needs a database to test is
a rules engine nobody re-tests.

The important design decision is that **explainability is a data structure, not
a string**. Every finding carries the actual numbers it fired on
(``inputs_used``) and where its threshold comes from (``source``). A rule that
cannot say which values triggered it cannot be clinically defended, cannot be
unit-tested against a boundary, and cannot be shown to a sceptical clinician --
which is the only kind worth designing for.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Severity, in the order the UI should sort them.
INFO = "info"
ATTENTION = "attention"
URGENT = "urgent"
INSUFFICIENT_DATA = "insufficient_data"

SEVERITY_ORDER = {URGENT: 0, ATTENTION: 1, INSUFFICIENT_DATA: 2, INFO: 3}


@dataclass(frozen=True)
class Measurement:
    """One value with the age it was taken at."""
    age_years: float
    value: float
    sds: Optional[float] = None


@dataclass(frozen=True)
class PatientSnapshot:
    """Everything the engine is allowed to reason from.

    Fields are Optional by default so that "not recorded" is representable and
    distinguishable from a value. That distinction is the whole safety
    argument: see ``Finding`` and the insufficient-data handling in rules.py.
    """

    sex: str                                  # "boys" | "girls"
    age_years: Optional[float] = None

    height: Optional[Measurement] = None
    weight: Optional[Measurement] = None
    bmi: Optional[Measurement] = None

    # Ascending history, used for trajectory rules.
    height_history: tuple[Measurement, ...] = ()
    # cm/year for each consecutive usable interval, most recent last.
    height_velocities: tuple[tuple[float, float, float], ...] = ()  # (from_age, to_age, cm_per_year)

    mother_height_cm: Optional[float] = None
    father_height_cm: Optional[float] = None
    parental_height_source: Optional[str] = None   # "measured" | "reported"
    # The mid-parental target expressed as an ADULT height SDS, supplied by the
    # service (which owns the growth reference). Comparing a child's height SDS
    # with this is the only valid way to ask "is this child on track for their
    # genetic potential" -- comparing centimetres against an adult target flags
    # every child under about fifteen, which is a false-positive generator.
    target_height_sds: Optional[float] = None

    gestational_age_weeks: Optional[float] = None
    birth_weight_g: Optional[float] = None

    # Tanner staging at the most recent assessment.
    breast_stage: Optional[int] = None
    genital_stage: Optional[int] = None
    pubic_hair_stage: Optional[int] = None
    testicular_volume_ml: Optional[float] = None
    menarche_reached: Optional[bool] = None

    bone_age_years: Optional[float] = None
    bone_age_method: Optional[str] = None

    arm_span_cm: Optional[float] = None
    sitting_height_cm: Optional[float] = None

    def has(self, field_name: str) -> bool:
        """Whether a required input is actually present.

        A rule declares what it needs and the engine checks it here, so
        "we didn't look" can never be rendered as "we looked and it was fine".
        """
        value = getattr(self, field_name, None)
        if value is None:
            return False
        if isinstance(value, (tuple, list)):
            return len(value) > 0
        if isinstance(value, Measurement):
            return value.value is not None
        return True


@dataclass(frozen=True)
class Finding:
    """One thing the engine noticed, and why."""

    rule_id: str
    severity: str
    title: str
    rationale: str
    # The actual numbers this fired on. Not decoration: it is what makes the
    # finding auditable, testable at a boundary, and defensible to a clinician.
    inputs_used: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    confidence: str = "moderate"          # low | moderate | high
    # Rules this one makes redundant. Without suppression a single problem
    # produces three alarms, and alarm fatigue is the documented failure mode of
    # clinical decision support -- it makes the panel worse than nothing.
    suppresses: tuple[str, ...] = ()
    # Specialties this finding points toward, if any.
    suggests_specialty: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "rationale": self.rationale,
            "inputs_used": self.inputs_used,
            "source": self.source,
            "confidence": self.confidence,
            "suggests_specialty": list(self.suggests_specialty),
        }


def insufficient(rule_id: str, missing: list[str], why: str) -> Finding:
    """A rule that could not run, said out loud.

    Silence is the dangerous output: an absent flag is indistinguishable from
    "checked and fine". A clinician reading a clean panel must be able to see
    that a check did not run because the input was never recorded.
    """
    return Finding(
        rule_id=rule_id,
        severity=INSUFFICIENT_DATA,
        title=f"Not assessed: {why}",
        rationale=("This check did not run because the following was not "
                   f"recorded: {', '.join(missing)}. Absence of a flag here does "
                   "not mean the finding was excluded."),
        inputs_used={"missing": missing},
        confidence="high",
    )

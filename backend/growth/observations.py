"""What can be observed, and what counts as a plausible value (M2).

Pure: no database, no HTTP. The service layer maps ORM rows onto these types
and back, which is what keeps ``backend/growth`` reusable and trivially
testable (the same boundary ``backend/tw3`` keeps against
``assessment_service``).

Deliberately broader than the chart-measure registry (``measures.py``): a clinic
records things that are not plotted on a growth chart -- blood pressure, arm
span -- and forcing those through a registry whose job is "which curves do we
draw" would conflate two different questions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final



@dataclass(frozen=True)
class ObservationType:
    key: str
    label: str
    unit: str
    # Plausibility bounds for a HUMAN CHILD, not reference limits. These reject
    # data entry errors (a height typed in metres, a weight in grams), which are
    # the most common corruption in a growth clinic. Anything inside these but
    # clinically extreme is a finding, not an error, and must still be stored.
    min_value: float
    max_value: float
    charted: bool  # has a growth-chart reference in measures.py
    monotonic: bool  # should never decrease with age in a healthy child


_ALL: Final[tuple[ObservationType, ...]] = (
    ObservationType("height", "Height", "cm", 30.0, 230.0, True, True),
    ObservationType("weight", "Weight", "kg", 0.3, 300.0, True, True),
    ObservationType("bmi", "BMI", "kg/m2", 5.0, 100.0, True, False),
    # Not yet charted -- B11/B14 add the references. Storing them now means the
    # history exists on the day those charts land, instead of starting empty.
    ObservationType("head_circumference", "Head circumference", "cm", 20.0, 70.0, False, True),
    ObservationType("sitting_height", "Sitting height", "cm", 20.0, 120.0, False, True),
    ObservationType("arm_span", "Arm span", "cm", 25.0, 240.0, False, True),
    ObservationType("systolic_bp", "Systolic BP", "mmHg", 40.0, 250.0, False, False),
    ObservationType("diastolic_bp", "Diastolic BP", "mmHg", 20.0, 180.0, False, False),
)

OBSERVATION_TYPES: Final[dict[str, ObservationType]] = {o.key: o for o in _ALL}
OBSERVATION_KEYS: Final[tuple[str, ...]] = tuple(o.key for o in _ALL)


class ObservationError(ValueError):
    """Rejected observation (maps to 422 at the API layer)."""


def get(key: str) -> ObservationType:
    try:
        return OBSERVATION_TYPES[key]
    except KeyError:
        raise ObservationError(
            f"unknown observation type {key!r}; known: {', '.join(OBSERVATION_KEYS)}"
        ) from None


def validate(key: str, value: float, unit: str | None = None) -> ObservationType:
    """Raise ObservationError unless the value is a plausible human measurement."""
    obs = get(key)
    if value is None or not isinstance(value, (int, float)) or value != value:
        raise ObservationError(f"{key}: value must be a number")
    if not (obs.min_value <= value <= obs.max_value):
        raise ObservationError(
            f"{key}: {value} {obs.unit} is outside the plausible range "
            f"{obs.min_value}-{obs.max_value} {obs.unit}. If this is a real "
            "measurement, record it with a note; more likely it is a unit error."
        )
    if unit is not None and unit != obs.unit:
        raise ObservationError(f"{key}: unit must be {obs.unit!r}, got {unit!r}")
    return obs

"""Growth velocity between two measurements (M2).

Pure: takes plain ``(age_years, value)`` pairs, never an ORM object or a
database session. That boundary is the reason ``backend/growth`` stays testable
without a database, and it is the one thing M2 most easily destroys -- the
obvious way to compute velocity is to hand this module a Session and let it
fetch the history. ``tests/growth/test_domain_purity.py`` fails if that happens.

Why the interval rules are not arbitrary:

* Under 6 months, measurement error dominates. Stadiometer technique varies by
  roughly 0.3 cm between operators; over 3 months a 0.5 cm error becomes 2 cm/yr
  of entirely spurious velocity -- larger than many real abnormalities. So a
  short interval yields no velocity at all rather than a confident wrong one.
* Over 2 years, a growth spurt inside the window is averaged away, so the
  number is real but hides what a clinician is looking for. Reported with a
  flag rather than withheld.

**Velocity SDS is deliberately not computed here.** It needs a published
velocity reference (Khadilkar et al., Indian Pediatr 2019 -- item B6/M1.3),
which this project does not yet hold. Inventing one, or reusing a distance-chart
SD, would produce a plausible number with no basis. The reference slots in
without touching this module.
"""
from __future__ import annotations

from dataclasses import dataclass

MIN_INTERVAL_YEARS = 0.5
LONG_INTERVAL_YEARS = 2.0
# Diurnal variation and measurement technique make a small apparent height loss
# unremarkable; a large one is a data-entry error or real pathology (vertebral
# collapse, severe scoliosis progression) and either way needs a human.
PLAUSIBLE_HEIGHT_LOSS_CM = 1.0


@dataclass(frozen=True)
class VelocityResult:
    available: bool
    velocity_per_year: float | None
    interval_years: float
    from_age_years: float
    to_age_years: float
    unit: str
    status: str
    flags: tuple[str, ...] = ()
    # Always None until a velocity reference is bundled -- see module docstring.
    velocity_sds: float | None = None
    sds_status: str = "no_velocity_reference_available"


def velocity(a1: float, v1: float, a2: float, v2: float, *,
             unit: str = "cm", monotonic: bool = True) -> VelocityResult:
    """Velocity between two measurements, or an explanation of why not."""
    if a2 < a1:
        a1, a2, v1, v2 = a2, a1, v2, v1

    interval = a2 - a1
    flags: list[str] = []

    if interval <= 0:
        return VelocityResult(False, None, interval, a1, a2, f"{unit}/yr",
                              "two measurements at the same age; velocity is undefined")

    if interval < MIN_INTERVAL_YEARS:
        return VelocityResult(
            False, None, interval, a1, a2, f"{unit}/yr",
            f"interval {interval * 12:.1f} months is under the {MIN_INTERVAL_YEARS * 12:.0f}-month "
            "minimum: measurement error would dominate the result",
        )

    rate = (v2 - v1) / interval

    if interval > LONG_INTERVAL_YEARS:
        flags.append("long_interval_may_average_out_a_spurt")

    if monotonic and v2 < v1:
        loss = v1 - v2
        flags.append(
            "implausible_decrease" if loss > PLAUSIBLE_HEIGHT_LOSS_CM else "small_decrease"
        )

    return VelocityResult(True, round(rate, 3), round(interval, 4), a1, a2,
                          f"{unit}/yr", "ok", tuple(flags))


def series_velocities(points: list[tuple[float, float]], *, unit: str = "cm",
                      monotonic: bool = True) -> list[VelocityResult]:
    """Velocity for each consecutive pair in an ascending (age, value) series.

    Consecutive pairs only -- not every combination. A clinician reads the
    trajectory step by step, and pairing a 5-year-old measurement with today's
    would produce an average that describes no period of the child's life.
    """
    ordered = sorted(points)
    return [
        velocity(a1, v1, a2, v2, unit=unit, monotonic=monotonic)
        for (a1, v1), (a2, v2) in zip(ordered, ordered[1:])
    ]

"""Canonical registry of growth measures — single source of truth (M0.3).

Before this module the measure set was declared **seven times across six files**
(``api_growth._VALID_MEASURES``, ``api_growth._UNITS``,
``blend._REQUIRE_MONOTONIC``, ``qa_report._MEASURE_FILE_PART``,
``qa_report._MEASURE_CENTILES``, ``validation.MEASURES``,
``who_reference._MEASURE_MAP`` and both ``_Seam.measures`` sets). Adding a
measure meant a correct edit in every one of them, with no compiler and no
failing test if one was missed — a partially-registered measure would simply
behave wrongly in whichever code path was forgotten (e.g. render a chart but
never be validated, or be validated but score against the wrong WHO seam).

This mirrors what ``tw3/constants.py`` already does correctly for bones and
stages: every module imports the canonical definition rather than re-declaring
it. ``tests/growth/test_measure_registry.py`` fails if any consumer drifts.

Deliberately dependency-free: no rcpchgrowth import, no I/O. The rcpchgrowth
binding is expressed as a plain string (``who_measurement_method``) and is
asserted against the real ``rcpchgrowth`` constants by the registry test, so the
coupling is checked without being hard-wired — which keeps the planned removal
of that dependency (M1.4) a local change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Measure:
    """One growth measure and every per-measure fact the engine needs."""

    key: str
    """Canonical identifier used in APIs, filenames and internal dicts."""

    label: str
    """Human-readable name for UI and reports."""

    unit: str
    """Clinical unit as displayed."""

    monotonic: bool
    """True when the value must never decrease with age, so a decrease is always
    a construction artefact (height, weight). False for BMI, which has a real
    'adiposity rebound' trough in early-mid childhood — forcing monotonicity
    there would itself be the distortion. Drives ``blend._REQUIRE_MONOTONIC``
    and ``validation.MONOTONIC_MEASURES``.

    NB: this is a property of the *measure*, not of a WHO seam. The seams in
    ``who_reference`` carry their own ``monotonic`` flag (the 5y handoff uses a
    bounded bridge for every measure, height included) and must NOT be derived
    from this field."""

    file_part: str | None
    """Filename fragment of the IAP 2015 CSV, e.g. 'height_cm' in
    ``boy_height_cm_IAP_5_18.csv``. None when the measure has no IAP table."""

    published_centiles: tuple[int, ...]
    """Centile columns actually published by IAP 2015. Height/weight carry the
    full 3–97 spread; BMI's published table only carries the lower half (plus
    two IOTF adult-equivalent cutoff columns that are not fixed-z percentiles
    and are excluded here)."""

    who_measurement_method: str | None
    """``rcpchgrowth`` measurement_method, or None when WHO has no reference for
    this measure (e.g. sitting height, arm span). Every WHO code path must
    handle None explicitly rather than falling back to height."""

    who_seam_2y: bool
    """Affected by WHO's recumbent-length vs standing-height convention change
    at 2.0y. Weight is not (it does not depend on the length convention)."""

    who_seam_5y: bool
    """Affected by the WHO-2006-child / WHO-2007-child table handoff (~5.08y)."""

    @property
    def who_backed(self) -> bool:
        return self.who_measurement_method is not None

    @property
    def has_iap_table(self) -> bool:
        return self.file_part is not None


_ALL: Final[tuple[Measure, ...]] = (
    Measure(
        key="height",
        label="Height",
        unit="cm",
        monotonic=True,
        file_part="height_cm",
        published_centiles=(3, 10, 25, 50, 75, 90, 97),
        who_measurement_method="height",
        who_seam_2y=True,
        who_seam_5y=True,
    ),
    Measure(
        key="weight",
        label="Weight",
        unit="kg",
        monotonic=True,
        file_part="weight_kg",
        published_centiles=(3, 10, 25, 50, 75, 90, 97),
        who_measurement_method="weight",
        who_seam_2y=False,  # weight does not depend on the length/height convention
        who_seam_5y=True,
    ),
    Measure(
        key="bmi",
        label="BMI",
        unit="kg/m2",
        monotonic=False,  # real adiposity-rebound trough — see blend.py
        file_part="bmi",
        published_centiles=(3, 5, 10, 25, 50),
        who_measurement_method="bmi",
        who_seam_2y=True,  # derived from height, so it inherits the 2y seam
        who_seam_5y=True,
    ),
)

MEASURES: Final[dict[str, Measure]] = {m.key: m for m in _ALL}
MEASURE_KEYS: Final[tuple[str, ...]] = tuple(m.key for m in _ALL)

MONOTONIC_MEASURE_KEYS: Final[tuple[str, ...]] = tuple(m.key for m in _ALL if m.monotonic)
WHO_BACKED_KEYS: Final[tuple[str, ...]] = tuple(m.key for m in _ALL if m.who_backed)
IAP_TABLE_KEYS: Final[tuple[str, ...]] = tuple(m.key for m in _ALL if m.has_iap_table)

SEAM_2Y_KEYS: Final[frozenset[str]] = frozenset(m.key for m in _ALL if m.who_seam_2y)
SEAM_5Y_KEYS: Final[frozenset[str]] = frozenset(m.key for m in _ALL if m.who_seam_5y)

UNITS: Final[dict[str, str]] = {m.key: m.unit for m in _ALL}
REQUIRE_MONOTONIC: Final[dict[str, bool]] = {m.key: m.monotonic for m in _ALL}
FILE_PART: Final[dict[str, str]] = {m.key: m.file_part for m in _ALL if m.file_part}
PUBLISHED_CENTILES: Final[dict[str, tuple[int, ...]]] = {
    m.key: m.published_centiles for m in _ALL
}


def get(key: str) -> Measure:
    """Look up a measure, raising a clear error for an unknown key."""
    try:
        return MEASURES[key]
    except KeyError:
        raise KeyError(
            f"unknown growth measure {key!r}; registered: {', '.join(MEASURE_KEYS)}"
        ) from None


def is_valid(key: str) -> bool:
    return key in MEASURES

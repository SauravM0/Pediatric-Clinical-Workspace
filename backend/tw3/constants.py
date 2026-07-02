"""Canonical TW3-RUS identifiers shared across the whole system.

Single source of truth for the 13 RUS bone codes, their human labels, the
sexes, the stage vocabulary, and assessment statuses. Every module (database,
API, scoring, reports, tests) must import these rather than re-declaring the
bone list or stage letters (directive §3, §38 — no duplicated bone config).
"""

from __future__ import annotations

from enum import Enum
from typing import Final

# The 13 RUS bones, in canonical order. These codes are used verbatim in the
# database, API payloads, frontend state, scoring, annotations and reports.
RUS_BONES: Final[tuple[str, ...]] = (
    "radius", "ulna",
    "mc1", "mc3", "mc5",
    "pp1", "pp3", "pp5",
    "mp3", "mp5",
    "dp1", "dp3", "dp5",
)

BONE_LABELS: Final[dict[str, str]] = {
    "radius": "Radius",
    "ulna": "Ulna",
    "mc1": "First metacarpal",
    "mc3": "Third metacarpal",
    "mc5": "Fifth metacarpal",
    "pp1": "Proximal phalanx (1st digit)",
    "pp3": "Proximal phalanx (3rd digit)",
    "pp5": "Proximal phalanx (5th digit)",
    "mp3": "Middle phalanx (3rd digit)",
    "mp5": "Middle phalanx (5th digit)",
    "dp1": "Distal phalanx (1st digit)",
    "dp3": "Distal phalanx (3rd digit)",
    "dp5": "Distal phalanx (5th digit)",
}

# Stage vocabulary. The active method is TW3-C RUS, which grades each bone on a
# numeric 1–8 scale (ulna has no grade 8). The authoritative allowed stages per
# bone come from the data file (tables.py); this is the full ordered vocabulary
# used for validation and UI ordering. (Original TW3 used A–I letters; TW3-C
# replaces them with grades 1–8 — see tw3_tables.json 'notes'.)
STAGES: Final[tuple[str, ...]] = ("1", "2", "3", "4", "5", "6", "7", "8")

# Sex at birth as used by the sex-specific TW3 tables.
SEXES: Final[tuple[str, ...]] = ("boys", "girls")

RUS_BONE_COUNT: Final[int] = len(RUS_BONES)


class AssessmentStatus(str, Enum):
    """Allowed lifecycle states for a TW3 assessment (directive §9.3)."""

    DRAFT = "draft"
    INCOMPLETE = "incomplete"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def months_to_years_months(total_months: int) -> tuple[int, int]:
    """126 -> (10, 6). Internal results are stored in whole months (directive §12)."""
    if total_months < 0:
        raise ValueError("bone age in months cannot be negative")
    return divmod(total_months, 12)

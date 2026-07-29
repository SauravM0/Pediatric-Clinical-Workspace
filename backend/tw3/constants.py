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

# The 7 carpal bones, in canonical order (matches the report layout). Carpals are
# staged for annotation only: the project has NO licensed carpal scoring tables,
# so carpal scores/ages stay disabled until the doctor supplies them (directive
# §6 Gate 1, §15 — carpals are never treated as ordinary phalanges).
CARPAL_BONES: Final[tuple[str, ...]] = (
    "capitate", "hamate", "triquetral", "lunate", "scaphoid", "trapezium", "trapezoid",
)

CARPAL_LABELS: Final[dict[str, str]] = {
    "capitate": "Capitate",
    "hamate": "Hamate",
    "triquetral": "Triquetral",
    "lunate": "Lunate",
    "scaphoid": "Scaphoid",
    "trapezium": "Trapezium",
    "trapezoid": "Trapezoid",
}

ALL_BONE_LABELS: Final[dict[str, str]] = {**BONE_LABELS, **CARPAL_LABELS}

# Stage vocabulary. The active method is TW3-C RUS, which grades each bone on a
# numeric 1–8 scale (ulna has no grade 8). The authoritative allowed stages per
# bone come from the data file (tables.py); this is the full ordered vocabulary
# used for validation and UI ordering. (Original TW3 used A–I letters; TW3-C
# replaces them with grades 1–8 — see tw3_tables.json 'notes'.)
STAGES: Final[tuple[str, ...]] = ("1", "2", "3", "4", "5", "6", "7", "8")

# Original-TW3 maturity letters. Used for the doctor's letter-based 20-bone
# annotation stream (13 RUS + 7 carpals). NB: the licensed original-TW3 source
# defines which letters are valid for each individual bone; the project does not
# have that source, so — for now — every bone offers A–I and this is flagged as
# unverified in the API. It is annotation only: no scoring is derived from it.
LETTER_STAGES: Final[tuple[str, ...]] = ("A", "B", "C", "D", "E", "F", "G", "H", "I")

# Acquisition domains (directive §16). The doctor may want AI suggestions even for
# a phone photo of a film, but the three domains must be tracked and evaluated
# separately — a model validated on DICOM cannot claim the same confidence on a
# glare-y photograph. 'unknown' is the honest default until the doctor confirms.
IMAGE_DOMAINS: Final[tuple[str, ...]] = (
    "digital_diagnostic",  # DICOM / PACS PNG / direct digital
    "compressed",          # WhatsApp / screenshot / compressed export
    "film_photo",          # mobile photograph of a film (glare, border, perspective)
    "unknown",
)

# Domains that must carry a prominent low-quality warning (§16).
LOW_TRUST_DOMAINS: Final[frozenset[str]] = frozenset({"compressed", "film_photo"})

# Sex at birth as used by the sex-specific TW3 tables.
SEXES: Final[tuple[str, ...]] = ("boys", "girls")

RUS_BONE_COUNT: Final[int] = len(RUS_BONES)
CARPAL_BONE_COUNT: Final[int] = len(CARPAL_BONES)


class StageSystem(str, Enum):
    """Which maturity vocabulary an assessment is staged in (directive §6, §18).

    The two streams are deliberately separate and never mixed:

    * ``TW3C_RUS`` — TW3-C (Chinese) RUS, numeric grades 1–8, 13 RUS bones. This
      is the only stream with verified point tables, so deterministic scoring
      (stage → score → bone age) is ENABLED here.
    * ``TW3_LETTERS`` — original-TW3 letters A–I, 13 RUS + 7 carpals (20 bones).
      Used to capture the doctor's staging in her familiar vocabulary. The
      licensed original-TW3 point/age tables are not available, so scoring is
      DISABLED: staging is persisted as annotation and every score/age shows '—'
      until the tables are supplied (directive §39, Gate 1).
    """

    TW3C_RUS = "tw3c-rus"
    TW3_LETTERS = "tw3-letters"


DEFAULT_STAGE_SYSTEM: Final[str] = StageSystem.TW3C_RUS.value

# ── Method labelling (M3.2) ──────────────────────────────────────────────────
# The active deterministic path is NOT Tanner-Whitehouse TW3. Its per-stage
# points were transcribed from Table 1 of a deep-learning conference paper
# (AIPR 2023), and its score->age curve was DIGITIZED FROM A FIGURE in that same
# paper -- 10-11 anchors at integer years, self-declared +/-0.5y. Two secondary
# sources for the two numbers that entirely determine the output.
#
# Displaying that as "TW3" invites a clinician to read it as the Tanner standard
# they know. It is not: on this centre's own films the TW3-C score (880) and the
# historically-reported original-TW3 RUS (681) differ by ~0.9-1.25 years of bone
# age. Every surface that shows a bone age must therefore carry the qualifier.
#
# Single source of truth so the label cannot drift between API, report and UI;
# tests/bone_age/test_method_labelling.py asserts each surface carries it.
METHOD_DISPLAY_NAME: Final[str] = "TW3-C (Chinese) RUS — provisional"
METHOD_QUALIFIER: Final[str] = (
    "Provisional research curve (±0.5y, digitized from a published figure). "
    "Not Tanner-Whitehouse TW3."
)
METHOD_SOURCE_NOTE: Final[str] = (
    "Stage points: Gu, Meng & Meng, AIPR 2023, Table 1 (grades 1–8). "
    "Score-to-age: digitized from Figure 8 of the same paper. "
    "Bone ages are not interchangeable with original-TW3 or Greulich–Pyle values."
)

# The 20-bone score is a TW2 construct. TW3 (Tanner et al. 2001) publishes RUS
# (13 bones) and Carpal (7 bones) as two SEPARATE, non-additive systems and does
# not define a 20-bone score at all -- so "TW3 20-bone bone age" is not a thing
# that exists, and RUS and carpal points must never be summed into one number.
# Used to keep UI copy honest about what the 20-bone staging screen is for.
TWENTY_BONE_NOTE: Final[str] = (
    "All 20 structures are staged for per-bone visibility. TW3 scores RUS (13) "
    "and Carpal (7) separately and defines no combined 20-bone age; a 20-bone "
    "score is a TW2 construct and is never derived by summing the two."
)

# Scoring is only ever derived from a stage system that has verified tables.
SCORING_ENABLED_SYSTEMS: Final[frozenset[str]] = frozenset({StageSystem.TW3C_RUS.value})


def bones_for_system(system: str) -> tuple[str, ...]:
    """Canonical, ordered bone list for a stage system.

    Letters cover all 20 bones (RUS + carpals); TW3-C covers the 13 RUS bones.
    """
    if system == StageSystem.TW3_LETTERS.value:
        return RUS_BONES + CARPAL_BONES
    return RUS_BONES


def bone_group(code: str) -> str:
    """'carpal' for the 7 carpals, else 'rus'."""
    return "carpal" if code in CARPAL_BONES else "rus"


def label_for(code: str) -> str:
    return ALL_BONE_LABELS.get(code, code)


def scoring_enabled(system: str) -> bool:
    return system in SCORING_ENABLED_SYSTEMS


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

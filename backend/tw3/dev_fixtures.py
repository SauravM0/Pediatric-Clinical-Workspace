"""SYNTHETIC, NON-CLINICAL letters-table fixture for development & demos.

This is the single source of the illustrative TW3-letters table used to exercise
the full 20-bone pipeline WITHOUT any real (copyrighted, licensed) TW3 values and
WITHOUT any reconstructed/guessed values. The numbers here are deliberately trivial
and monotonic — they are NOT TW3 data and must never be presented as a clinical
result. Both the end-to-end activation test and the committed dev fixture
(`fixtures/dev_synthetic_letters_tables.json`) are built from this one function, so
there is a single source of truth.

Regenerate the committed fixture after changing this file:
    python -m backend.tw3.dev_fixtures

Launch the app in dev-provisional scoring mode (clearly non-clinical):
    TW3_LETTERS_TABLES_PATH=backend/tw3/fixtures/dev_synthetic_letters_tables.json \
        python -m backend.server
"""
from __future__ import annotations

from pathlib import Path

from backend.tw3 import CARPAL_BONES, LETTER_STAGES, RUS_BONES

_LETTERS = list(LETTER_STAGES)  # A..I

_PROV = {
    "book_title": "SYNTHETIC fixture (NOT a real TW3 book)",
    "edition": "dev-1",
    "isbn": "",
    "licensed_owner": "Development / Demo (non-clinical)",
    "pages": "n/a",
    "entered_by": "dev-fixture",
    "verified_by": "dev-fixture",
    "verification_date": "2026-07-14",
}


def _points() -> dict:
    """letter -> points, with A dropped so allowed_letters is provably DERIVED (B..I)."""
    return {L: float(i + 1) for i, L in enumerate(_LETTERS) if L != "A"}  # B=2 .. I=9


def synthetic_letters_table() -> dict:
    """A structurally-complete, clearly non-clinical letters table (girls stream).

    Linear score->age curves make the reference cases exact:
      all-H RUS = 13*8 = 104 -> 13.75y ; all-I RUS = 13*9 = 117 -> 15.0y
      all-G carpal = 7*7 = 49 -> 11.5y ; all-I carpal = 7*9 = 63 -> 14.0y
    """
    girls_rus = {b: _points() for b in RUS_BONES}        # 13 bones
    girls_carpal = {c: _points() for c in CARPAL_BONES}  # 7 bones
    return {
        "method": "TW3-letters",
        "version": "SYNTHETIC-NONCLINICAL-1",
        "source_reference": "SYNTHETIC fixture — NOT real TW3 values (development only)",
        "provenance": _PROV,
        "rus_stage_to_score": {"girls": girls_rus},
        "carpal_stage_to_score": {"girls": girls_carpal},
        "rus_score_to_age": {"twiii": {"girls": [[13, 5.0], [117, 15.0]]},
                             "twii": {"girls": [[13, 4.0], [117, 16.0]]}},
        "carpal_score_to_age": {"twiii": {"girls": [[7, 4.0], [63, 14.0]]},
                                "twii": {"girls": [[7, 3.0], [63, 15.0]]}},
        "reference_cases": [
            {"id": "ref-1", "sex": "girls",
             "rus_stages": {b: "H" for b in RUS_BONES},
             "carpal_stages": {c: "G" for c in CARPAL_BONES},
             "expected": {"rus_score": 104, "twiii_rus_age_years": 13.75,
                          "carpal_score": 49, "twiii_carpal_age_years": 11.5},
             "tolerance_years": 0.3},
            {"id": "ref-2", "sex": "girls",
             "rus_stages": {b: "I" for b in RUS_BONES},
             "carpal_stages": {c: "I" for c in CARPAL_BONES},
             "expected": {"rus_score": 117, "twiii_rus_age_years": 15.0,
                          "carpal_score": 63, "twiii_carpal_age_years": 14.0},
             "tolerance_years": 0.3},
        ],
    }


FIXTURE_PATH = Path(__file__).with_name("fixtures") / "dev_synthetic_letters_tables.json"


def write_fixture(path: Path = FIXTURE_PATH) -> Path:
    """Validate + checksum-lock the synthetic table into the committed dev fixture."""
    from backend.tw3 import letters_scoring as ls
    path.parent.mkdir(parents=True, exist_ok=True)
    ls.save_letter_tables(synthetic_letters_table(), path)  # validates + writes checksum
    return path


def main() -> int:
    p = write_fixture()
    from backend.tw3 import letters_scoring as ls
    t = ls.load_letter_tables(p)
    print(f"Wrote dev fixture: {p}")
    print(f"  checksum_verified={t.checksum_verified}  provenance_complete={t.provenance_complete()}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

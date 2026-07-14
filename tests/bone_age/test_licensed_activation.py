"""End-to-end licensed-TW3 activation (Plan 1 WI-4 + WI-7).

Proves the WHOLE licensed path lights up without shipping any real copyrighted
values: a SYNTHETIC, clearly-non-clinical letters table with full provenance, a
valid checksum, and two self-consistent reference cases makes all four gates pass
-> /config turns scoring on -> /report returns real, SEPARATE RUS and carpal bone
ages -> tampering the file reverts everything to disabled.

The fixture values are illustrative and monotonic; they are NOT TW3 data.
"""
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "activation_test.db"))

import pytest
from fastapi.testclient import TestClient

import backend.tw3.letters_scoring as ls
from backend.server import app
from backend.tw3 import CARPAL_BONES, LETTER_STAGES, RUS_BONES

_LETTERS = list(LETTER_STAGES)  # A..I
_PROV = {
    "book_title": "SYNTHETIC fixture (NOT a real TW3 book)",
    "edition": "test-1",
    "isbn": "",
    "licensed_owner": "Unit Test Clinic",
    "pages": "n/a",
    "entered_by": "test",
    "verified_by": "test-2",
    "verification_date": "2026-07-13",
}


def _points() -> dict:
    """letter -> points, A dropped so allowed_letters is provably DERIVED (B..I)."""
    return {L: float(i + 1) for i, L in enumerate(_LETTERS) if L != "A"}  # B=2 .. I=9


def _synthetic_table() -> dict:
    girls_rus = {b: _points() for b in RUS_BONES}       # 13 bones
    girls_carpal = {c: _points() for c in CARPAL_BONES}  # 7 bones
    return {
        "method": "TW3-letters",
        "version": "SYNTHETIC-NONCLINICAL-1",
        "source_reference": "SYNTHETIC fixture — NOT real TW3 values",
        "provenance": _PROV,
        "rus_stage_to_score": {"girls": girls_rus},
        "carpal_stage_to_score": {"girls": girls_carpal},
        # linear score->age so reference cases are exact:
        #   all-H RUS = 13*8 = 104 -> 13.75y ; all-I RUS = 13*9 = 117 -> 15.0y
        "rus_score_to_age": {"twiii": {"girls": [[13, 5.0], [117, 15.0]]},
                             "twii": {"girls": [[13, 4.0], [117, 16.0]]}},
        #   all-G carpal = 7*7 = 49 -> 11.5y ; all-I carpal = 7*9 = 63 -> 14.0y
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


@pytest.fixture
def fixture_path(tmp_path, monkeypatch):
    p = tmp_path / "letters_tables.json"
    ls.save_letter_tables(_synthetic_table(), p)     # validates + writes checksum
    monkeypatch.setattr(ls, "_TABLES_PATH", p)       # point the whole app at it
    return p


def test_all_four_gates_pass_and_scoring_ready(fixture_path):
    st = ls.letters_status()
    assert st["scoring_ready"] is True
    assert st["any_calibrated"] is True
    assert st["reference_validation"]["all_passed"] is True
    assert st["provenance_complete"] is True
    assert st["checksum_verified"] is True


def test_config_turns_scoring_on_and_derives_letters(fixture_path):
    body = TestClient(app).get("/api/bone-age/config").json()
    letters = body["stage_systems"]["tw3-letters"]
    assert letters["scoring_enabled"] is True
    assert letters["letter_stages_unverified"] is False
    assert all(letters["gates"].values())
    # allowed letters are DERIVED from the entered points (A was dropped).
    radius = next(b for b in letters["bones"] if b["code"] == "radius")
    assert "A" not in radius["stages"]
    assert set(radius["stages"]) == set("BCDEFGHI")


def test_report_returns_separate_rus_and_carpal_ages(fixture_path):
    r = TestClient(app).post("/api/bone-age/report", json={
        "sex": "girls",
        "rus_stages": {b: "H" for b in RUS_BONES},
        "carpal_stages": {c: "G" for c in CARPAL_BONES},
        "chronological_age_years": 10.0,
    })
    assert r.status_code == 200
    rep = r.json()
    assert rep["method"]["scoring_enabled"] is True
    assert rep["definitive_bone_age_years"] == 13.75      # RUS via TWIII
    assert rep["carpal_definitive_age_years"] == 11.5     # carpal, SEPARATE
    assert rep["definitive_bone_age_years"] != rep["carpal_definitive_age_years"]
    assert rep["maturation"] == "ADVANCED"                # 13.75 vs 10.0
    radius = next(b for b in rep["per_bone_results"] if b["bone_code"] == "radius")
    assert radius["scored"] is True and radius["points"] == 8.0


def test_tamper_reverts_to_disabled(fixture_path):
    doc = json.loads(fixture_path.read_text(encoding="utf-8"))
    doc["rus_stage_to_score"]["girls"]["radius"]["H"] = 999.0  # edit, keep old checksum
    fixture_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(ls.LetterTablesError, match="checksum mismatch"):
        ls.letters_status()

    letters = TestClient(app).get("/api/bone-age/config").json()["stage_systems"]["tw3-letters"]
    assert letters["scoring_enabled"] is False
    assert "error" in letters and "checksum mismatch" in letters["error"]

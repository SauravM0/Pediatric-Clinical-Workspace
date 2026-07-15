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
from backend.tw3 import CARPAL_BONES, RUS_BONES
from backend.tw3.dev_fixtures import synthetic_letters_table


@pytest.fixture
def fixture_path(tmp_path, monkeypatch):
    p = tmp_path / "letters_tables.json"
    ls.save_letter_tables(synthetic_letters_table(), p)  # validates + writes checksum
    monkeypatch.setattr(ls, "_TABLES_PATH", p)           # point the whole app at it
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

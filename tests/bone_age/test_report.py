"""Structured 20-bone bone-age report (directive S-BA-4).

The report shows EVERY expected structure (13 RUS + 7 carpal) with its stage and
visibility, keeps RUS and carpal ages SEPARATE (never averaged), never invents a
per-bone age, and stays honest (scores/ages null until licensed tables exist).
Runs headless via FastAPI TestClient -- no model/GPU needed.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "report_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.tw3 import RUS_BONES, CARPAL_BONES
from backend.tw3.report import build_report
from backend.server import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_report_has_all_20_bones_in_canonical_order():
    rep = build_report("girls", {"radius": "H"}, {"capitate": "G"})
    rows = rep["per_bone_results"]
    assert len(rows) == 20
    assert [r["display_order"] for r in rows] == list(range(1, 21))
    assert [r["bone_id"] for r in rows[:13]] == [b.upper() for b in RUS_BONES]
    assert [r["bone_id"] for r in rows[13:]] == [b.upper() for b in CARPAL_BONES]
    assert all(r["system"] == "RUS" for r in rows[:13])
    assert all(r["system"] == "CARPAL" for r in rows[13:])


def test_visibility_states_recorded_and_not_scored():
    rep = build_report("boys", {"radius": "H", "ulna": "NOT_VISIBLE", "mc1": "NOT_SCORABLE"}, {})
    by = {r["bone_code"]: r for r in rep["per_bone_results"]}
    assert by["radius"]["visibility"] == "STAGED"
    assert by["ulna"]["visibility"] == "NOT_VISIBLE"
    assert by["mc1"]["visibility"] == "NOT_SCORABLE"
    assert by["mc5"]["visibility"] == "NOT_STAGED"
    # a flagged bone is never scored
    assert by["ulna"]["scored"] is False and by["ulna"]["points"] is None
    assert rep["completeness"]["rus_not_visible_or_scorable"] == 2
    assert rep["completeness"]["rus_staged"] == 1


def test_no_per_bone_age_is_ever_invented():
    rep = build_report("girls", {b: "H" for b in RUS_BONES}, {})
    for r in rep["per_bone_results"]:
        assert "age" not in r and "age_years" not in r, "TW3 has no per-bone age"


def test_rus_and_carpal_ages_are_separate_and_never_averaged():
    rep = build_report("girls", {b: "H" for b in RUS_BONES},
                       {c: "G" for c in CARPAL_BONES}, chronological_age_years=13.0)
    assert "rus" in rep and "carpal" in rep
    assert rep["rus"]["system"] == "RUS" and rep["carpal"]["system"] == "CARPAL"
    # no combined/averaged field anywhere in the summary
    assert "combined_age_years" not in rep and "average_age_years" not in rep
    # uncalibrated shipped tables -> no age, honest note, review required
    assert rep["rus"]["twiii_age_years"] is None
    assert rep["carpal"]["twiii_age_years"] is None
    assert rep["definitive_bone_age_years"] is None
    assert rep["method"]["scoring_enabled"] is False
    assert rep["scoring_note"] and "licensed TW3 tables" in rep["scoring_note"]
    assert rep["clinician_review"]["required"] is True
    assert rep["mandatory_disclaimer"]


def test_ai_estimate_is_a_separate_cross_check_not_a_tw3_age():
    rep = build_report("boys", {"radius": "H"}, {}, ai_estimate_years=11.7)
    assert rep["ai_screening_estimate_years"] == 11.7
    # it must NOT become the definitive/TW3 bone age
    assert rep["definitive_bone_age_years"] is None


def test_endpoint_returns_structured_report(client):
    r = client.post("/api/bone-age/report", json={
        "sex": "girls",
        "rus_stages": {"radius": "H", "ulna": "NOT_VISIBLE"},
        "carpal_stages": {"capitate": "G"},
        "chronological_age_years": 12.5,
        "ai_estimate_years": 12.0,
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["per_bone_results"]) == 20
    assert body["completeness"]["rus_not_visible_or_scorable"] == 1
    assert body["ai_screening_estimate_years"] == 12.0
    assert body["mandatory_disclaimer"]


def test_endpoint_rejects_bad_sex(client):
    r = client.post("/api/bone-age/report", json={"sex": "other"})
    assert r.status_code == 422

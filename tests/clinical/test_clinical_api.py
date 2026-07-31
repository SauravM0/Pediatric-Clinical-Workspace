"""End-to-end: stored observations become findings and a triage level (M5).

This is the join M2 made possible. Before it, no measurement was stored, so no
trajectory rule could exist.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.db import init_db, session_scope
from backend.models import Patient
from backend.server import app

BIRTH = datetime(2016, 1, 15)


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def patient_id():
    with session_scope() as db:
        p = Patient(patient_code=f"M5-{uuid.uuid4().hex[:8]}", name="Reasoning Child",
                    sex_at_birth="girls", date_of_birth=BIRTH,
                    mother_height_cm=152.0, father_height_cm=168.0,
                    parental_height_source="measured")
        db.add(p)
        db.flush()
        return p.id


def _obs(client, pid, obs_type, value, years):
    return client.post(f"/api/patients/{pid}/observations", json={
        "obs_type": obs_type, "value": value,
        "observed_at": (BIRTH + timedelta(days=int(365.25 * years))).isoformat()})


def test_a_child_falling_off_her_centile_is_flagged(client, patient_id):
    """The clinical case the whole product exists for."""
    for years, height in ((5, 108.0), (6, 112.0), (7, 115.0), (8, 117.0)):
        assert _obs(client, patient_id, "height", height, years).status_code == 201

    body = client.get(f"/api/clinical/patients/{patient_id}/assessment").json()
    ids = {f["rule_id"] for f in body["findings"]}

    assert "DOWNWARD_CENTILE_CROSSING" in ids, "a sustained centile fall was not detected"
    assert "LOW_HEIGHT_VELOCITY" in ids
    assert body["triage"]["level"] == "specialist_soon"
    assert "paediatric endocrinology" in body["triage"]["specialties"]

    crossing = next(f for f in body["findings"] if f["rule_id"] == "DOWNWARD_CENTILE_CROSSING")
    assert crossing["inputs_used"]["change_sds"] < -0.67
    assert crossing["source"]


def test_a_normally_growing_child_gets_monitoring_not_an_all_clear(client, patient_id):
    for years, height in ((5, 108.0), (6, 114.5), (7, 121.0)):
        _obs(client, patient_id, "height", height, years)
    body = client.get(f"/api/clinical/patients/{patient_id}/assessment").json()
    assert body["triage"]["level"] == "routine_monitoring"
    assert "keep measuring" in body["triage"]["guidance"].lower()


def test_checks_that_could_not_run_are_reported(client, patient_id):
    """A thin record must not read as a clean one."""
    _obs(client, patient_id, "height", 115.0, 7)
    body = client.get(f"/api/clinical/patients/{patient_id}/assessment").json()
    assert body["triage"]["not_assessed"], "nothing was reported as un-assessed"
    gaps = [f for f in body["findings"] if f["severity"] == "insufficient_data"]
    assert any("missing" in f["inputs_used"] for f in gaps)


def test_assessment_carries_a_disclaimer(client, patient_id):
    _obs(client, patient_id, "height", 115.0, 7)
    body = client.get(f"/api/clinical/patients/{patient_id}/assessment").json()
    assert "not diagnoses" in body["disclaimer"]
    assert "does not exclude disease" in body["disclaimer"]


def test_adult_height_separates_target_from_prediction(client, patient_id):
    _obs(client, patient_id, "height", 115.0, 7)
    _obs(client, patient_id, "weight", 20.0, 7)
    body = client.get(f"/api/clinical/patients/{patient_id}/adult-height").json()
    assert body["genetic_target"]["target_cm"] == pytest.approx((152 + 168 - 13) / 2)
    assert body["predicted_adult_height"]["available"] is False
    assert "different quantities" in body["note"]


def test_parent_summary_is_not_generated_by_default(client, patient_id):
    """Two gates: a doctor's permission AND an explicit release. The failure mode
    is not a wrong number, it is a worried parent acting on a sentence nobody
    chose to send them."""
    _obs(client, patient_id, "height", 115.0, 7)
    r = client.get(f"/api/clinical/patients/{patient_id}/parent-summary")
    assert r.status_code == 403
    assert "explicitly released" in r.json()["detail"]


def test_parent_summary_when_released_avoids_diagnosis(client, patient_id):
    _obs(client, patient_id, "height", 100.0, 7)
    body = client.get(
        f"/api/clinical/patients/{patient_id}/parent-summary?release=true").json()
    assert "not a diagnosis" in body["important"]
    assert body["questions_to_ask"]
    assert "what_to_do" in body


def test_rules_endpoint_publishes_what_is_checked_and_on_whose_authority(client):
    body = client.get("/api/clinical/rules").json()
    assert len(body["rules"]) >= 10
    assert all(r["requires"] is not None for r in body["rules"])
    assert body["triage_levels"] == ["routine_monitoring", "discuss_with_paediatrician",
                                     "specialist_soon"]
    assert all("source" in v for k, v in body["thresholds"].items() if k != "version")


def test_unknown_patient_is_404(client):
    assert client.get("/api/clinical/patients/999999/assessment").status_code == 404

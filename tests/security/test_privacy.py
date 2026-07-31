"""Consent, access, erasure and retention (DPDP Act 2023 — C.3)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend import privacy_service as svc
from backend.db import SessionLocal, init_db, session_scope
from backend.models import Patient, SecurityEvent, TW3Assessment
from backend.server import app


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def patient_id():
    import uuid

    code = f"PRIV-{uuid.uuid4().hex[:8]}"
    with session_scope() as db:
        p = Patient(patient_code=code, name="Test Child", sex_at_birth="girls")
        db.add(p)
        db.flush()
        pid = p.id
        db.add(TW3Assessment(patient_id=pid, sex_at_birth="girls"))
    return pid


# ── consent ─────────────────────────────────────────────────────────────────

def test_absent_consent_is_not_granted(client, patient_id):
    """DPDP requires affirmative consent: silence is not agreement."""
    body = client.get(f"/api/privacy/patients/{patient_id}/consent").json()
    for purpose, state in body["purposes"].items():
        assert state["granted"] is False, f"{purpose} defaulted to granted"
        assert state["explicitly_recorded"] is False


def test_consent_is_recorded_per_purpose(client, patient_id):
    """Agreeing to care is not agreeing to model training."""
    r = client.post(f"/api/privacy/patients/{patient_id}/consent", json={
        "purpose": "clinical_care", "granted": True,
        "given_by": "Priya Sharma", "relationship": "mother"})
    assert r.status_code == 201

    state = client.get(f"/api/privacy/patients/{patient_id}/consent").json()["purposes"]
    assert state["clinical_care"]["granted"] is True
    assert state["clinical_care"]["relationship"] == "mother"
    assert state["model_training"]["granted"] is False, (
        "consenting to care silently granted model training"
    )


def test_withdrawal_uses_the_same_endpoint_and_wins(client, patient_id):
    """DPDP: withdrawal must be as easy as giving."""
    url = f"/api/privacy/patients/{patient_id}/consent"
    client.post(url, json={"purpose": "model_training", "granted": True})
    assert client.get(url).json()["purposes"]["model_training"]["granted"] is True

    client.post(url, json={"purpose": "model_training", "granted": False})
    assert client.get(url).json()["purposes"]["model_training"]["granted"] is False


def test_consent_history_is_appended_never_overwritten(client, patient_id):
    """A regulator asks what was agreed and when, not just the current state."""
    url = f"/api/privacy/patients/{patient_id}/consent"
    client.post(url, json={"purpose": "research", "granted": True})
    client.post(url, json={"purpose": "research", "granted": False})
    client.post(url, json={"purpose": "research", "granted": True})
    assert client.get(url).json()["history_count"] == 3


def test_unknown_purpose_is_rejected(client, patient_id):
    r = client.post(f"/api/privacy/patients/{patient_id}/consent",
                    json={"purpose": "sell_to_insurer", "granted": True})
    assert r.status_code == 422


def test_has_consent_helper_matches_the_api(client, patient_id):
    client.post(f"/api/privacy/patients/{patient_id}/consent",
                json={"purpose": "quality_audit", "granted": True})
    with SessionLocal() as db:
        assert svc.has_consent(db, patient_id, "quality_audit") is True
        assert svc.has_consent(db, patient_id, "research") is False


# ── right of access ─────────────────────────────────────────────────────────

def test_export_returns_the_whole_record_and_is_logged(client, patient_id):
    r = client.get(f"/api/privacy/patients/{patient_id}/export")
    assert r.status_code == 200
    body = r.json()
    # The subject's own data, so identifiers are deliberately included.
    assert body["patient"]["name"] == "Test Child"
    assert len(body["assessments"]) == 1
    assert "consent" in body and "retention" in body

    with SessionLocal() as db:
        assert db.execute(
            select(SecurityEvent).where(SecurityEvent.event_type == "data_export")
            .where(SecurityEvent.patient_id == patient_id)
        ).scalars().first() is not None, "handing over a full record was not logged"


def test_export_of_unknown_patient_is_404(client):
    assert client.get("/api/privacy/patients/999999/export").status_code == 404


# ── erasure ─────────────────────────────────────────────────────────────────

def test_pseudonymise_destroys_identifiers_but_keeps_clinical_rows(client, patient_id):
    req = client.post(f"/api/privacy/patients/{patient_id}/erasure",
                      json={"requested_by": "mother"}).json()
    out = client.post(f"/api/privacy/erasure/{req['id']}/execute",
                      json={"mode": "pseudonymise"}).json()

    assert out["identifiers_removed"] is True
    assert out["assessments_retained"] == 1, "clinical rows were destroyed by the default mode"
    assert out["rows_deleted"] == 0

    with SessionLocal() as db:
        p = db.get(Patient, patient_id)
        assert p.name is None and p.date_of_birth is None
        assert p.patient_code.startswith("ERASED-")
        assert db.execute(
            select(TW3Assessment).where(TW3Assessment.patient_id == patient_id)
        ).scalars().first() is not None


def test_full_delete_removes_clinical_rows(client, patient_id):
    req = client.post(f"/api/privacy/patients/{patient_id}/erasure", json={}).json()
    out = client.post(f"/api/privacy/erasure/{req['id']}/execute",
                      json={"mode": "delete"}).json()
    assert out["rows_deleted"] >= 1 and out["assessments_retained"] == 0
    with SessionLocal() as db:
        assert db.execute(
            select(TW3Assessment).where(TW3Assessment.patient_id == patient_id)
        ).scalars().first() is None


def test_erasure_cannot_be_executed_twice(client, patient_id):
    req = client.post(f"/api/privacy/patients/{patient_id}/erasure", json={}).json()
    assert client.post(f"/api/privacy/erasure/{req['id']}/execute", json={}).status_code == 200
    r = client.post(f"/api/privacy/erasure/{req['id']}/execute", json={})
    assert r.status_code == 422 and "already" in r.json()["detail"]


def test_erasure_is_recorded_in_the_security_log(client, patient_id):
    req = client.post(f"/api/privacy/patients/{patient_id}/erasure", json={}).json()
    client.post(f"/api/privacy/erasure/{req['id']}/execute", json={})
    with SessionLocal() as db:
        ev = db.execute(
            select(SecurityEvent).where(SecurityEvent.event_type == "erasure")
            .where(SecurityEvent.patient_id == patient_id)
        ).scalars().first()
        assert ev is not None and ev.severity == "warn"


def test_erased_radiographs_are_excluded_from_future_training_exports(client, patient_id):
    """Withdrawing by erasure must also stop the images being reused."""
    from backend.models import Radiograph

    with session_scope() as db:
        db.add(Radiograph(patient_id=patient_id, consent_status="consented"))
    req = client.post(f"/api/privacy/patients/{patient_id}/erasure", json={}).json()
    client.post(f"/api/privacy/erasure/{req['id']}/execute", json={"mode": "pseudonymise"})
    with SessionLocal() as db:
        for r in db.execute(
            select(Radiograph).where(Radiograph.patient_id == patient_id)
        ).scalars().all():
            assert r.consent_status == "withheld"


def test_invalid_erasure_mode_is_rejected(client, patient_id):
    req = client.post(f"/api/privacy/patients/{patient_id}/erasure", json={}).json()
    r = client.post(f"/api/privacy/erasure/{req['id']}/execute", json={"mode": "shred"})
    assert r.status_code == 422


# ── retention ───────────────────────────────────────────────────────────────

def test_retention_review_reports_and_never_deletes(client):
    body = client.get("/api/privacy/retention").json()
    assert body["policy_years"] == svc.RETENTION_YEARS_AFTER_LAST_ACTIVITY
    assert "human decision" in body["action"]
    assert isinstance(body["overdue"], list)


def test_recent_patients_are_not_flagged_overdue(client, patient_id):
    overdue = client.get("/api/privacy/retention").json()["overdue"]
    assert patient_id not in [o["patient_id"] for o in overdue]


# ── access control ──────────────────────────────────────────────────────────

def test_assistant_cannot_reach_data_rights_endpoints(real_auth, client, patient_id):
    """Exporting or erasing a record is not front-desk work."""
    from backend.security import roles
    from tests.security.test_auth import GOOD_PASSWORD, _make_user

    _make_user("nurse_privacy", roles.ASSISTANT)
    client.post("/api/auth/login",
                json={"username": "nurse_privacy", "password": GOOD_PASSWORD})
    assert client.get(f"/api/privacy/patients/{patient_id}/export").status_code == 403
    assert client.post(f"/api/privacy/patients/{patient_id}/erasure", json={}).status_code == 403

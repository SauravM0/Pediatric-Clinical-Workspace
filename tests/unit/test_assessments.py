"""Assessment lifecycle + persistence tests (directive §25.3, §25.4)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.server import app
from backend.tw3 import RUS_BONES

client = TestClient(app)

# case-001 girls grading -> RUS 880
CASE1 = dict(radius="8", ulna="7", mc1="7", mc3="7", mc5="6", pp1="7",
             pp3="7", pp5="7", mp3="7", mp5="7", dp1="7", dp3="7", dp5="7")


def _new_assessment(chrono=10.4) -> dict:
    code = f"CASE-{uuid.uuid4().hex[:8]}"
    r = client.post("/api/bone-age/assessments",
                    json={"patient_code": code, "sex": "girls",
                          "chronological_age_years": chrono})
    assert r.status_code == 201, r.text
    return r.json()


def _grade_all(aid: int, grades: dict) -> None:
    for bone, g in grades.items():
        r = client.put(f"/api/bone-age/assessments/{aid}/bones/{bone}", json={"stage": g})
        assert r.status_code == 200, r.text


def test_create_makes_13_bones_and_draft() -> None:
    a = _new_assessment()
    assert a["assessment_status"] == "draft"
    assert [b["bone_code"] for b in a["bones"]] == list(RUS_BONES)
    assert a["revision"] == 1


def test_full_lifecycle_calculate_and_approve() -> None:
    a = _new_assessment()
    aid = a["id"]
    _grade_all(aid, CASE1)
    calc = client.post(f"/api/bone-age/assessments/{aid}/calculate").json()
    assert calc["assessment_status"] == "ready_for_review"
    assert calc["total_rus_score"] == 880.0
    assert calc["bone_age_months"] is not None
    # bone_age - chronological_age difference is recorded
    assert calc["bone_age_difference_months"] is not None

    appr = client.post(f"/api/bone-age/assessments/{aid}/approve",
                       json={"approved_by": "Dr Test"})
    assert appr.status_code == 200
    assert appr.json()["assessment_status"] == "approved"
    assert appr.json()["doctor_approved"] is True


def test_calculate_incomplete_rejected() -> None:
    a = _new_assessment()
    aid = a["id"]
    client.put(f"/api/bone-age/assessments/{aid}/bones/radius", json={"stage": "8"})
    r = client.post(f"/api/bone-age/assessments/{aid}/calculate")
    assert r.status_code == 422  # only 1 of 13 graded


def test_approve_before_calculate_rejected() -> None:
    a = _new_assessment()
    r = client.post(f"/api/bone-age/assessments/{a['id']}/approve",
                    json={"approved_by": "Dr Test"})
    assert r.status_code == 409


def test_approved_is_immutable() -> None:
    a = _new_assessment()
    aid = a["id"]
    _grade_all(aid, CASE1)
    client.post(f"/api/bone-age/assessments/{aid}/calculate")
    client.post(f"/api/bone-age/assessments/{aid}/approve", json={"approved_by": "Dr Test"})
    # editing a bone on an approved assessment is refused
    r = client.put(f"/api/bone-age/assessments/{aid}/bones/radius", json={"stage": "7"})
    assert r.status_code == 409


def test_revision_supersedes_and_copies_grades() -> None:
    a = _new_assessment()
    aid = a["id"]
    _grade_all(aid, CASE1)
    client.post(f"/api/bone-age/assessments/{aid}/calculate")
    client.post(f"/api/bone-age/assessments/{aid}/approve", json={"approved_by": "Dr Test"})

    rev = client.post(f"/api/bone-age/assessments/{aid}/revise",
                      json={"reason": "re-read"})
    assert rev.status_code == 201
    new = rev.json()
    assert new["revision"] == 2
    assert new["supersedes_id"] == aid
    assert new["assessment_status"] == "draft"
    # grades were copied
    graded = {b["bone_code"]: b["confirmed_stage"] for b in new["bones"]}
    assert graded["radius"] == "8"
    # original is now superseded
    old = client.get(f"/api/bone-age/assessments/{aid}").json()
    assert old["assessment_status"] == "superseded"


def test_editing_after_calculate_returns_to_draft() -> None:
    a = _new_assessment()
    aid = a["id"]
    _grade_all(aid, CASE1)
    client.post(f"/api/bone-age/assessments/{aid}/calculate")
    upd = client.put(f"/api/bone-age/assessments/{aid}/bones/radius", json={"stage": "7"}).json()
    assert upd["assessment_status"] == "draft"
    assert upd["total_rus_score"] is None  # stale result cleared


def test_invalid_grade_rejected() -> None:
    a = _new_assessment()
    r = client.put(f"/api/bone-age/assessments/{a['id']}/bones/radius", json={"stage": "Z"})
    assert r.status_code == 422


def test_audit_trail_recorded() -> None:
    a = _new_assessment()
    aid = a["id"]
    _grade_all(aid, CASE1)
    client.post(f"/api/bone-age/assessments/{aid}/calculate")
    client.post(f"/api/bone-age/assessments/{aid}/approve", json={"approved_by": "Dr Test"})
    full = client.get(f"/api/bone-age/assessments/{aid}?include_audit=true").json()
    events = [e["event_type"] for e in full["audit"]]
    assert "create" in events and "calculation" in events and "approval" in events


def test_reject_requires_reason() -> None:
    a = _new_assessment()
    r = client.post(f"/api/bone-age/assessments/{a['id']}/reject", json={})
    assert r.status_code == 422


def test_missing_assessment_404() -> None:
    assert client.get("/api/bone-age/assessments/999999").status_code == 404


def test_bone_uniqueness_constraint() -> None:
    """Directive §25.4: duplicate (assessment, bone) is rejected by the DB."""
    from sqlalchemy.exc import IntegrityError
    from backend.db import session_scope
    from backend.models import BoneAssessment

    a = _new_assessment()
    with pytest.raises(IntegrityError):
        with session_scope() as db:
            db.add(BoneAssessment(assessment_id=a["id"], bone_code="radius"))

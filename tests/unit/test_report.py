"""TW3-C report generation tests (directive §20, §25.3)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.server import app

client = TestClient(app)

CASE1 = dict(radius="8", ulna="7", mc1="7", mc3="7", mc5="6", pp1="7",
             pp3="7", pp5="7", mp3="7", mp5="7", dp1="7", dp3="7", dp5="7")


def _approved_assessment() -> int:
    code = f"RPT-{uuid.uuid4().hex[:8]}"
    aid = client.post("/api/bone-age/assessments",
                      json={"patient_code": code, "sex": "girls",
                            "chronological_age_years": 10.4}).json()["id"]
    for bone, g in CASE1.items():
        client.put(f"/api/bone-age/assessments/{aid}/bones/{bone}", json={"stage": g})
    client.post(f"/api/bone-age/assessments/{aid}/calculate")
    client.post(f"/api/bone-age/assessments/{aid}/approve", json={"approved_by": "Dr Rathod"})
    return aid


def test_report_before_calculate_rejected() -> None:
    code = f"RPT-{uuid.uuid4().hex[:8]}"
    aid = client.post("/api/bone-age/assessments",
                      json={"patient_code": code, "sex": "girls"}).json()["id"]
    assert client.get(f"/api/bone-age/assessments/{aid}/report").status_code == 409


def test_report_contains_required_fields() -> None:
    aid = _approved_assessment()
    r = client.get(f"/api/bone-age/assessments/{aid}/report")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    # method, total score, bone age, all 13 bone labels, doctor, versions
    assert "Tanner" in body and "TW3-C RUS" in body
    assert "880" in body                     # total RUS score
    assert "12" in body                      # bone age years
    assert "Radius" in body and "Distal phalanx (5th digit)" in body
    assert "Dr Rathod" in body               # approving doctor
    assert "Reviewed and approved" in body   # doctor-review statement, approved
    assert "report template" in body         # version footer
    assert "fully automated" not in body.lower()  # §20 honesty
    assert "adult height" not in body.lower()     # no adult-height in this phase


def test_report_draft_watermark_when_not_approved() -> None:
    code = f"RPT-{uuid.uuid4().hex[:8]}"
    aid = client.post("/api/bone-age/assessments",
                      json={"patient_code": code, "sex": "girls"}).json()["id"]
    for bone, g in CASE1.items():
        client.put(f"/api/bone-age/assessments/{aid}/bones/{bone}", json={"stage": g})
    client.post(f"/api/bone-age/assessments/{aid}/calculate")  # calculated, not approved
    body = client.get(f"/api/bone-age/assessments/{aid}/report").text
    assert "DRAFT" in body

"""End-to-end guard for the bone-age feedback / self-improvement flywheel
(backend/api_bone_age.py + backend/models.BoneAgeFeedback).

The suggestion box records a clinician's corrected bone age as EVIDENCE (never a
patient result). These tests prove the loop works: a correction is stored, the
AI-vs-human error is monitored, and multi-rater disagreement on one image is
flagged for adjudication instead of being silently averaged.

Runs headless via FastAPI's TestClient against a throwaway SQLite DB — no server,
no GPU, no model file needed (the feedback path never touches ONNX).
"""
import os
import tempfile

# Point the app at a throwaway DB BEFORE backend.config is imported (it reads
# TW3_DB_PATH at import time).
_TMP_DB = os.path.join(tempfile.mkdtemp(), "feedback_test.db")
os.environ["TW3_DB_PATH"] = _TMP_DB

import pytest
from fastapi.testclient import TestClient

from backend.db import init_db
from backend.server import app


@pytest.fixture(scope="module")
def client():
    init_db()
    return TestClient(app)


def test_feedback_is_stored_and_scored(client):
    r = client.post("/api/bone-age/feedback", json={
        "corrected_age_years": 11.5,
        "method": "tw3-rus",
        "confidence": "high",
        "rater_id": "DR",
        "sex": "girls",
        "ai_estimate_years": 12.1,
        "ai_model_version": "boneage-gp-test",
        "image_hash": "imgA",
        "image_domain": "digital_diagnostic",
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] and d["id"] > 0
    assert d["corrected_age_years"] == 11.5
    # + means the AI under-estimated relative to the clinician; here it over-read.
    assert d["ai_error_years"] == pytest.approx(-0.6, abs=0.05)


def test_bad_input_is_rejected(client):
    assert client.post("/api/bone-age/feedback", json={"corrected_age_years": 99}).status_code == 422
    assert client.post("/api/bone-age/feedback",
                       json={"corrected_age_years": 10, "method": "made-up"}).status_code == 422
    assert client.post("/api/bone-age/feedback",
                       json={"corrected_age_years": 10, "confidence": "certain"}).status_code == 422


def test_multi_rater_disagreement_flags_adjudication(client):
    # Two clinicians close, a third wildly off on the SAME image → must be flagged,
    # never averaged into a false consensus (report §7.2, mirrors consensus.py).
    for rater, age in [("AB", 11.0), ("CD", 11.4), ("ZZ", 14.5)]:
        assert client.post("/api/bone-age/feedback", json={
            "corrected_age_years": age, "method": "tw3-rus", "confidence": "medium",
            "rater_id": rater, "image_hash": "imgDispute",
        }).status_code == 200

    stats = client.get("/api/bone-age/feedback/stats").json()
    assert stats["total_feedback"] >= 4
    assert stats["ai_vs_human_mae_years"] is not None  # at least one AI-paired row exists
    disputed = [c for c in stats["consensus"] if c["image"] == "imgDispute"][0]
    assert disputed["n_raters"] == 3
    assert disputed["needs_adjudication"] is True
    assert disputed["spread_years"] == pytest.approx(3.5, abs=0.05)

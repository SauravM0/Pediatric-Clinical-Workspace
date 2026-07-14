"""Monitoring & drift endpoint (Plan 2 WI-6 wiring, PLAN-0 A2).

/api/bone-age/monitoring reuses the feedback-stats computation and adds
input-domain drift plus a SOFT, non-gating CPP plausibility panel. Headless via
FastAPI TestClient on a throwaway DB.
"""
import os
import tempfile
from datetime import datetime, timedelta

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "monitoring_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.db import init_db, session_scope
from backend.models import BoneAgeFeedback
from backend.server import app


@pytest.fixture(scope="module")
def client():
    init_db()
    # Seed 9 corrections: older reads are clean/high-error, recent reads are
    # low-trust/low-error -> drift worsens, trend improves.
    base = datetime(2026, 1, 1)
    with session_scope() as db:
        for i in range(9):
            recent = i >= 6
            db.add(BoneAgeFeedback(
                image_hash=f"img{i}",
                sex="boys" if i % 2 else "girls",
                corrected_age_months=108 + i,               # ~9-10y band
                ai_estimate_months=108 + i + (2 if recent else 10),
                method="tw3-letters",
                image_domain="compressed" if recent else "digital_diagnostic",
                confidence="low" if recent else "high",
                rater_id=f"r{i%2}",
                created_at=base + timedelta(days=i),
            ))
    return TestClient(app)


def test_monitoring_returns_stats_drift_and_priors(client):
    body = client.get("/api/bone-age/monitoring").json()
    assert set(body) >= {"stats", "input_drift", "plausibility", "note"}
    assert body["stats"]["paired_with_ai"] == 9


def test_trend_improves_and_drift_worsens(client):
    body = client.get("/api/bone-age/monitoring").json()
    tr = body["stats"]["trend"]
    assert tr["recent_mae_years"] < tr["older_mae_years"]     # recent error is lower
    dr = body["input_drift"]
    assert dr["recent_low_trust_share"] > dr["older_low_trust_share"]
    assert dr["worsening"] is True


def test_plausibility_is_soft_external_and_never_gates(client):
    pl = client.get("/api/bone-age/monitoring").json()["plausibility"]
    assert pl["vs_cpp"]["gating"] is False and pl["vs_control"]["gating"] is False
    assert "EXTERNAL" in pl["vs_cpp"]["caveat"]
    # observed ages (~9-10y) fall in the CPP modal band
    assert pl["observed_bands"]["9-10"] >= 1
    assert "de-prioritise" in pl["maturity_notes"]["cvmi"].lower()

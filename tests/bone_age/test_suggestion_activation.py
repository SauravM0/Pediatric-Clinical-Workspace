"""AI stage-suggestion activation gate, wired into the pipeline (PLAN-0 A4).

The pure gate (suggestion_gate) is tested in test_suggestion_gate.py; this pins
the WIRING: the /suggestion-activation endpoint and the per-bone status carried on
the assessment detail. With no auto-stager model installed, every bone is "manual"
(never a fabricated suggestion) — and the gate genuinely flips to "eligible" when
support + agreement + calibration are met (so it isn't hardcoded off).
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "sugg_activation_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.db import init_db
from backend.server import app


@pytest.fixture(scope="module")
def client():
    init_db()
    return TestClient(app)


def test_endpoint_reports_no_model_installed_all_manual(client):
    body = client.get("/api/bone-age/suggestion-activation").json()
    assert body["any_model_installed"] is False
    assert body["n_allowed"] == 0
    assert "manual" in body["note"]


def test_below_support_yields_manual_decision():
    # The gate itself: a bone below the support floor is never eligible.
    from backend.ai.suggestion_gate import suggestions_allowed
    d = suggestions_allowed("mc3", "boys", support_per_stage={"D": 3, "E": 4},
                            consensus_agreement=0.9, calibration_ok=True)
    assert d["allowed"] is False
    assert any("FAIL support" in r for r in d["reasons"])


def test_gate_flips_eligible_when_all_criteria_met():
    from backend.ai.suggestion_gate import suggestions_allowed
    d = suggestions_allowed("mc3", "boys",
                            support_per_stage={"D": 60, "E": 55, "F": 80},
                            consensus_agreement=0.85, calibration_ok=True)
    assert d["allowed"] is True   # proves the gate is real, not hardcoded off

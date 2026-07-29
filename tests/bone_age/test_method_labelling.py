"""Truth-in-labelling for the bone-age method (M3.2).

The deterministic path is NOT Tanner-Whitehouse TW3. Its stage points came from
Table 1 of a deep-learning conference paper and its score->age curve was
digitized from a figure in that same paper. On this centre's own films the two
disagree by roughly a year of bone age (TW3-C score 880 vs reported original-TW3
RUS 681). Presenting that as "TW3" invites a clinician to read it as the Tanner
standard they were trained on.

These tests pin the qualifier onto every surface that can show a bone age --
API, printed report, and UI -- so it cannot quietly drop off one of them.
The frontend is checked by static analysis, matching tests/frontend/.
"""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "label_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend import reports
from backend.server import app
from backend.tw3 import (
    METHOD_DISPLAY_NAME,
    METHOD_QUALIFIER,
    METHOD_SOURCE_NOTE,
    TWENTY_BONE_NOTE,
)

# M6: the app moved out of index.html into frontend/src/.
from _frontend_source import frontend_source


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── the constants themselves ────────────────────────────────────────────────

def test_qualifier_states_what_it_is_not():
    """The load-bearing half of the label: a reader must learn this is not TW3."""
    assert "Not Tanner-Whitehouse TW3" in METHOD_QUALIFIER
    assert "provisional" in METHOD_DISPLAY_NAME.lower()
    assert "±0.5y" in METHOD_QUALIFIER
    assert "digitized" in METHOD_QUALIFIER.lower()


def test_source_note_names_the_actual_provenance():
    assert "AIPR 2023" in METHOD_SOURCE_NOTE
    assert "Figure 8" in METHOD_SOURCE_NOTE


def test_twenty_bone_note_denies_a_tw3_20_bone_age():
    """TW3 publishes RUS (13) and Carpal (7) separately and defines no combined
    20-bone score -- that is a TW2 construct. Summing them is never valid."""
    assert "TW2" in TWENTY_BONE_NOTE
    assert "separately" in TWENTY_BONE_NOTE.lower()


# ── API surfaces ────────────────────────────────────────────────────────────

def test_config_endpoint_carries_the_labels(client):
    cfg = client.get("/api/bone-age/config").json()
    assert cfg["method_display_name"] == METHOD_DISPLAY_NAME
    assert cfg["method_qualifier"] == METHOD_QUALIFIER
    assert cfg["method_source_note"] == METHOD_SOURCE_NOTE
    assert cfg["twenty_bone_note"] == TWENTY_BONE_NOTE
    # The raw machine code stays available for storage/versioning.
    assert cfg["method"] == "TW3-C-RUS"


def test_score_endpoint_carries_the_labels_and_curve_status(client):
    from backend.tw3.constants import RUS_BONES

    r = client.post("/api/bone-age/score",
                    json={"sex": "boys", "stages": {b: "5" for b in RUS_BONES}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["method_qualifier"] == METHOD_QUALIFIER
    assert body["curve_status"] == "ok"
    assert body["curve_domain"] == [150.0, 1000.0]
    assert body["out_of_curve_domain"] is False


def test_score_endpoint_explains_a_withheld_age(client):
    """M3.1 + M3.2 together: no age, and a reason the UI can render."""
    from backend.tw3.constants import RUS_BONES

    r = client.post("/api/bone-age/score",
                    json={"sex": "boys", "stages": {b: "1" for b in RUS_BONES}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bone_age_years"] is None
    assert body["out_of_curve_domain"] is True
    assert body["curve_status"] == "score_below_curve_domain"
    assert "below the score-to-age curve" in body["status"]


# ── printed report ──────────────────────────────────────────────────────────

def _render(**overrides) -> str:
    from backend.models import TW3Assessment

    assessment = TW3Assessment(
        sex_at_birth="boys", assessment_status="draft",
        assessment_method="TW3-C-RUS", patient_id=1,
    )
    data = {
        "patient_code": "TEST-001", "assessment_method": "TW3-C-RUS",
        "sex_at_birth": "boys", "bone_age_years": 10.5, "bone_age_months": 126,
        "bone_age_difference_months": 6, "total_rus_score": 400.0,
        "chronological_age_months": 120, "bones": [], "status": "ok",
        "doctor_approved": False, "quality_status": "accepted",
    }
    data.update(overrides)
    return reports.render_report_html(assessment, data)


def test_printed_report_carries_the_qualifier():
    """This document goes into a patient file; the number must not travel alone."""
    html = _render()
    assert METHOD_QUALIFIER in html or "Not Tanner-Whitehouse TW3" in html
    assert "Tanner" in html


def test_printed_report_states_when_no_age_was_derived():
    html = _render(bone_age_years=None, bone_age_months=None,
                   status="RUS score 96 is below the score-to-age curve's range (150-1000)")
    assert "No bone age was derived" in html
    assert "below the score-to-age curve" in html
    assert "not derived" in html


# ── UI (static analysis, per tests/frontend convention) ─────────────────────

def test_frontend_does_not_claim_a_tw3_20_bone_age():
    """Regression guard: the header used to read 'Bone Age · TW3 (20 bones: 13
    RUS + 7 carpal)', which asserts a scoring system TW3 does not define."""
    src = frontend_source()
    assert "TW3 (20 bones" not in src, (
        "frontend claims a TW3 20-bone method again -- TW3 scores RUS and carpal "
        "separately; a 20-bone score is TW2."
    )


def test_frontend_footer_does_not_cite_plain_tw3_2001():
    """The reference line used to read 'TW3 2001', implying the Tanner standard
    supplied these numbers. It did not."""
    src = frontend_source()
    assert "· TW3 2001 ·" not in src, (
        "frontend cites 'TW3 2001' as a reference again -- the active curve is "
        "TW3-C digitized from a 2023 paper, not Tanner et al. 2001."
    )
    assert "NOT Tanner–Whitehouse TW3" in src or "Not Tanner-Whitehouse TW3" in src

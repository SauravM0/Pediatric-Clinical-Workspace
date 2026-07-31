"""The longitudinal record: persistence, guards, velocity (M2).

The gap this milestone closes: no growth measurement was stored anywhere.
/api/growth/point took age and value as query parameters, returned a z-score,
and discarded both — so the product could not distinguish a child who has always
been on the 3rd centile (probably a short child) from one who has fallen from the
50th to the 3rd (an urgent endocrine work-up). The trajectory is the diagnosis.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db import SessionLocal, init_db, session_scope
from backend.growth import observations, velocity as vel
from backend.models import Observation, Patient
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
        p = Patient(patient_code=f"M2-{uuid.uuid4().hex[:8]}", name="Trajectory Child",
                    sex_at_birth="girls", date_of_birth=BIRTH)
        db.add(p)
        db.flush()
        return p.id


def _record(client, patient_id, obs_type, value, when, **extra):
    body = {"obs_type": obs_type, "value": value, "observed_at": when.isoformat(), **extra}
    return client.post(f"/api/patients/{patient_id}/observations", json=body)


# ── the core gap ────────────────────────────────────────────────────────────

def test_measurements_persist_across_requests(client, patient_id):
    """Three visits a year apart survive and come back as a trajectory."""
    for years, height in ((5, 108.0), (6, 114.0), (7, 119.5)):
        r = _record(client, patient_id, "height", height, BIRTH + timedelta(days=365 * years))
        assert r.status_code == 201, r.text

    points = client.get(f"/api/patients/{patient_id}/series/height").json()["points"]
    assert len(points) == 3
    assert [round(p["age_years"]) for p in points] == [5, 6, 7]
    assert [p["value"] for p in points] == [108.0, 114.0, 119.5]


def test_age_is_derived_from_date_of_birth_not_supplied(client, patient_id):
    r = _record(client, patient_id, "height", 110.0, BIRTH + timedelta(days=365 * 5))
    assert r.json()["age_years"] == pytest.approx(5.0, abs=0.02)


def test_timeline_returns_everything_on_one_screen(client, patient_id):
    when = BIRTH + timedelta(days=365 * 6)
    _record(client, patient_id, "height", 115.0, when)
    _record(client, patient_id, "weight", 20.0, when)
    client.post(f"/api/patients/{patient_id}/puberty",
                json={"assessed_at": when.isoformat(), "breast_stage": 1, "pubic_hair_stage": 1})

    body = client.get(f"/api/patients/{patient_id}/timeline").json()
    assert body["patient"]["patient_code"].startswith("M2-")
    assert "height" in body["observations"] and "weight" in body["observations"]
    assert len(body["puberty"]) == 1


# ── data-entry guards ───────────────────────────────────────────────────────

@pytest.mark.parametrize("obs_type,value,why", [
    ("height", 1.1, "height typed in metres"),
    ("weight", 20000, "weight typed in grams"),
    ("height", 400, "impossible height"),
])
def test_unit_errors_are_rejected(client, patient_id, obs_type, value, why):
    r = _record(client, patient_id, obs_type, value, BIRTH + timedelta(days=365 * 6))
    assert r.status_code == 422, why
    assert "plausible range" in r.json()["detail"]


def test_a_clinically_extreme_but_real_value_is_still_accepted(client, patient_id):
    """The guard rejects unit errors, not findings. A severely stunted child must
    still be recordable."""
    r = _record(client, patient_id, "height", 85.0, BIRTH + timedelta(days=365 * 7))
    assert r.status_code == 201


def test_same_day_repeat_warns_but_does_not_block(client, patient_id):
    """Re-measuring on the same visit is good practice, not an error."""
    when = BIRTH + timedelta(days=365 * 6)
    _record(client, patient_id, "height", 115.0, when)
    r = _record(client, patient_id, "height", 115.4, when)
    assert r.status_code == 201
    assert any("duplicate_same_day" in w for w in r.json()["warnings"])


def test_implausible_height_loss_is_blocked_by_default(client, patient_id):
    """The most common corruption in a growth clinic: it silently destroys every
    velocity derived from it, and entry is the only cheap place to catch it."""
    _record(client, patient_id, "height", 120.0, BIRTH + timedelta(days=365 * 7))
    r = _record(client, patient_id, "height", 112.0, BIRTH + timedelta(days=365 * 8))
    assert r.status_code == 422
    assert "implausible_decrease" in r.json()["detail"]


def test_implausible_loss_can_be_overridden_deliberately(client, patient_id):
    _record(client, patient_id, "height", 120.0, BIRTH + timedelta(days=365 * 7))
    r = _record(client, patient_id, "height", 112.0, BIRTH + timedelta(days=365 * 8),
                allow_implausible_change=True)
    assert r.status_code == 201
    assert any("implausible_decrease" in w for w in r.json()["warnings"])


def test_small_measurement_variation_is_not_blocked(client, patient_id):
    """Diurnal variation and technique make a few millimetres unremarkable."""
    _record(client, patient_id, "height", 120.0, BIRTH + timedelta(days=365 * 7))
    r = _record(client, patient_id, "height", 119.6, BIRTH + timedelta(days=365 * 8))
    assert r.status_code == 201


def test_observation_before_birth_is_rejected(client, patient_id):
    r = _record(client, patient_id, "height", 50.0, BIRTH - timedelta(days=30))
    assert r.status_code == 422 and "predates" in r.json()["detail"]


def test_unknown_observation_type_is_rejected(client, patient_id):
    r = _record(client, patient_id, "shoe_size", 7, BIRTH + timedelta(days=365 * 6))
    assert r.status_code == 422 and "unknown observation type" in r.json()["detail"]


# ── correction keeps history ────────────────────────────────────────────────

def test_correction_appends_and_never_edits_in_place(client, patient_id):
    """The original is what an earlier printed report was built from; losing it
    makes that report unexplainable."""
    created = _record(client, patient_id, "height", 150.0,
                      BIRTH + timedelta(days=365 * 7)).json()
    r = client.post(f"/api/patients/observations/{created['id']}/correct",
                    json={"new_value": 115.0, "reason": "transposed digits"})
    assert r.status_code == 200

    with SessionLocal() as db:
        original = db.get(Observation, created["id"])
        assert original.value == 150.0, "the original value was mutated"
        assert original.status == "corrected"
        assert original.corrected_by_id == r.json()["id"]

    points = client.get(f"/api/patients/{patient_id}/series/height").json()["points"]
    assert [p["value"] for p in points] == [115.0], "the corrected row is still active"


def test_a_correction_requires_a_reason(client, patient_id):
    created = _record(client, patient_id, "height", 115.0,
                      BIRTH + timedelta(days=365 * 7)).json()
    r = client.post(f"/api/patients/observations/{created['id']}/correct",
                    json={"new_value": 116.0, "reason": ""})
    assert r.status_code == 422


def test_an_observation_cannot_be_corrected_twice(client, patient_id):
    created = _record(client, patient_id, "height", 115.0,
                      BIRTH + timedelta(days=365 * 7)).json()
    body = {"new_value": 116.0, "reason": "re-measured"}
    assert client.post(f"/api/patients/observations/{created['id']}/correct",
                       json=body).status_code == 200
    r = client.post(f"/api/patients/observations/{created['id']}/correct", json=body)
    assert r.status_code == 422 and "already corrected" in r.json()["detail"]


# ── date-of-birth correction ────────────────────────────────────────────────

def test_correcting_date_of_birth_recomputes_every_stored_age(client, patient_id):
    """age_months is a CACHE. Correcting a date of birth without recomputing
    leaves every historical z-score silently wrong."""
    for years in (5, 6, 7):
        _record(client, patient_id, "height", 100.0 + years * 6,
                BIRTH + timedelta(days=365 * years))

    before = [p["age_years"] for p in
              client.get(f"/api/patients/{patient_id}/series/height").json()["points"]]

    corrected = BIRTH + timedelta(days=365)  # a year later than recorded
    r = client.put(f"/api/patients/{patient_id}/date-of-birth",
                   json={"date_of_birth": corrected.isoformat()})
    assert r.status_code == 200 and r.json()["observations_recomputed"] == 3

    after = [p["age_years"] for p in
             client.get(f"/api/patients/{patient_id}/series/height").json()["points"]]
    assert all(a == pytest.approx(b - 1.0, abs=0.02) for a, b in zip(after, before)), (
        "stored ages did not follow the corrected date of birth"
    )


# ── velocity ────────────────────────────────────────────────────────────────

def test_velocity_between_annual_measurements(client, patient_id):
    _record(client, patient_id, "height", 108.0, BIRTH + timedelta(days=365 * 5))
    _record(client, patient_id, "height", 114.0, BIRTH + timedelta(days=365 * 6))
    body = client.get(f"/api/patients/{patient_id}/velocity/height").json()
    assert len(body["intervals"]) == 1
    interval = body["intervals"][0]
    assert interval["available"] is True
    assert interval["velocity_per_year"] == pytest.approx(6.0, abs=0.1)
    assert interval["unit"] == "cm/yr"


def test_short_interval_yields_no_velocity(client, patient_id):
    """Under 6 months, measurement error dominates: a 0.5 cm stadiometer
    difference over 3 months is 2 cm/yr of pure noise."""
    _record(client, patient_id, "height", 108.0, BIRTH + timedelta(days=365 * 5))
    _record(client, patient_id, "height", 109.0, BIRTH + timedelta(days=365 * 5 + 100))
    body = client.get(f"/api/patients/{patient_id}/velocity/height").json()
    interval = body["intervals"][0]
    assert interval["available"] is False
    assert "minimum" in interval["status"]


def test_measurements_within_a_month_are_not_paired(client, patient_id):
    """Two readings a fortnight apart are the same clinical event."""
    base = BIRTH + timedelta(days=365 * 5)
    _record(client, patient_id, "height", 108.0, base)
    _record(client, patient_id, "height", 108.2, base + timedelta(days=14))
    _record(client, patient_id, "height", 114.0, base + timedelta(days=365))
    body = client.get(f"/api/patients/{patient_id}/velocity/height").json()
    assert len(body["intervals"]) == 1, "the fortnight-apart pair was treated as an interval"
    assert body["intervals"][0]["velocity_per_year"] == pytest.approx(6.0, abs=0.2)


def test_velocity_sds_is_withheld_not_invented(client, patient_id):
    """No published velocity reference is bundled yet (B6/M1.3). Reporting a
    centile against an invented SD would be worse than reporting none."""
    _record(client, patient_id, "height", 108.0, BIRTH + timedelta(days=365 * 5))
    _record(client, patient_id, "height", 114.0, BIRTH + timedelta(days=365 * 6))
    body = client.get(f"/api/patients/{patient_id}/velocity/height").json()
    assert body["intervals"][0]["velocity_sds"] is None
    assert body["intervals"][0]["sds_status"] == "no_velocity_reference_available"
    assert "Khadilkar" in body["sds_note"]


def test_long_interval_is_flagged_not_hidden(client, patient_id):
    _record(client, patient_id, "height", 108.0, BIRTH + timedelta(days=365 * 5))
    _record(client, patient_id, "height", 130.0, BIRTH + timedelta(days=365 * 8))
    interval = client.get(f"/api/patients/{patient_id}/velocity/height").json()["intervals"][0]
    assert interval["available"] is True
    assert "long_interval_may_average_out_a_spurt" in interval["flags"]


# ── pure velocity unit tests ────────────────────────────────────────────────

def test_velocity_is_order_independent():
    a = vel.velocity(5.0, 108.0, 6.0, 114.0)
    b = vel.velocity(6.0, 114.0, 5.0, 108.0)
    assert a.velocity_per_year == b.velocity_per_year == pytest.approx(6.0)


def test_velocity_at_identical_ages_is_undefined():
    r = vel.velocity(6.0, 114.0, 6.0, 115.0)
    assert r.available is False and "undefined" in r.status


def test_bmi_decrease_is_not_flagged_as_implausible():
    """BMI legitimately falls (adiposity rebound), so it is not monotonic."""
    r = vel.velocity(5.0, 16.0, 6.0, 15.2, unit="kg/m2", monotonic=False)
    assert r.available is True and not r.flags


# ── puberty ─────────────────────────────────────────────────────────────────

def test_tanner_stage_outside_1_to_5_is_rejected(client, patient_id):
    r = client.post(f"/api/patients/{patient_id}/puberty", json={"breast_stage": 7})
    assert r.status_code == 422 and "Tanner 1-5" in r.json()["detail"]


def test_observation_types_are_advertised(client):
    body = client.get("/api/patients/observation-types").json()
    keys = {t["key"] for t in body["types"]}
    assert {"height", "weight", "head_circumference", "sitting_height"} <= keys
    assert set(keys) == set(observations.OBSERVATION_KEYS)

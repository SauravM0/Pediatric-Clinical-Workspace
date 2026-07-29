"""Absurd measurements are flagged, not scored (M1.2).

A z-score is mathematically defined for any positive value, so a mistyped
measurement produced a confident-looking number: 40 cm entered for a 6-year-old
scored z = -12.9. Rendered next to a real result that reads as a precise
finding rather than a data-entry error.

The domain functions still return the exact value -- they are the honest
primitive, and clamping there would corrupt the maths. The bound is applied at
the API boundary, with a flag, so the UI can say "outside reference range".
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "range_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.growth.lms_core import (
    Z_REPORTABLE_MAX,
    Z_REPORTABLE_MIN,
    clamp_reportable_z,
)
from backend.server import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _point(client, **kw):
    r = client.get("/api/growth/point", params=kw)
    assert r.status_code == 200, r.text
    return r.json()


# ── the helper ──────────────────────────────────────────────────────────────

def test_in_range_values_are_returned_untouched():
    for z in (-4.99, -2.0, 0.0, 1.88079, 4.99):
        got, flagged = clamp_reportable_z(z)
        assert got == z and flagged is False


def test_out_of_range_values_are_clamped_and_flagged():
    got, flagged = clamp_reportable_z(-12.9)
    assert got == Z_REPORTABLE_MIN and flagged is True
    got, flagged = clamp_reportable_z(40.0)
    assert got == Z_REPORTABLE_MAX and flagged is True


def test_boundaries_are_in_range():
    for z in (Z_REPORTABLE_MIN, Z_REPORTABLE_MAX):
        got, flagged = clamp_reportable_z(z)
        assert got == z and flagged is False


def test_none_passes_through():
    assert clamp_reportable_z(None) == (None, False)


# ── through the API ─────────────────────────────────────────────────────────

def test_absurd_height_is_flagged_not_scored(client):
    """The concrete case: 40 cm for a 6-year-old used to score z = -12.9."""
    body = _point(client, measure="height", sex="boys", age=6, value=40)
    assert body["available"] is True
    assert body["out_of_reference_range"] is True
    assert body["z"] == Z_REPORTABLE_MIN
    assert body["z"] >= -5.0, "a clamped z must not still read as -12.9"


def test_absurd_weight_is_flagged(client):
    body = _point(client, measure="weight", sex="girls", age=10, value=400)
    assert body["out_of_reference_range"] is True
    assert body["z"] == Z_REPORTABLE_MAX


@pytest.mark.parametrize("measure,sex,age,value", [
    ("height", "boys", 6, 112.0),
    ("height", "girls", 10, 138.0),
    ("weight", "boys", 10, 30.0),
    ("bmi", "girls", 12, 17.0),
])
def test_ordinary_measurements_are_not_flagged(client, measure, sex, age, value):
    """Guard against over-clamping: a normal child must be unaffected."""
    body = _point(client, measure=measure, sex=sex, age=age, value=value)
    assert body["out_of_reference_range"] is False
    assert Z_REPORTABLE_MIN < body["z"] < Z_REPORTABLE_MAX


def test_genuine_extremes_are_still_reportable(client):
    """-5/+5 is deliberately wide: severe malnutrition really does reach -4 SD
    and must stay a reportable finding, not be swallowed as 'out of range'."""
    from backend.growth import iap_reference as iap
    from backend.growth.lms_core import lms_value_at_z

    l, m, s = iap._SERIES[("boys", "weight")].lms_at(10.0)
    value = lms_value_at_z(l, m, s, -4.0)
    body = _point(client, measure="weight", sex="boys", age=10, value=value)
    assert body["out_of_reference_range"] is False
    assert body["z"] < -3.5


def test_response_advertises_the_range(client):
    body = _point(client, measure="height", sex="boys", age=6, value=112.0)
    assert body["z_reportable_range"] == [Z_REPORTABLE_MIN, Z_REPORTABLE_MAX]


def test_percentile_is_derived_from_the_clamped_z(client):
    """The percentile must agree with the z actually reported, or the two fields
    contradict each other on exactly the rows a reader would scrutinise."""
    body = _point(client, measure="height", sex="boys", age=6, value=40)
    assert body["percentile"] == 0.1     # floor, consistent with z = -5

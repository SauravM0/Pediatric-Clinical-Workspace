"""QRISK3-2017 validation (audit F-3).

Four kinds of check:
  1. authoritative coefficient parity -- key constants equal the ClinRisk/CRAN
     QRISK3 values (verified against the CRAN `QRISK3` package);
  2. single source -- the frontend's inline coefficients equal the backend's, so
     the two implementations can never silently diverge;
  3. clinical direction -- each risk factor moves the score the documented way
     (the CRAN test-dataset philosophy: one factor at a time);
  4. eligibility + imputation -- outside 25-84 or without BMI there is NO score,
     and every defaulted input is reported.
"""
import os
import re
import tempfile
from pathlib import Path

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "cvd_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.cvd import qrisk3
from backend.cvd.qrisk3 import FEMALE, MALE
from backend.server import app

# M6: the app moved out of index.html into frontend/src/.
from _frontend_source import frontend_source

_BASE = dict(sex="female", age=60, bmi=28, ethnicity=1, smoke=0, diabetes=0,
             cholesterol_ratio=4.5, systolic_bp=135)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── 1. authoritative parity (vs ClinRisk / CRAN QRISK3) ──────────────────────

def test_survivor_constants_match_clinrisk():
    assert FEMALE["survivor"] == 0.988876402378082
    assert MALE["survivor"] == 0.977268040180206


def test_key_female_coefficients_match_clinrisk():
    assert FEMALE["c"]["age1"] == -8.1388109247726188
    assert FEMALE["c"]["age2"] == 0.7973337668969910
    assert FEMALE["c"]["bmi1"] == 0.2923609227546005
    assert FEMALE["c"]["type1"] == 1.7267977510537347
    assert FEMALE["c"]["type2"] == 1.0688773244615468
    assert FEMALE["Ismoke"] == [0, 0.1338683378654626, 0.5620085801243854,
                                0.6674959337750255, 0.8494817764483085]


# ── 2. single source: frontend inline coefficients == backend ────────────────

def _flatten(M) -> list[float]:
    out = [M["survivor"], *M["Iethrisk"], *M["Ismoke"]]
    for k in ("c", "i1", "i2", "center"):
        out += list(M[k].values())
    return [float(v) for v in out if isinstance(v, float) and v != 0.0]


def _frontend_decimals(start: str, end: str) -> list[float]:
    src = frontend_source()
    i = src.index(start)
    j = src.index(end, i)
    return sorted(float(x) for x in re.findall(r"-?\d+\.\d+", src[i:j]))


@pytest.mark.parametrize("M,start,end", [
    (FEMALE, "const QRISK3_FEMALE = {", "const QRISK3_MALE"),
    (MALE, "const QRISK3_MALE = {", "// p = patient object"),
])
def test_frontend_and_backend_coefficients_are_identical(M, start, end):
    backend_nums = sorted(_flatten(M))
    frontend_nums = _frontend_decimals(start, end)
    assert len(backend_nums) == len(frontend_nums), "coefficient count drifted"
    for a, b in zip(backend_nums, frontend_nums):
        assert a == pytest.approx(b, abs=1e-12), "a coefficient drifted frontend<->backend"


# ── 3. clinical direction (one factor at a time) ─────────────────────────────

def _risk(**over):
    return qrisk3({**_BASE, **over})["risk_percent"]


def test_risk_is_a_valid_percentage():
    assert 0.0 <= _risk() <= 100.0


@pytest.mark.parametrize("field,value", [
    ("age", 72), ("smoke", 4), ("diabetes", 2), ("systolic_bp", 170),
    ("cholesterol_ratio", 7.0), ("AF", True), ("ra", True), ("treatedhyp", True),
])
def test_each_risk_factor_increases_risk(field, value):
    assert _risk(**{field: value}) > _risk()


def test_men_have_higher_baseline_than_women():
    assert _risk(sex="male") > _risk()


# ── 4. eligibility + imputation ──────────────────────────────────────────────

@pytest.mark.parametrize("age", [10, 24, 85, 90])
def test_outside_adult_range_returns_no_score(age):
    r = qrisk3({**_BASE, "age": age})
    assert r["available"] is False and r.get("eligible") is False
    assert "risk_percent" not in r


def test_missing_bmi_returns_no_score():
    r = qrisk3({"sex": "male", "age": 50})
    assert r["available"] is False and "risk_percent" not in r


def test_bmi_computed_from_height_weight():
    r = qrisk3({"sex": "male", "age": 50, "height_cm": 175, "weight_kg": 80,
                "cholesterol_ratio": 4.0, "systolic_bp": 125})
    assert r["available"] is True and r["risk_percent"] >= 0


def test_defaulted_inputs_are_reported():
    r = qrisk3({"sex": "male", "age": 50, "bmi": 26})
    assert set(r["imputed_fields"]) == {"cholesterol_ratio", "systolic_bp", "sbp_sd", "townsend"}
    full = qrisk3({**_BASE, "sbp_sd": 8.0, "townsend": 0.0})
    assert full["imputed_fields"] == []


# ── endpoint ─────────────────────────────────────────────────────────────────

def test_endpoint_returns_risk(client):
    r = client.post("/api/cvd/qrisk3", json=_BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True and 0 <= body["risk_percent"] <= 100
    assert "imputed_fields" in body


def test_endpoint_enforces_adult_eligibility(client):
    r = client.post("/api/cvd/qrisk3", json={**_BASE, "age": 15})
    assert r.status_code == 200
    assert r.json()["available"] is False

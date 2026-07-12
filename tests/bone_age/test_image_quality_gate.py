"""Image acceptability gate for the AI screening estimate (directive S-BA-6).

validation_protocol.md §4: "Do not silently generate a normal report after a
quality failure." A HARD quality flag (fracture, cast, wrong laterality,
clipped/too-small anatomy...) -- whether clinician-declared or auto-detected --
must make the whole-hand estimate ABSTAIN before the model ever runs.
"""
import io
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "iqg_test.db"))

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import imaging
from backend.imaging import LoadedImage, auto_quality_flags, gate_ai_estimate
from backend.server import app

_STARTER = Path(__file__).resolve().parents[2] / "bone_age_product_starter_pack" / "case_input_schema.json"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _png(w: int, h: int, seed: int = 0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(h, w), dtype=np.uint8)  # high contrast, not blank
    buf = io.BytesIO()
    Image.fromarray(arr, mode="L").save(buf, format="PNG")
    return buf.getvalue()


def _loaded(w: int, h: int, laterality=None) -> LoadedImage:
    arr = np.random.default_rng(1).integers(0, 256, size=(h, w), dtype=np.uint8)
    return LoadedImage(analysis=arr, width=w, height=h, bit_depth=8,
                       source_format="PNG", laterality=laterality)


# ── vocabulary is tied to the product contract ──────────────────────────────

def test_canonical_flags_match_the_starter_pack_contract():
    schema = json.loads(_STARTER.read_text(encoding="utf-8"))
    contract = set(schema["properties"]["quality_flags"]["items"]["enum"])
    assert imaging.CANONICAL_QUALITY_FLAGS == contract, (
        "quality-flag vocabulary drifted from case_input_schema.json"
    )
    assert imaging.HARD_QUALITY_FLAGS <= imaging.CANONICAL_QUALITY_FLAGS


# ── auto detection (only what's reliable) ───────────────────────────────────

def test_auto_flags_catch_too_small_and_wrong_laterality():
    flags, _ = auto_quality_flags(_loaded(50, 50))
    assert "IMAGE_TOO_SMALL" in flags
    flags2, _ = auto_quality_flags(_loaded(400, 400, laterality="R"))
    assert "WRONG_LATERALITY" in flags2


def test_auto_flags_clean_image_has_none():
    flags, notes = auto_quality_flags(_loaded(400, 400))
    assert flags == []


# ── gate logic ──────────────────────────────────────────────────────────────

def test_declared_hard_flag_blocks():
    q = gate_ai_estimate([], ["FRACTURE"])
    assert q["accepted"] is False and "FRACTURE" in q["hard_flags"]
    assert q["reason_for_rejection"]


def test_declared_soft_flag_is_accepted_but_recorded():
    q = gate_ai_estimate([], ["rotation"])  # case-insensitive
    assert q["accepted"] is True and q["soft_flags"] == ["ROTATION"]


def test_unknown_declared_flag_is_recorded_not_gating():
    q = gate_ai_estimate([], ["MADE_UP"])
    assert q["accepted"] is True and q["unknown_declared"] == ["MADE_UP"]


# ── endpoint abstains before inference ──────────────────────────────────────

def test_endpoint_abstains_on_declared_fracture(client):
    r = client.post("/api/bone-age/estimate",
                    data={"sex": "boys", "declared_flags": "FRACTURE"},
                    files={"file": ("hand.png", _png(400, 400), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False and body["accepted"] is False
    assert "bone_age_months" not in body  # no silent age emitted
    assert "FRACTURE" in body["quality"]["hard_flags"]


def test_endpoint_abstains_on_too_small_image(client):
    r = client.post("/api/bone-age/estimate",
                    data={"sex": "girls"},
                    files={"file": ("tiny.png", _png(60, 60), "image/png")})
    body = r.json()
    assert body["available"] is False and body["accepted"] is False
    assert "IMAGE_TOO_SMALL" in body["quality"]["hard_flags"]


def test_endpoint_accepts_a_clean_image(client):
    r = client.post("/api/bone-age/estimate",
                    data={"sex": "boys"},
                    files={"file": ("hand.png", _png(400, 400), "image/png")})
    body = r.json()
    # gate passes; whether an age is returned depends only on model presence,
    # never on the quality gate.
    assert body["quality"]["accepted"] is True
    if body["available"] is False:
        assert "model" in body["message"].lower()

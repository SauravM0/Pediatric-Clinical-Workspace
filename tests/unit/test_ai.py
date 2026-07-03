"""AI screening estimate tests (directive §17, §28).

The trained model is a gitignored local artifact, so these tests adapt to whether
it is present: they always check honest degradation, and check a real estimate
only when the model exists.
"""

from __future__ import annotations

import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from backend.ai import boneage
from backend.server import app

client = TestClient(app)


def _png() -> bytes:
    arr = (np.random.default_rng(0).integers(0, 255, size=(200, 160))).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, mode="L").save(buf, format="PNG")
    return buf.getvalue()


def test_config_reports_ai_flag() -> None:
    cfg = client.get("/api/bone-age/config").json()
    assert "ai_estimate_available" in cfg
    assert cfg["ai_estimate_available"] == boneage.model_available()


def test_estimate_rejects_bad_sex() -> None:
    r = client.post("/api/bone-age/estimate",
                    data={"sex": "x"}, files={"file": ("h.png", _png(), "image/png")})
    assert r.status_code == 422


def test_estimate_behaviour_matches_model_presence() -> None:
    r = client.post("/api/bone-age/estimate",
                    data={"sex": "girls"}, files={"file": ("h.png", _png(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    if boneage.model_available():
        assert body["available"] is True
        assert 0 <= body["bone_age_months"] <= 240
        assert "not TW3" in body["method"]
    else:
        assert body["available"] is False


def test_estimate_empty_upload_rejected() -> None:
    r = client.post("/api/bone-age/estimate",
                    data={"sex": "girls"}, files={"file": ("h.png", b"", "image/png")})
    assert r.status_code == 422

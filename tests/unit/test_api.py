"""Bone-age API bridge tests (directive §25.3)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.server import app
from backend.tw3 import RUS_BONES

client = TestClient(app)


def test_config_lists_13_bones_with_grades() -> None:
    cfg = client.get("/api/bone-age/config").json()
    assert cfg["method"] == "TW3-C-RUS"
    assert [b["code"] for b in cfg["bones"]] == list(RUS_BONES)
    stages = {b["code"]: b["stages"] for b in cfg["bones"]}
    assert stages["radius"] == ["1", "2", "3", "4", "5", "6", "7", "8"]
    assert stages["ulna"] == ["1", "2", "3", "4", "5", "6", "7"]  # ulna has no grade 8


def test_score_full_grading_returns_bone_age() -> None:
    stages = dict(radius="8", ulna="7", mc1="7", mc3="7", mc5="6", pp1="7",
                  pp3="7", pp5="7", mp3="7", mp5="7", dp1="7", dp3="7", dp5="7")
    r = client.post("/api/bone-age/score", json={"sex": "girls", "stages": stages}).json()
    assert r["total_rus_score"] == 880.0
    assert r["complete"] is True
    assert r["bone_age_years"] is not None
    assert r["provisional_curve"] is True


def test_score_partial_withholds_age() -> None:
    r = client.post("/api/bone-age/score",
                    json={"sex": "girls", "stages": {"radius": "8"}}).json()
    assert r["staged_count"] == 1
    assert r["bone_age_months"] is None
    assert r["complete"] is False


def test_score_rejects_bad_sex_and_stage() -> None:
    assert client.post("/api/bone-age/score",
                       json={"sex": "x", "stages": {}}).status_code == 422
    assert client.post("/api/bone-age/score",
                       json={"sex": "girls", "stages": {"radius": "Z"}}).status_code == 422

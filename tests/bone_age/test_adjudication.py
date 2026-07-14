"""Adjudication queue (Plan 2 WI-4).

Disputed per-bone stages across independent reads are queued for a senior read,
never silently averaged; resolving is audited; refresh is idempotent; resolved
labels take precedence. Headless via FastAPI TestClient on a throwaway DB.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "adjud_test.db"))

import pytest
from fastapi.testclient import TestClient

from backend.db import init_db, session_scope
from backend.server import app
from backend.tw3 import adjudication

# Three raters on one film: radius unanimous (F), ulna majority (E), mc1 3-way tie.
_FILMS = [
    {"film_key": "film-1", "stage_system": "tw3-letters", "stages": {"radius": "F", "ulna": "E", "mc1": "D"}},
    {"film_key": "film-1", "stage_system": "tw3-letters", "stages": {"radius": "F", "ulna": "E", "mc1": "E"}},
    {"film_key": "film-1", "stage_system": "tw3-letters", "stages": {"radius": "F", "ulna": "F", "mc1": "F"}},
]


@pytest.fixture(scope="module")
def client():
    init_db()
    return TestClient(app)


def test_refresh_opens_item_only_for_the_disputed_bone(client):
    r = client.post("/api/bone-age/adjudication/refresh", json={"films": _FILMS})
    assert r.status_code == 200
    summary = r.json()
    assert summary["groups"] == 1
    # radius (unanimous) and ulna (2/3 majority) are decided; only mc1 (tie) is queued.
    assert summary["opened"] == 1

    listing = client.get("/api/bone-age/adjudication", params={"status": "open"}).json()
    bones = [i["bone_code"] for i in listing["items"]]
    assert "mc1" in bones and "radius" not in bones and "ulna" not in bones
    mc1 = next(i for i in listing["items"] if i["bone_code"] == "mc1")
    assert mc1["n_readers"] == 3 and mc1["votes"] == {"D": 1, "E": 1, "F": 1}


def test_refresh_is_idempotent(client):
    before = client.get("/api/bone-age/adjudication", params={"status": "open"}).json()["count"]
    client.post("/api/bone-age/adjudication/refresh", json={"films": _FILMS})
    after = client.get("/api/bone-age/adjudication", params={"status": "open"}).json()["count"]
    assert after == before   # no duplicate open item for mc1


def test_resolve_closes_item_and_records_label(client):
    item_id = next(i["id"] for i in
                   client.get("/api/bone-age/adjudication", params={"status": "open"}).json()["items"]
                   if i["bone_code"] == "mc1")
    r = client.post(f"/api/bone-age/adjudication/{item_id}/resolve",
                    json={"resolved_stage": "E", "resolved_by": "Dr Senior", "reason": "closest to atlas"})
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    assert r.json()["resolved_stage"] == "E"

    # resolved label takes precedence and is retrievable
    with session_scope() as db:
        labels = adjudication.consensus_labels(db, "film-1", "tw3-letters")
        assert labels.get("mc1") == "E"

    # a second resolve on the same item is refused
    assert client.post(f"/api/bone-age/adjudication/{item_id}/resolve",
                       json={"resolved_stage": "F", "resolved_by": "X"}).status_code == 422


def test_invalid_stage_is_refused(client):
    client.post("/api/bone-age/adjudication/refresh", json={"films": [
        {"film_key": "film-2", "stage_system": "tw3-letters", "stages": {"ulna": "A"}},
        {"film_key": "film-2", "stage_system": "tw3-letters", "stages": {"ulna": "C"}},
    ]})
    item_id = next(i["id"] for i in
                   client.get("/api/bone-age/adjudication", params={"status": "open"}).json()["items"]
                   if i["film_key"] == "film-2")
    bad = client.post(f"/api/bone-age/adjudication/{item_id}/resolve",
                      json={"resolved_stage": "Z", "resolved_by": "Dr Senior"})
    assert bad.status_code == 422

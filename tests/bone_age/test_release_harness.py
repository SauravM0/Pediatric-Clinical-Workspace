"""Gated release harness (Plan 2 WI-7).

Proves the safety core: a candidate deploys ONLY when the Plan 5 gate passes AND a
human signs off; a failing gate is rejected (never deployed) even with a signature;
a passing gate without sign-off stays a candidate. Every decision is persisted to
the ModelRelease audit table. Uses a throwaway SQLite DB.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "release_test.db"))

import json

import pytest

from backend.ai.release import (CANDIDATE, DEPLOYED, REJECTED, decide_from_spec,
                                decide_release, main, record_release)
from backend.db import init_db, session_scope
from backend.models import ModelRelease


@pytest.fixture(scope="module", autouse=True)
def _db():
    init_db()


_TARGETS = [60, 72, 84, 96, 108, 120]
_INCUMBENT = [t + 8 for t in _TARGETS]      # ~8 mo error
_CANDIDATE_WIN = [t + 2 for t in _TARGETS]  # ~2 mo error -> clearly better, gates pass


def test_passing_gate_with_signoff_deploys_and_persists():
    d = decide_release(model_kind="screening", version="v2", dataset="rsna",
                       targets=_TARGETS, candidate_preds=_CANDIDATE_WIN,
                       incumbent_preds=_INCUMBENT, incumbent_version="v1",
                       min_improvement_months=0.3, signed_off_by="Dr Rao")
    assert d.status == DEPLOYED
    assert d.verdict.passed is True
    assert d.model_card["intended_use"].startswith("clinician-assist")
    with session_scope() as db:
        row = record_release(db, d, model_kind="screening", version="v2",
                             incumbent_version="v1", signed_off_by="Dr Rao")
        assert row.status == DEPLOYED
        assert row.verdict_passed is True and row.beat_incumbent is True
        assert row.signed_off_by == "Dr Rao" and row.signed_off_at is not None


def test_passing_gate_without_signoff_stays_candidate():
    d = decide_release(model_kind="screening", version="v2", dataset="rsna",
                       targets=_TARGETS, candidate_preds=_CANDIDATE_WIN,
                       incumbent_preds=_INCUMBENT, min_improvement_months=0.3)
    assert d.status == CANDIDATE
    with session_scope() as db:
        row = record_release(db, d, model_kind="screening", version="v2")
        assert row.status == CANDIDATE and row.signed_off_at is None


def test_gate_breach_is_rejected_even_with_signoff():
    # candidate beats a terrible incumbent but MAE 10 > 6mo gate -> gate fails.
    incumbent_bad = [t + 30 for t in _TARGETS]
    candidate_meh = [t + 10 for t in _TARGETS]
    d = decide_release(model_kind="screening", version="v2", dataset="rsna",
                       targets=_TARGETS, candidate_preds=candidate_meh,
                       incumbent_preds=incumbent_bad, signed_off_by="Dr Rao")
    assert d.verdict.passed is False and d.status == REJECTED
    with session_scope() as db:
        row = record_release(db, d, model_kind="screening", version="v2",
                             signed_off_by="Dr Rao")
        assert row.status == REJECTED
        assert row.signed_off_by is None and row.signed_off_at is None   # never signed a reject


def test_subgroup_regression_is_rejected():
    groups = ["boys", "boys", "boys", "girls", "girls", "girls"]
    incumbent = [t + 3 for t in _TARGETS]
    candidate = [_TARGETS[0], _TARGETS[1], _TARGETS[2],
                 _TARGETS[3] + 15, _TARGETS[4] + 15, _TARGETS[5] + 15]  # girls much worse
    d = decide_release(model_kind="screening", version="v2", dataset="rsna",
                       targets=_TARGETS, candidate_preds=candidate,
                       incumbent_preds=incumbent, groups=groups, signed_off_by="Dr Rao")
    assert d.status == REJECTED
    assert any("FAIL no-subgroup-regression" in r for r in d.verdict.reasons)


def test_unknown_kind_raises():
    with pytest.raises(ValueError):
        decide_release(model_kind="magic", version="v", dataset="d",
                       targets=_TARGETS, candidate_preds=_CANDIDATE_WIN)


# ── CLI entrypoint (PLAN-0 A1) — the harness consumes an evaluation artifact ──

def _spec(**over) -> dict:
    base = {"model_kind": "screening", "version": "v2", "dataset": "rsna-locked-test",
            "incumbent_version": "v1", "targets": _TARGETS,
            "candidate_preds": _CANDIDATE_WIN, "incumbent_preds": _INCUMBENT,
            "min_improvement_months": 0.3}
    base.update(over)
    return base


def test_decide_from_spec_requires_core_fields():
    with pytest.raises(ValueError):
        decide_from_spec({"model_kind": "screening"})  # missing targets/candidate_preds/...


def test_cli_signed_off_winner_deploys_writes_card_and_records(tmp_path):
    preds = tmp_path / "preds.json"
    preds.write_text(json.dumps(_spec(version="v2cli")), encoding="utf-8")
    card = tmp_path / "card.json"

    rc = main([str(preds), "--sign-off", "Dr Rao", "--card-out", str(card)])

    assert rc == 0
    assert card.exists()
    saved = json.loads(card.read_text(encoding="utf-8"))
    assert saved["gate_passed"] is True and saved["version"] == "v2cli"
    with session_scope() as db:
        row = db.query(ModelRelease).filter_by(version="v2cli", status=DEPLOYED).first()
        assert row is not None and row.signed_off_by == "Dr Rao"
        assert row.model_card_path == str(card)


def test_cli_no_signoff_stays_candidate_never_auto_promotes(tmp_path):
    preds = tmp_path / "preds.json"
    preds.write_text(json.dumps(_spec(version="v3")), encoding="utf-8")

    rc = main([str(preds), "--card-out", str(tmp_path / "c.json")])

    assert rc == 0   # passed the gate, but no sign-off => candidate, not deployed
    with session_scope() as db:
        row = db.query(ModelRelease).filter_by(version="v3").first()
        assert row.status == CANDIDATE and row.signed_off_at is None


def test_cli_gate_breach_rejects_and_exits_nonzero(tmp_path):
    # candidate MAE ~10mo > 6mo engineering gate -> rejected regardless of sign-off.
    breach = _spec(version="v4", incumbent_preds=[t + 30 for t in _TARGETS],
                   candidate_preds=[t + 10 for t in _TARGETS])
    preds = tmp_path / "preds.json"
    preds.write_text(json.dumps(breach), encoding="utf-8")

    rc = main([str(preds), "--sign-off", "Dr Rao", "--card-out", str(tmp_path / "c.json")])

    assert rc == 1
    with session_scope() as db:
        row = db.query(ModelRelease).filter_by(version="v4").first()
        assert row.status == REJECTED and row.signed_off_by is None


def test_cli_dry_run_writes_card_but_does_not_record(tmp_path):
    preds = tmp_path / "preds.json"
    preds.write_text(json.dumps(_spec(version="v5")), encoding="utf-8")
    card = tmp_path / "c.json"

    rc = main([str(preds), "--sign-off", "Dr Rao", "--dry-run", "--card-out", str(card)])

    assert rc == 0 and card.exists()
    with session_scope() as db:
        assert db.query(ModelRelease).filter_by(version="v5").first() is None


def test_releases_endpoint_lists_recorded_decisions(tmp_path):
    from fastapi.testclient import TestClient
    from backend.server import app

    # record one via the CLI, then read it back through the audit endpoint.
    preds = tmp_path / "preds.json"
    preds.write_text(json.dumps(_spec(version="v6")), encoding="utf-8")
    main([str(preds), "--sign-off", "Dr Rao", "--card-out", str(tmp_path / "c.json")])

    body = TestClient(app).get("/api/bone-age/releases").json()
    assert body["count"] >= 1
    versions = {r["version"] for r in body["releases"]}
    assert "v6" in versions
    v6 = next(r for r in body["releases"] if r["version"] == "v6")
    assert v6["status"] == DEPLOYED and v6["verdict_passed"] is True

"""Gated release harness (Plan 2 WI-7).

Proves the safety core: a candidate deploys ONLY when the Plan 5 gate passes AND a
human signs off; a failing gate is rejected (never deployed) even with a signature;
a passing gate without sign-off stays a candidate. Every decision is persisted to
the ModelRelease audit table. Uses a throwaway SQLite DB.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "release_test.db"))

import pytest

from backend.ai.release import CANDIDATE, DEPLOYED, REJECTED, decide_release, record_release
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

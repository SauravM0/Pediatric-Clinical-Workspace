"""Deterministic TW3-RUS scoring engine tests (directive §25.1).

Reference cases (score→age) use the centre's own verified values. The stage→score
maths is tested with a small synthetic calibrated fixture so the logic is proven
without depending on the (separately reconstructed) production point table.
"""

from __future__ import annotations

import pytest

from backend.tw3 import (
    RUS_BONES,
    RUS_BONE_COUNT,
    ScoringError,
    calculate_strict,
    compute,
    load_tables,
    score_to_age,
)
from backend.tw3.tables import ScoringTables


def _fixture_tables() -> ScoringTables:
    """A fully-calibrated synthetic table: boys and girls differ so we can prove
    sex-specific selection. Every bone at grade '6'=5 (boys) / 10 (girls),
    '7'=10/20, '8'=15/30. score_to_age is a simple linear curve."""
    boys = {b: {"6": 5, "7": 10, "8": 15} for b in RUS_BONES}
    girls = {b: {"6": 10, "7": 20, "8": 30} for b in RUS_BONES}
    return ScoringTables(
        method="TW3-C-RUS-test",
        version="test-1",
        source_reference="synthetic",
        stage_to_score={"boys": boys, "girls": girls},
        score_to_age={
            "boys": [[0, 2.0], [130, 15.0]],
            "girls": [[0, 2.0], [260, 15.0]],
        },
        allowed_stages={b: ("6", "7", "8") for b in RUS_BONES},
        min_age_years=0.0,
        max_age_years=19.0,
        checksum_verified=True,
    )


def test_all_thirteen_bones() -> None:
    assert RUS_BONE_COUNT == 13
    assert len(set(RUS_BONES)) == 13


def test_unknown_bone_rejected() -> None:
    t = _fixture_tables()
    stages = {b: "G" for b in RUS_BONES}
    stages["not_a_bone"] = "G"
    with pytest.raises(ScoringError):
        compute(stages, "girls", t)


def test_invalid_stage_rejected() -> None:
    t = _fixture_tables()
    stages = {b: "7" for b in RUS_BONES}
    stages["radius"] = "Z"
    with pytest.raises(ScoringError):
        compute(stages, "girls", t)


def test_unsupported_sex_rejected() -> None:
    t = _fixture_tables()
    with pytest.raises(ScoringError):
        compute({b: "7" for b in RUS_BONES}, "other", t)


def test_male_scores_selected() -> None:
    t = _fixture_tables()
    r = compute({b: "7" for b in RUS_BONES}, "boys", t)
    assert r.total_rus_score == 13 * 10  # boys grade 7 = 10
    assert r.complete and r.calibrated


def test_female_scores_selected() -> None:
    t = _fixture_tables()
    r = compute({b: "7" for b in RUS_BONES}, "girls", t)
    assert r.total_rus_score == 13 * 20  # girls grade 7 = 20


def test_total_and_mixed_stages() -> None:
    t = _fixture_tables()
    stages = {b: "7" for b in RUS_BONES}
    stages["radius"] = "8"  # +30 instead of +20
    stages["mc5"] = "6"     # +10 instead of +20
    r = compute(stages, "girls", t)
    assert r.total_rus_score == (11 * 20) + 30 + 10


def test_incomplete_rejected_by_strict() -> None:
    t = _fixture_tables()
    stages = {b: "7" for b in RUS_BONES}
    del stages["dp5"]  # only 12 of 13
    with pytest.raises(ScoringError):
        calculate_strict(stages, "girls", t)


def test_missing_score_reported_not_guessed() -> None:
    t = _fixture_tables()
    # grade '1' is a valid vocabulary stage but absent from the fixture score rows.
    stages = {b: "7" for b in RUS_BONES}
    stages["radius"] = "1"
    r = compute(stages, "girls", t)
    assert "radius" in r.missing_score
    assert r.bone_age_months is None  # withheld, never guessed


def test_determinism() -> None:
    t = _fixture_tables()
    stages = {b: "8" for b in RUS_BONES}
    r1 = calculate_strict(stages, "boys", t)
    r2 = calculate_strict(stages, "boys", t)
    assert r1.total_rus_score == r2.total_rus_score
    assert r1.bone_age_months == r2.bone_age_months


def test_score_to_age_boundaries_and_interp() -> None:
    t = _fixture_tables()
    # below first / above last anchor clamp to endpoints (terminal behaviour)
    assert score_to_age(-100, "girls", t) == 2.0
    assert score_to_age(9999, "girls", t) == 15.0
    # midpoint interpolation: girls curve [0,2]..[260,15]; at 130 -> 8.5y
    assert score_to_age(130, "girls", t) == pytest.approx(8.5, abs=0.01)


# ── Production TW3-C table checks (directive §25.1) ───────────────────────────

def test_production_max_grade_totals_1000() -> None:
    """Transcription invariant: TW3-C RUS is normalised so the maximum grade of
    every bone sums to exactly 1000, for both sexes. Guards against a mis-typed
    point value in the production table."""
    t = load_tables()
    for sex in ("boys", "girls"):
        highest = {b: max(rows) for b, rows in t.stage_to_score[sex].items()}
        total = sum(t.stage_to_score[sex][b][g] for b, g in highest.items())
        assert total == 1000, f"{sex} max-grade total is {total}, expected 1000"


def test_production_full_grading_produces_bone_age() -> None:
    """A fully graded TW3-C assessment yields a bone age within the curve range."""
    t = load_tables()
    r = compute({b: "5" for b in RUS_BONES}, "girls", t)
    assert r.complete and r.calibrated
    assert r.bone_age_months is not None
    assert t.min_age_years * 12 <= r.bone_age_months <= t.max_age_years * 12


def test_production_table_calibrated() -> None:
    t = load_tables()
    assert t.is_calibrated("girls") and t.is_calibrated("boys")
    assert t.checksum_verified  # integrity guard is active

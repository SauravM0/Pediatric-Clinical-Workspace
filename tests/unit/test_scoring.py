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
    sex-specific selection. Every bone at stage 'G'=10 (boys) / 20 (girls),
    'H'=15/30, 'F'=5/10. score_to_age is a simple linear curve."""
    boys = {b: {"F": 5, "G": 10, "H": 15} for b in RUS_BONES}
    girls = {b: {"F": 10, "G": 20, "H": 30} for b in RUS_BONES}
    return ScoringTables(
        method="TW3-RUS-test",
        version="test-1",
        source_reference="synthetic",
        stage_to_score={"boys": boys, "girls": girls},
        score_to_age={
            "boys": [[0, 2.0], [130, 15.0]],
            "girls": [[0, 2.0], [260, 15.0]],
        },
        allowed_stages={b: ("F", "G", "H") for b in RUS_BONES},
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
    stages = {b: "G" for b in RUS_BONES}
    stages["radius"] = "Z"
    with pytest.raises(ScoringError):
        compute(stages, "girls", t)


def test_unsupported_sex_rejected() -> None:
    t = _fixture_tables()
    with pytest.raises(ScoringError):
        compute({b: "G" for b in RUS_BONES}, "other", t)


def test_male_scores_selected() -> None:
    t = _fixture_tables()
    r = compute({b: "G" for b in RUS_BONES}, "boys", t)
    assert r.total_rus_score == 13 * 10  # boys G = 10
    assert r.complete and r.calibrated


def test_female_scores_selected() -> None:
    t = _fixture_tables()
    r = compute({b: "G" for b in RUS_BONES}, "girls", t)
    assert r.total_rus_score == 13 * 20  # girls G = 20


def test_total_and_mixed_stages() -> None:
    t = _fixture_tables()
    stages = {b: "G" for b in RUS_BONES}
    stages["radius"] = "H"  # +30 instead of +20
    stages["mc5"] = "F"     # +10 instead of +20
    r = compute(stages, "girls", t)
    assert r.total_rus_score == (11 * 20) + 30 + 10


def test_incomplete_rejected_by_strict() -> None:
    t = _fixture_tables()
    stages = {b: "G" for b in RUS_BONES}
    del stages["dp5"]  # only 12 of 13
    with pytest.raises(ScoringError):
        calculate_strict(stages, "girls", t)


def test_missing_score_reported_not_guessed() -> None:
    t = _fixture_tables()
    # 'A' is a valid vocabulary stage but absent from the fixture score rows.
    stages = {b: "G" for b in RUS_BONES}
    stages["radius"] = "A"
    r = compute(stages, "girls", t)
    assert "radius" in r.missing_score
    assert r.bone_age_months is None  # withheld, never guessed


def test_determinism() -> None:
    t = _fixture_tables()
    stages = {b: "H" for b in RUS_BONES}
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


# ── Reference cases: the centre's own verified score→age anchors ───────────────

@pytest.mark.parametrize("score,expected_years", [(681, 12.1), (713, 12.4)])
def test_reference_cases_score_to_age(score: float, expected_years: float) -> None:
    """Directive §25.1: known reference cases must reproduce the expected bone age.
    These two girls anchors come from the centre's own reports."""
    t = load_tables()
    got = score_to_age(score, "girls", t)
    assert got is not None
    assert got == pytest.approx(expected_years, abs=0.05)


def test_production_table_never_guesses_when_uncalibrated() -> None:
    """Until the stage→score table is reconstructed, the engine must withhold a
    bone age rather than fabricate one."""
    t = load_tables()
    if t.is_calibrated("girls"):
        pytest.skip("production table is calibrated; guess-guard not applicable")
    r = compute({b: "G" for b in RUS_BONES}, "girls", t)
    assert r.bone_age_months is None
    assert not r.complete

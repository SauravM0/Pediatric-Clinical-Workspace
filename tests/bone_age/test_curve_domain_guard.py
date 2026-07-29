"""Score-to-age curve domain guard (M3.1).

The TW3-C curve is defined over score 150-1000 (boys) / 270-1000 (girls).
``_interp_months`` used to CLAMP anything outside that to the nearest endpoint,
so scores of 50, 100 and 150 all returned exactly 6.00y with nothing in the
output distinguishing a clamp from a computation -- the product was least
reliable precisely where it looked most confident. An all-grade-1 boy really
does score below the curve (RUS 96), so this was reachable, not theoretical.

It now withholds and explains, matching the engine's contract everywhere else.
"""
import pytest

from backend.tw3 import scoring, tables
from backend.tw3.constants import RUS_BONES

_ANCHORS = [[150.0, 6.0], [500.0, 12.0], [1000.0, 16.0]]


@pytest.fixture(scope="module")
def t():
    return tables.load_tables()


# ── the primitive ───────────────────────────────────────────────────────────

def test_below_domain_is_withheld_not_clamped():
    for score in (0, 50, 100, 149, 149.999):
        months, status = scoring._interp_months(_ANCHORS, score)
        assert months is None, f"score {score} produced an age instead of withholding"
        assert status == scoring.CURVE_BELOW_DOMAIN


def test_above_domain_is_withheld_not_clamped():
    for score in (1000.001, 1001, 5000):
        months, status = scoring._interp_months(_ANCHORS, score)
        assert months is None
        assert status == scoring.CURVE_ABOVE_DOMAIN


def test_endpoints_are_inside_the_domain():
    """`<` / `>`, not `<=` / `>=`. A maximum-grade assessment legitimately totals
    exactly 1000 -- the curve's last anchor -- and must still score."""
    lo_months, lo_status = scoring._interp_months(_ANCHORS, 150)
    hi_months, hi_status = scoring._interp_months(_ANCHORS, 1000)
    assert (lo_months, lo_status) == (72, scoring.CURVE_OK)     # 6.0y
    assert (hi_months, hi_status) == (192, scoring.CURVE_OK)    # 16.0y


def test_interpolation_is_unchanged_inside_the_domain():
    months, status = scoring._interp_months(_ANCHORS, 325)      # midway 150->500
    assert status == scoring.CURVE_OK
    assert months == round((6.0 + (325 - 150) / 350 * 6.0) * 12)


def test_uncalibrated_curve_is_distinguishable_from_out_of_domain():
    """Two different clinical messages: 'this centre has not entered the tables'
    vs 'this score is off the end of the curve'."""
    months, status = scoring._interp_months([], 500)
    assert months is None and status == scoring.CURVE_UNCALIBRATED
    months, status = scoring._interp_months([[150.0, 6.0]], 500)   # <2 anchors
    assert months is None and status == scoring.CURVE_UNCALIBRATED


def test_curve_domain_reports_the_real_bounds(t):
    assert scoring.curve_domain(_ANCHORS) == (150.0, 1000.0)
    assert scoring.curve_domain([]) is None
    assert scoring.curve_domain([[1.0, 2.0]]) is None
    assert scoring.curve_domain(t.score_to_age["boys"]) == (150.0, 1000.0)
    assert scoring.curve_domain(t.score_to_age["girls"]) == (270.0, 1000.0)


# ── end to end through compute() ────────────────────────────────────────────

def test_all_grade_1_withholds_instead_of_reporting_six_years(t):
    """The concrete regression: previously reported 6.00y for a score of 96."""
    for sex in ("boys", "girls"):
        r = scoring.compute({b: "1" for b in RUS_BONES}, sex, t)
        assert r.complete and r.calibrated
        assert r.bone_age_months is None, (
            f"{sex}: an out-of-domain score produced a bone age again"
        )
        assert r.out_of_curve_domain
        assert r.curve_status == scoring.CURVE_BELOW_DOMAIN
        assert "below the score-to-age curve" in r.status
        assert f"{r.total_rus_score:g}" in r.status, "status should name the actual score"
        assert r.curve_domain is not None and any(
            f"{r.curve_domain[0]:g}" in w for w in r.warnings
        )


def test_maximum_grade_assessment_still_scores(t):
    """Guard against over-correcting: max grades sum to exactly 1000 by design
    (the TW3-RUS invariant this table was verified against), which is the last
    anchor. Rejecting it would break the top of the range."""
    for sex, expected_years in (("boys", 16.0), ("girls", 15.0)):
        top = {
            b: max(t.stage_to_score[sex][b], key=lambda k: t.stage_to_score[sex][b][k])
            for b in RUS_BONES
        }
        r = scoring.compute(top, sex, t)
        assert r.total_rus_score == 1000, f"{sex}: max-grade total is not 1000"
        assert r.curve_status == scoring.CURVE_OK
        assert r.bone_age_years == expected_years
        assert r.status == "ok"


def test_mid_range_assessment_is_unaffected(t):
    """The guard must not disturb ordinary in-range scoring."""
    r = scoring.compute({b: "5" for b in RUS_BONES}, "boys", t)
    assert r.curve_status == scoring.CURVE_OK
    assert r.bone_age_years is not None and 6.0 <= r.bone_age_years <= 16.0


def test_strict_calculation_raises_with_the_real_reason(t):
    with pytest.raises(scoring.ScoringError, match="below the score-to-age curve"):
        scoring.calculate_strict({b: "1" for b in RUS_BONES}, "boys", t)


def test_score_to_age_months_keeps_its_optional_int_contract(t):
    """Callers already branch on a None bone age, so the guard needed no
    downstream signature change -- this pins that."""
    assert scoring.score_to_age_months(96, "boys", t) is None
    assert isinstance(scoring.score_to_age_months(500, "boys", t), int)
    months, status = scoring.score_to_age_with_status(96, "boys", t)
    assert months is None and status == scoring.CURVE_BELOW_DOMAIN

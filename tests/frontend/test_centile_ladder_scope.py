"""The frontend centile-ladder inverse must stay on near-symmetric measures (M1.2).

`zForValueFromCentileStats` in index.html extends the 7-centile ladder in a
straight line beyond P3/P97. That is correct only where the distribution is
close to symmetric.

Measured, both directions:

  * its one real caller -- adult height at 19y (WHO, Cole's L ~ 1) -- has an
    error of 0.000 SD at +/-3 SD, so the straight-line tail is right there and
    was NOT changed;
  * the same algorithm applied to weight (right-skewed) mis-scores the tails by
    up to ~0.8 SD, which is what the backend was fixed for.

The client cannot mirror the backend fix: L, M and S are never sent to it. So
the guarantee has to be a scope limit -- this helper stays on height-like
measures, and anything skewed goes to /api/growth/point, which is exact.

Static analysis of the source, matching the convention of the other tests in
this directory (no browser or JS runner needed).
"""
import re
from pathlib import Path

import pytest

from backend.growth import blend

_INDEX_HTML = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
_CENTILE_Z = [
    (3, -1.8807936), (10, -1.2815516), (25, -0.6744898), (50, 0.0),
    (75, 0.6744898), (90, 1.2815516), (97, 1.8807936),
]


def _src() -> str:
    return _INDEX_HTML.read_text(encoding="utf-8")


def _ladder_z(stats: dict, value: float):
    """Python mirror of the frontend helper (straight-line tails)."""
    pts = sorted([(stats[c], z) for c, z in _CENTILE_Z], key=lambda p: p[0])

    def lerp(x0, z0, x1, z1):
        return z0 if x1 == x0 else z0 + (value - x0) / (x1 - x0) * (z1 - z0)

    if value <= pts[0][0]:
        return lerp(*pts[0], *pts[1])
    if value >= pts[-1][0]:
        return lerp(*pts[-2], *pts[-1])
    for a, b in zip(pts, pts[1:]):
        if a[0] <= value <= b[0]:
            return lerp(*a, *b)
    return None


# ── why the frontend was left alone ─────────────────────────────────────────

@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_straight_line_tail_is_accurate_for_adult_height(sex):
    """Its only caller. WHO height at 19y is near-symmetric, so the straight-line
    tail is exact -- rewriting it would have been churn, not a fix."""
    stats = {c: blend.unified_value_at_z("height", sex, 19.0, z) for c, z in _CENTILE_Z}
    for target_z in (-3.0, -2.5, 2.5, 3.0):
        value = blend.unified_value_at_z("height", sex, 19.0, target_z)
        assert _ladder_z(stats, value) == pytest.approx(target_z, abs=0.02)


@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_straight_line_tail_would_be_wrong_for_weight(sex):
    """Pins WHY the scope limit exists: the same algorithm on a skewed measure
    reproduces the backend bug that M1.2 fixed."""
    stats = {c: blend.unified_value_at_z("weight", sex, 10.0, z) for c, z in _CENTILE_Z}
    worst = max(
        abs(_ladder_z(stats, blend.unified_value_at_z("weight", sex, 10.0, tz)) - tz)
        for tz in (-3.0, 3.0)
    )
    assert worst > 0.20, (
        "the centile ladder no longer mis-scores skewed tails -- if the frontend "
        "helper gained an LMS-shaped tail, relax this guard and its scope comment"
    )


# ── the scope limit is documented and its caller is unchanged ───────────────

def test_scope_limit_is_documented_in_source():
    src = _src()
    assert "SCOPE LIMIT (M1.2)" in src, (
        "the scope comment on zForValueFromCentileStats was removed -- without it "
        "the next developer has no signal that this is height-only"
    )
    assert "/api/growth/point" in src


def test_helper_has_exactly_one_caller_and_it_is_adult_height():
    """If a second call site appears, it must be reviewed against the scope limit."""
    src = _src()
    # Exclude the declaration itself: `function zForValueFromCentileStats(`.
    calls = [
        m.start() for m in re.finditer(r"zForValueFromCentileStats\s*\(", src)
        if not src[:m.start()].rstrip().endswith("function")
    ]
    assert len(calls) == 1, (
        f"zForValueFromCentileStats now has {len(calls)} call sites (expected 1). "
        "A new caller must be checked: this helper is only valid for near-symmetric "
        "measures. For weight/BMI use /api/growth/point."
    )
    context = src[max(0, calls[0] - 700):calls[0] + 120]
    assert "adultHeight" in context, (
        "the single call site is no longer the adult-height projection -- re-verify "
        "the measure is near-symmetric before allowing the straight-line tail"
    )

"""Predicted adult height from skeletal maturity (M2C / C11).

**The tables are not bundled and are not invented.** Like the RUS point tables
beside them, TW3's percentage-of-adult-height values are copyrighted (Tanner,
Healy, Goldstein & Cameron, 2001) and must be entered once by a clinic from its
own licensed copy. Until then this returns nothing and says why.

What this computes
------------------
    predicted adult height = current height / (% of adult height attained)

where the percentage is read against **bone age**, not chronological age. That
substitution is the whole point: two 10-year-olds of identical height who differ
by two years of skeletal maturity have very different adult heights ahead of
them, and only the skeletally delayed one has the growth left to catch up.

Three different quantities, and they must never be merged
--------------------------------------------------------
This is the third of three adult-height numbers in the product, and the audit's
F-1 finding was that two of them were being conflated:

1. **Mid-parental target** (``clinical/prediction.py``) — where genetics point.
   Says nothing about whether this child is on track for it.
2. **Khamis-Roche** — predicted adult height with no radiograph. Gated on its
   own coefficients.
3. **This** — predicted adult height using the child's actual skeletal maturity.
   The most informative of the three when a film exists, and the only one that
   responds to a child being early or late maturing.

A prediction is only as good as the bone age behind it
------------------------------------------------------
This inherits every limitation of the bone age it is given. On the current
provisional TW3-C curve (digitized, ±0.5y) a half-year error near puberty moves
a predicted adult height by several centimetres, so :func:`predict` reports the
bone-age uncertainty alongside the number rather than letting a single figure
imply a precision it does not have.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

# Below this bone age the percentage-attained method is not used: the fraction
# of adult height attained is small, so dividing by it multiplies any error in
# the bone age enormously. Published tables generally start around here.
MIN_BONE_AGE_YEARS = 6.0

# A percentage this low would imply a prediction more than ~3x current height,
# which is never a real clinical result -- it means the table or the bone age is
# wrong, and returning the number would be worse than returning nothing.
MIN_PLAUSIBLE_PERCENT = 30.0


@dataclass(frozen=True)
class AdultHeightPrediction:
    available: bool
    predicted_cm: Optional[float]
    percent_attained: Optional[float]
    bone_age_years: Optional[float]
    method: str
    status: str
    # Range implied by the bone age's own uncertainty, when one is supplied.
    range_cm: Optional[tuple[float, float]] = None
    caveat: str = ""


def _interp_percent(anchors: Sequence[Sequence[float]], bone_age_years: float) -> Optional[float]:
    """Piecewise-linear % attained at a bone age. No extrapolation: outside the
    table's own range it returns None, for the same reason the RUS score->age
    curve refuses to clamp (M3.1) -- an endpoint value presented as a result is
    indistinguishable from a computed one."""
    pts = sorted(([float(p[0]), float(p[1])] for p in anchors if len(p) == 2),
                 key=lambda p: p[0])
    if len(pts) < 2:
        return None
    if bone_age_years < pts[0][0] or bone_age_years > pts[-1][0]:
        return None
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= bone_age_years <= x1:
            if x1 == x0:
                return y0
            return y0 + (bone_age_years - x0) / (x1 - x0) * (y1 - y0)
    return None


def table_for(sex: str, tables) -> list:
    """The %-attained anchors for one sex, or [] when not entered."""
    raw = (getattr(tables, "raw", None) or {}).get("pct_adult_height", {})
    return list(raw.get(sex) or [])


def is_calibrated(sex: str, tables) -> bool:
    return len(table_for(sex, tables)) >= 2


def predict(sex: str, current_height_cm: float, bone_age_years: Optional[float],
            tables, *, bone_age_uncertainty_years: Optional[float] = None
            ) -> AdultHeightPrediction:
    """Predicted adult height, or an explanation of why not."""
    method = "TW3 percentage of adult height attained"

    if not is_calibrated(sex, tables):
        return AdultHeightPrediction(
            False, None, None, bone_age_years, method,
            "The TW3 percentage-of-adult-height table is not entered. These "
            "values are copyrighted (Tanner, Healy, Goldstein & Cameron, 2001) "
            "and must be entered once from the clinic's licensed copy into "
            "letters_tables.json under 'pct_adult_height'. Nothing is estimated "
            "in their absence.",
        )
    if bone_age_years is None:
        return AdultHeightPrediction(False, None, None, None, method,
                                     "no bone age available to predict from")
    if not (current_height_cm and current_height_cm > 0):
        return AdultHeightPrediction(False, None, None, bone_age_years, method,
                                     "a current height is required")
    if bone_age_years < MIN_BONE_AGE_YEARS:
        return AdultHeightPrediction(
            False, None, None, bone_age_years, method,
            f"bone age {bone_age_years:.1f}y is below {MIN_BONE_AGE_YEARS:.0f}y. The "
            "percentage attained is small there, so dividing by it multiplies any "
            "error in the bone age into a large error in the prediction.",
        )

    percent = _interp_percent(table_for(sex, tables), bone_age_years)
    if percent is None:
        return AdultHeightPrediction(
            False, None, None, bone_age_years, method,
            f"bone age {bone_age_years:.1f}y is outside the entered table's range; "
            "the value is not extrapolated",
        )
    if percent < MIN_PLAUSIBLE_PERCENT:
        return AdultHeightPrediction(
            False, None, percent, bone_age_years, method,
            f"table returned {percent:.1f}% attained, which is implausible — check "
            "the entered values (percentages, not fractions)",
        )

    predicted = current_height_cm / (percent / 100.0)

    range_cm = None
    if bone_age_uncertainty_years:
        lo_pct = _interp_percent(table_for(sex, tables),
                                 bone_age_years + bone_age_uncertainty_years)
        hi_pct = _interp_percent(table_for(sex, tables),
                                 bone_age_years - bone_age_uncertainty_years)
        # A HIGHER bone age means more growth already achieved, so a LOWER
        # predicted adult height -- the mapping inverts, which is easy to get
        # backwards and would report the interval upside down.
        bounds = [current_height_cm / (p / 100.0) for p in (lo_pct, hi_pct) if p]
        if len(bounds) == 2:
            range_cm = (round(min(bounds), 1), round(max(bounds), 1))

    caveat = (
        "This prediction inherits the uncertainty of the bone age it was computed "
        "from. On a provisional curve a half-year error near puberty moves the "
        "result by several centimetres — quote the range, not the point estimate."
    )
    return AdultHeightPrediction(True, round(predicted, 1), round(percent, 2),
                                 bone_age_years, method, "ok", range_cm, caveat)

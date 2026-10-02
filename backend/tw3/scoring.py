"""
TW3-RUS deterministic scoring engine — the "S / scoring" module (directive §11).

    13 confirmed stages --(stage_to_score)--> RUS maturity score --(score_to_age)--> bone age

This module is pure and deterministic: same input → same output. It does NOT
touch the UI, image files, AI, or chronological age. It never invents a stage or
a score; when the licensed values are absent it reports exactly what is missing.

Chronological age is used only by callers to compute (bone age − chronological
age); it must never influence stage scoring (directive §11, §39).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from .constants import RUS_BONES, RUS_BONE_COUNT, SEXES, STAGES
from .tables import ScoringTables, load_tables

CALCULATION_VERSION = "tw3-rus-scoring-1.0"

# Status vocabulary for the score→age conversion (M3.1). "ok" is the only status
# that carries an age; every other value means the age is deliberately withheld.
# Declared here, above ScoreResult, because it is used as a field default —
# dataclass defaults are evaluated at class-definition time.
CURVE_OK = "ok"
CURVE_UNCALIBRATED = "curve_uncalibrated"
CURVE_BELOW_DOMAIN = "score_below_curve_domain"
CURVE_ABOVE_DOMAIN = "score_above_curve_domain"


class ScoringError(ValueError):
    """Raised by strict scoring when inputs are invalid or incomplete."""


@dataclass(frozen=True)
class BoneScore:
    bone_code: str
    confirmed_stage: str
    score: float


@dataclass(frozen=True)
class ScoreResult:
    """Immutable result of a TW3-RUS calculation."""

    method: str
    table_version: str
    calculation_version: str
    sex: str
    bones: tuple[BoneScore, ...]
    total_rus_score: float
    bone_age_months: Optional[int]
    status: str
    complete: bool
    calibrated: bool
    staged_count: int
    missing_stage: tuple[str, ...] = ()
    missing_score: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    # Why the score→age conversion did or did not produce an age (CURVE_*), and
    # the score range the curve is actually defined over. Exposed so the UI can
    # say "score 120 is below this curve's minimum of 150" instead of showing a
    # bare blank — or, as before M3.1, a clamped age indistinguishable from a
    # real one.
    curve_status: str = CURVE_UNCALIBRATED
    curve_domain: Optional[tuple[float, float]] = None

    @property
    def bone_age_years(self) -> Optional[float]:
        return None if self.bone_age_months is None else round(self.bone_age_months / 12, 2)

    @property
    def out_of_curve_domain(self) -> bool:
        return self.curve_status in (CURVE_BELOW_DOMAIN, CURVE_ABOVE_DOMAIN)


def curve_domain(anchors: list[list[float]]) -> Optional[tuple[float, float]]:
    """(min_score, max_score) the curve is actually defined over, or None if it
    has too few anchors to interpolate."""
    pts = sorted((p[0] for p in anchors if len(p) == 2))
    return (pts[0], pts[-1]) if len(pts) >= 2 else None


def _interp_months(anchors: list[list[float]], score: float) -> tuple[Optional[int], str]:
    """Piecewise-linear score→age(years) over ascending [score, ageYears]
    anchors, returned as (whole months, status).

    Out-of-domain scores return (None, reason) — they are NOT clamped to the
    endpoint. The previous clamp was silent and actively misleading at the low
    end: the TW3-C curve starts at score 150 (boys) / 270 (girls), so scores of
    50, 100 and 150 all returned exactly 6.00y with nothing in the output
    marking it a clamp rather than a computation. A clinician reading "bone age
    6.0y" could not tell it apart from a real result, and the product was least
    reliable exactly where it looked most confident.

    Withholding matches the engine's established contract everywhere else
    (§"nothing is ever guessed"): callers already branch on a None bone age, so
    this needs no signature change downstream.

    Boundary handling: a score exactly equal to either endpoint is IN domain
    (`<` / `>`, not `<=` / `>=`). This matters — a maximum-grade assessment
    legitimately totals exactly 1000, which is the curve's last anchor, and must
    not be rejected as out of range.
    """
    pts = sorted(([p[0], p[1]] for p in anchors if len(p) == 2), key=lambda p: p[0])
    if len(pts) < 2:
        return None, CURVE_UNCALIBRATED
    if score < pts[0][0]:
        return None, CURVE_BELOW_DOMAIN
    if score > pts[-1][0]:
        return None, CURVE_ABOVE_DOMAIN

    years = pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= score <= x1:
            years = y0 + (score - x0) / (x1 - x0) * (y1 - y0)
            break
    return round(years * 12), CURVE_OK


def _validate_sex(sex: str) -> None:
    if sex not in SEXES:
        raise ScoringError(f"unsupported sex {sex!r}; expected one of {SEXES}")


def score_to_age_months(score: float, sex: str, tables: ScoringTables) -> Optional[int]:
    """Bone age in months, or None when the curve cannot answer (uncalibrated, or
    the score falls outside the anchors). Use :func:`score_to_age_with_status`
    when the caller needs to explain *why* to a clinician."""
    _validate_sex(sex)
    months, _ = _interp_months(tables.score_to_age.get(sex, []), score)
    return months


def score_to_age_with_status(score: float, sex: str,
                             tables: ScoringTables) -> tuple[Optional[int], str]:
    """As :func:`score_to_age_months`, but also returns the CURVE_* status so the
    UI/report can distinguish 'this centre has not entered the tables' from
    'this score is off the end of the curve' — two very different messages."""
    _validate_sex(sex)
    return _interp_months(tables.score_to_age.get(sex, []), score)


def compute(stages: Mapping[str, str], sex: str,
            tables: Optional[ScoringTables] = None) -> ScoreResult:
    """Score the 13 RUS bones and convert to bone age, reporting an honest status.

    Non-strict: tolerates a partially-staged assessment (for live draft feedback)
    and never raises for missing data — it fills ``missing_stage`` / ``missing_score``
    and withholds the bone age. Use :func:`calculate_strict` for the final,
    approval-gated calculation that must have all 13 confirmed stages.
    """
    _validate_sex(sex)
    tables = tables or load_tables()

    tbl = tables.stage_to_score.get(sex, {})
    calibrated = tables.is_calibrated(sex)

    bones: list[BoneScore] = []
    total = 0.0
    staged = 0
    missing_stage: list[str] = []
    missing_score: list[str] = []
    warnings: list[str] = []

    for bone in RUS_BONES:
        stage = stages.get(bone)
        if not stage:
            missing_stage.append(bone)
            continue
        if stage not in tables.stages_for(bone) and stage not in STAGES:
            raise ScoringError(f"invalid stage {stage!r} for bone {bone!r}")
        staged += 1
        pts = (tbl.get(bone) or {}).get(stage)
        if isinstance(pts, (int, float)) and not isinstance(pts, bool):
            total += float(pts)
            bones.append(BoneScore(bone, stage, float(pts)))
        else:
            missing_score.append(bone)

    # Reject unknown bone codes supplied by the caller.
    for bone in stages:
        if bone not in RUS_BONES:
            raise ScoringError(f"unknown bone code {bone!r}")

    complete = staged == RUS_BONE_COUNT and not missing_score
    anchors = tables.score_to_age.get(sex, [])
    domain = curve_domain(anchors)
    bone_age_months: Optional[int] = None
    curve_status = CURVE_UNCALIBRATED
    if complete and calibrated:
        bone_age_months, curve_status = _interp_months(anchors, total)

    if not calibrated:
        status = "stage_to_score / score_to_age not calibrated for this sex"
    elif missing_stage:
        status = f"bones not staged: {', '.join(missing_stage)}"
    elif missing_score:
        status = f"no score for staged bones: {', '.join(missing_score)}"
    elif curve_status == CURVE_UNCALIBRATED:
        status = "score_to_age curve needs ≥2 anchor points for this sex"
    elif curve_status in (CURVE_BELOW_DOMAIN, CURVE_ABOVE_DOMAIN):
        # Explain the withholding rather than clamping to an endpoint (M3.1).
        # The bound is named so the clinician can see how far outside they are.
        side = "below" if curve_status == CURVE_BELOW_DOMAIN else "above"
        bound = domain[0] if curve_status == CURVE_BELOW_DOMAIN else domain[1]
        status = (
            f"RUS score {total:g} is {side} the score-to-age curve's range "
            f"({domain[0]:g}-{domain[1]:g}); no bone age can be derived. "
            "The previous behaviour silently reported the curve's endpoint age."
        )
        warnings.append(f"{curve_status}: score {total:g}, curve bound {bound:g}")
    else:
        status = "ok"

    return ScoreResult(
        method=tables.method,
        table_version=tables.version,
        calculation_version=CALCULATION_VERSION,
        sex=sex,
        bones=tuple(bones),
        total_rus_score=total,
        bone_age_months=bone_age_months,
        status=status,
        complete=complete,
        calibrated=calibrated,
        staged_count=staged,
        missing_stage=tuple(missing_stage),
        missing_score=tuple(missing_score),
        warnings=tuple(warnings),
        curve_status=curve_status,
        curve_domain=domain,
    )


@dataclass(frozen=True)
class CurveCaseResult:
    id: str
    sex: str
    expected_years: Optional[float]
    computed_years: Optional[float]
    error_years: Optional[float]
    within_tolerance: bool
    status: str


@dataclass(frozen=True)
class CurveValidation:
    """Result of checking the (digitized/provisional) score->age curve against a
    clinic's own historically-reported reference films (directive S-BA-2)."""
    validated: bool
    n_cases: int
    n_passing: int
    min_cases: int
    tolerance_years: float
    cases: tuple[CurveCaseResult, ...]


def validate_curve(tables: Optional[ScoringTables] = None) -> CurveValidation:
    """Score every entered reference case on the current tables and report whether
    the curve reproduces them within tolerance. The curve counts as *validated*
    only when at least ``min_cases`` cases are entered and ALL reproduce within
    ``tolerance_years`` -- this is what lets a digitized curve clear its
    'provisional' flag, on real local evidence rather than a self-declaration.
    Nothing here mutates the tables; it is pure verification."""
    tables = tables or load_tables()
    results: list[CurveCaseResult] = []
    passing = 0
    for i, case in enumerate(tables.reference_cases):
        cid = str(case.get("id") or f"case-{i + 1}")
        sex = case.get("sex")
        stages = case.get("stages") or {}
        expected = case.get("expected_bone_age_years")
        expected_f = float(expected) if isinstance(expected, (int, float)) else None
        computed_years: Optional[float] = None
        err: Optional[float] = None
        within = False

        if sex not in SEXES:
            status = f"invalid sex {sex!r}"
        elif expected_f is None:
            status = "missing expected_bone_age_years"
        else:
            try:
                r = compute(stages, sex, tables)
                if r.bone_age_years is None:
                    status = f"not scorable ({r.status})"
                else:
                    computed_years = r.bone_age_years
                    err = round(computed_years - expected_f, 3)
                    within = abs(err) <= tables.curve_tolerance_years
                    status = "pass" if within else "outside_tolerance"
            except ScoringError as exc:
                status = f"scoring_error: {exc}"

        if within:
            passing += 1
        results.append(CurveCaseResult(cid, str(sex), expected_f, computed_years, err, within, status))

    n = len(results)
    validated = n > 0 and n >= tables.curve_min_cases and passing == n
    return CurveValidation(
        validated=validated,
        n_cases=n,
        n_passing=passing,
        min_cases=tables.curve_min_cases,
        tolerance_years=tables.curve_tolerance_years,
        cases=tuple(results),
    )


def calculate_strict(stages: Mapping[str, str], sex: str,
                     tables: Optional[ScoringTables] = None) -> ScoreResult:
    """Final calculation for approval. Raises ScoringError unless all 13 bones
    are present with a valid, scored stage and the tables are calibrated."""
    _validate_sex(sex)
    tables = tables or load_tables()

    dupes = [b for b in stages if list(stages).count(b) > 1]
    if dupes:
        raise ScoringError(f"duplicate bone codes: {sorted(set(dupes))}")
    missing = [b for b in RUS_BONES if not stages.get(b)]
    if missing:
        raise ScoringError(f"incomplete: {len(missing)} of {RUS_BONE_COUNT} "
                           f"bones unstaged ({', '.join(missing)})")
    if not tables.is_calibrated(sex):
        raise ScoringError("TW3 tables are not calibrated; calculation disabled")

    result = compute(stages, sex, tables)
    if result.missing_score:
        raise ScoringError(f"no score for: {', '.join(result.missing_score)}")
    if result.bone_age_months is None:
        # Carry the real reason (out-of-domain vs uncalibrated curve) instead of
        # a generic failure -- this message reaches the clinician via the API.
        raise ScoringError(result.status)
    return result


# ── Backward-compatible thin wrappers (kept for existing importers) ────────────

def rus_score(stages: Mapping[str, str], sex: str, tables: ScoringTables) -> dict:
    r = compute(stages, sex, tables)
    return {
        "score": r.total_rus_score, "staged": r.staged_count, "total": RUS_BONE_COUNT,
        "calibrated": r.calibrated, "missing_score": list(r.missing_score),
        "missing_stage": list(r.missing_stage), "complete": r.complete,
    }


def score_to_age(score: float, sex: str, tables: ScoringTables) -> Optional[float]:
    m = score_to_age_months(score, sex, tables)
    return None if m is None else round(m / 12, 2)


def bone_age_from_stages(stages: Mapping[str, str], sex: str,
                         tables: Optional[ScoringTables] = None) -> dict:
    r = compute(stages, sex, tables or load_tables())
    return {
        "method": r.method, "rus_score": r.total_rus_score,
        "bone_age_years": r.bone_age_years, "bone_age_months": r.bone_age_months,
        "status": r.status, "score": r.total_rus_score, "staged": r.staged_count,
        "total": RUS_BONE_COUNT, "calibrated": r.calibrated,
        "missing_score": list(r.missing_score), "missing_stage": list(r.missing_stage),
        "complete": r.complete,
    }


if __name__ == "__main__":
    t = load_tables()
    for sex in SEXES:
        print(f"{sex}: calibrated={t.is_calibrated(sex)}  "
              f"score_to_age anchors={len(t.score_to_age.get(sex, []))}")

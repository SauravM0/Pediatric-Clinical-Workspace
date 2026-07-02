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

from dataclasses import dataclass, field
from typing import Mapping, Optional

from .constants import RUS_BONES, RUS_BONE_COUNT, SEXES, STAGES
from .tables import ScoringTables, load_tables

CALCULATION_VERSION = "tw3-rus-scoring-1.0"


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

    @property
    def bone_age_years(self) -> Optional[float]:
        return None if self.bone_age_months is None else round(self.bone_age_months / 12, 2)


def _interp_months(anchors: list[list[float]], score: float) -> Optional[int]:
    """Piecewise-linear score→age(years) over ascending [score, ageYears] anchors,
    returned in whole months. Clamps to the endpoints (terminal-stage behaviour)."""
    pts = sorted(([p[0], p[1]] for p in anchors if len(p) == 2), key=lambda p: p[0])
    if len(pts) < 2:
        return None
    if score <= pts[0][0]:
        years = pts[0][1]
    elif score >= pts[-1][0]:
        years = pts[-1][1]
    else:
        years = pts[-1][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= score <= x1:
                years = y0 + (score - x0) / (x1 - x0) * (y1 - y0)
                break
    return round(years * 12)


def _validate_sex(sex: str) -> None:
    if sex not in SEXES:
        raise ScoringError(f"unsupported sex {sex!r}; expected one of {SEXES}")


def score_to_age_months(score: float, sex: str, tables: ScoringTables) -> Optional[int]:
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
    bone_age_months = (
        score_to_age_months(total, sex, tables) if complete and calibrated else None
    )

    if not calibrated:
        status = "stage_to_score / score_to_age not calibrated for this sex"
    elif missing_stage:
        status = f"bones not staged: {', '.join(missing_stage)}"
    elif missing_score:
        status = f"no score for staged bones: {', '.join(missing_score)}"
    elif bone_age_months is None:
        status = "score_to_age curve needs ≥2 anchor points for this sex"
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
        raise ScoringError("could not convert RUS score to bone age")
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

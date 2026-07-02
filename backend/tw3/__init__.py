"""TW3-RUS automatic bone-age package: deterministic scoring, labelled data, training roadmap."""
from .constants import RUS_BONES, BONE_LABELS, STAGES, SEXES, RUS_BONE_COUNT, AssessmentStatus
from .tables import ScoringTables, load_tables, compute_checksum, TablesError
from .scoring import (
    bone_age_from_stages,
    rus_score,
    score_to_age,
    score_to_age_months,
    compute,
    calculate_strict,
    ScoreResult,
    BoneScore,
    ScoringError,
    CALCULATION_VERSION,
)

__all__ = [
    "RUS_BONES", "BONE_LABELS", "STAGES", "SEXES", "RUS_BONE_COUNT", "AssessmentStatus",
    "ScoringTables", "load_tables", "compute_checksum", "TablesError",
    "bone_age_from_stages", "rus_score", "score_to_age", "score_to_age_months",
    "compute", "calculate_strict", "ScoreResult", "BoneScore", "ScoringError",
    "CALCULATION_VERSION",
]

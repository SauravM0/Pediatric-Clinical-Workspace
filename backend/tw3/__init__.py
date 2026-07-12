"""TW3-RUS automatic bone-age package: deterministic scoring, labelled data, training roadmap."""
from .constants import (
    RUS_BONES, BONE_LABELS, STAGES, SEXES, RUS_BONE_COUNT, AssessmentStatus,
    CARPAL_BONES, CARPAL_LABELS, CARPAL_BONE_COUNT, ALL_BONE_LABELS, LETTER_STAGES,
    StageSystem, DEFAULT_STAGE_SYSTEM, SCORING_ENABLED_SYSTEMS,
    IMAGE_DOMAINS, LOW_TRUST_DOMAINS,
    bones_for_system, bone_group, label_for, scoring_enabled,
)
from .tables import ScoringTables, load_tables, compute_checksum, TablesError
from .scoring import (
    bone_age_from_stages,
    rus_score,
    score_to_age,
    score_to_age_months,
    compute,
    calculate_strict,
    validate_curve,
    CurveValidation,
    CurveCaseResult,
    ScoreResult,
    BoneScore,
    ScoringError,
    CALCULATION_VERSION,
)

__all__ = [
    "RUS_BONES", "BONE_LABELS", "STAGES", "SEXES", "RUS_BONE_COUNT", "AssessmentStatus",
    "CARPAL_BONES", "CARPAL_LABELS", "CARPAL_BONE_COUNT", "ALL_BONE_LABELS", "LETTER_STAGES",
    "StageSystem", "DEFAULT_STAGE_SYSTEM", "SCORING_ENABLED_SYSTEMS",
    "IMAGE_DOMAINS", "LOW_TRUST_DOMAINS",
    "bones_for_system", "bone_group", "label_for", "scoring_enabled",
    "ScoringTables", "load_tables", "compute_checksum", "TablesError",
    "bone_age_from_stages", "rus_score", "score_to_age", "score_to_age_months",
    "compute", "calculate_strict", "validate_curve", "CurveValidation",
    "CurveCaseResult", "ScoreResult", "BoneScore", "ScoringError",
    "CALCULATION_VERSION",
]

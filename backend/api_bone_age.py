"""Bone-age API: a thin, stateless bridge from the UI to the deterministic
TW3-C RUS scoring engine (directive §21).

Two endpoints for now (persistence and the full assessment lifecycle come with
the database work):

* ``GET  /api/bone-age/config``  — the canonical bone list, per-bone allowed
  grades, method/version and calibration status, so the frontend renders the
  staging UI from one source of truth instead of duplicating it.
* ``POST /api/bone-age/score``   — score confirmed grades → RUS score → bone age
  via ``backend.tw3.scoring`` only. No AI, no heuristic, no guessing.
"""

from __future__ import annotations

import statistics
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai import boneage
from backend.config import APP_VERSION
from backend.db import get_db
from backend.imaging import ImagingError, load_bytes
from backend.models import BoneAgeFeedback
from backend.tw3 import (
    BONE_LABELS,
    CARPAL_BONES,
    CARPAL_LABELS,
    IMAGE_DOMAINS,
    LETTER_STAGES,
    LOW_TRUST_DOMAINS,
    RUS_BONES,
    SEXES,
    ScoringError,
    StageSystem,
    bone_group,
    compute,
    load_tables,
    validate_curve,
)
from backend.tw3.tables import TablesError

router = APIRouter(prefix="/api/bone-age", tags=["bone-age"])


def _curve_declared_provisional(tables) -> bool:
    """The author's self-declaration that the curve is not yet trustworthy."""
    text = f"{tables.version} {tables.source_reference}".lower()
    return "provisional" in text or "digitized" in text


def _provisional_curve(tables) -> bool:
    """The score→age curve is provisional UNTIL it is validated on real evidence.

    A digitized/self-declared-provisional curve (directive S-BA-2) clears the flag
    only once it reproduces the clinic's own reference films within tolerance
    (``validate_curve``). A curve the author never declared provisional is not
    treated as provisional. So: provisional = declared AND not yet validated.
    """
    if not _curve_declared_provisional(tables):
        return False
    return not validate_curve(tables).validated


def _curve_validation_summary(tables) -> dict:
    """Read-out of the score→age curve gate (directive S-BA-2): how many of the
    clinic's reference films the digitized curve reproduces, and what is still
    needed to clear the provisional flag. Never exposes patient data — only case
    ids, expected/computed ages, and errors."""
    cv = validate_curve(tables)
    return {
        "declared_provisional": _curve_declared_provisional(tables),
        "validated": cv.validated,
        "n_cases": cv.n_cases,
        "n_passing": cv.n_passing,
        "min_cases": cv.min_cases,
        "tolerance_years": cv.tolerance_years,
        "cases": [
            {"id": c.id, "sex": c.sex, "expected_years": c.expected_years,
             "computed_years": c.computed_years, "error_years": c.error_years,
             "within_tolerance": c.within_tolerance, "status": c.status}
            for c in cv.cases
        ],
    }


class ScoreRequest(BaseModel):
    sex: str = Field(..., description="'boys' or 'girls'")
    stages: dict[str, str] = Field(
        default_factory=dict,
        description="Map of bone code -> confirmed grade, e.g. {'radius': '8'}",
    )


@router.get("/config")
def config() -> dict:
    try:
        t = load_tables()
    except TablesError as exc:
        raise HTTPException(status_code=500, detail=f"tables_invalid: {exc}") from exc

    return {
        "method": t.method,
        "version": t.version,
        "source_reference": t.source_reference,
        "notes": t.raw.get("notes", ""),
        "sexes": list(SEXES),
        "min_age_years": t.min_age_years,
        "max_age_years": t.max_age_years,
        "provisional_curve": _provisional_curve(t),
        "curve_validation": _curve_validation_summary(t),
        "calibrated": {sex: t.is_calibrated(sex) for sex in SEXES},
        "ai_estimate_available": boneage.model_available(),
        "ai_model": boneage.model_metadata(),
        "bones": [
            {"code": code, "label": BONE_LABELS[code], "stages": list(t.stages_for(code))}
            for code in RUS_BONES
        ],
        # Two staging streams from one source of truth (directive §6, §18). The
        # frontend renders the grading UI from this instead of duplicating it.
        "stage_systems": {
            StageSystem.TW3C_RUS.value: {
                "label": "TW3-C RUS (grades 1–8)",
                "scoring_enabled": True,
                "letter_stages_unverified": False,
                "bones": [
                    {"code": c, "label": BONE_LABELS[c], "group": "rus",
                     "stages": list(t.stages_for(c))}
                    for c in RUS_BONES
                ],
            },
            StageSystem.TW3_LETTERS.value: {
                "label": "Original TW3 letters (A–I) · 13 RUS + 7 carpals",
                "scoring_enabled": False,
                # Per-bone letter restrictions need the licensed original-TW3
                # source, which the project does not have; every bone offers A–I.
                "letter_stages_unverified": True,
                "note": "Annotation only — RUS and carpal scores/ages stay '—' "
                        "until the clinic's licensed TW3 tables are supplied.",
                "bones": [
                    {"code": c, "label": (BONE_LABELS.get(c) or CARPAL_LABELS.get(c)),
                     "group": bone_group(c), "stages": list(LETTER_STAGES)}
                    for c in (RUS_BONES + CARPAL_BONES)
                ],
            },
        },
    }


@router.post("/estimate")
async def estimate(
    file: UploadFile = File(...),
    sex: str = Form(...),
    image_domain: str = Form("unknown"),
) -> dict:
    """Stateless AI screening estimate for the top-of-page upload flow.

    Whole-image Greulich-Pyle style, NOT TW3 — a suggestion the doctor verifies.
    Works before any assessment exists; nothing is persisted here.

    ``image_domain`` (digital_diagnostic / compressed / film_photo / unknown) drives
    a quality gate: a model validated on clean digital radiographs cannot claim the
    same trust on a compressed WhatsApp image or a phone photo of a film, so those
    get an explicit low-trust flag (directive §16) instead of a silent number.
    """
    if sex not in SEXES:
        raise HTTPException(status_code=422, detail=f"unsupported sex: {sex!r}")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="empty upload")
    if not boneage.model_available():
        return {"available": False,
                "message": "No screening model installed. Train it locally with: "
                           "python -m backend.ai.train_boneage"}
    try:
        loaded = load_bytes(raw, file.filename or "")
    except ImagingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = boneage.predict_months(Image.fromarray(loaded.analysis), is_male=(sex == "boys"))

    domain = image_domain if image_domain in IMAGE_DOMAINS else "unknown"
    low_trust = domain in LOW_TRUST_DOMAINS
    quality_warning = None
    if low_trust:
        quality_warning = (
            "Low-trust image source ("
            + ("compressed export" if domain == "compressed" else "photo of a film")
            + "). The screening model was validated on clean digital radiographs; "
            "glare, compression and perspective can shift the estimate. Re-acquire a "
            "direct digital / DICOM image where possible, and rely on manual TW3."
        )
    return {
        "available": True,
        "source_format": loaded.source_format,
        "image_domain": domain,
        "low_trust": low_trust,
        "quality_warning": quality_warning,
        **(result or {}),
    }


class LettersScoreRequest(BaseModel):
    sex: str = Field(..., description="'boys' or 'girls'")
    rus_stages: dict[str, str] = Field(default_factory=dict, description="bone code -> letter A-I")
    carpal_stages: dict[str, str] = Field(default_factory=dict, description="carpal code -> letter A-I")


@router.post("/letters-score")
def letters_score(req: LettersScoreRequest) -> dict:
    """Stateless original-TW3 letter score for live report feedback: independent
    RUS and carpal scores/ages. Ages stay null until the licensed tables are entered."""
    from backend.tw3.letters_scoring import (
        LetterTablesError, compute_letters, load_letter_tables)

    if req.sex not in SEXES:
        raise HTTPException(status_code=422, detail=f"unsupported sex: {req.sex!r}")
    try:
        t = load_letter_tables()
        r = compute_letters(req.rus_stages, req.carpal_stages, req.sex, t)
    except LetterTablesError as exc:
        raise HTTPException(status_code=500, detail=f"letters_tables_invalid: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    def g(x) -> dict:
        return {"total_score": x.total_score if x.complete else None,
                "twii_age_years": x.twii_age_years, "twiii_age_years": x.twiii_age_years,
                "complete": x.complete, "staged_count": x.staged_count,
                "total_bones": x.total_bones, "points_calibrated": x.points_calibrated,
                "missing_stage": list(x.missing_stage)}

    tw20 = {"total_score": r.tw20.total_score if r.tw20.complete else None,
            "age_years": r.tw20.age_years, "complete": r.tw20.complete,
            "staged_count": r.tw20.staged_count, "total_bones": r.tw20.total_bones,
            "points_calibrated": r.tw20.points_calibrated}
    return {"any_calibrated": t.any_calibrated(), "rus": g(r.rus), "carpal": g(r.carpal), "tw20": tw20}


@router.post("/score")
def score(req: ScoreRequest) -> dict:
    if req.sex not in SEXES:
        raise HTTPException(status_code=422, detail=f"unsupported sex: {req.sex!r}")
    try:
        t = load_tables()
        r = compute(req.stages, req.sex, t)
    except (ScoringError, TablesError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "method": r.method,
        "table_version": r.table_version,
        "calculation_version": r.calculation_version,
        "provisional_curve": _provisional_curve(t),
        "sex": r.sex,
        "total_rus_score": r.total_rus_score,
        "bone_age_months": r.bone_age_months,
        "bone_age_years": r.bone_age_years,
        "status": r.status,
        "complete": r.complete,
        "calibrated": r.calibrated,
        "staged_count": r.staged_count,
        "total_bones": len(RUS_BONES),
        "missing_stage": list(r.missing_stage),
        "missing_score": list(r.missing_score),
        "warnings": list(r.warnings),
        "bones": [
            {"bone_code": b.bone_code, "confirmed_stage": b.confirmed_stage, "score": b.score}
            for b in r.bones
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feedback / self-improvement flywheel (report §3, §7)
#
# The suggestion box: a clinician's corrected bone age is logged as EVIDENCE
# (never the patient's clinical result). These rows power (a) AI-vs-human
# accuracy monitoring over time and (b) later consensus de-noising + retraining.
# ─────────────────────────────────────────────────────────────────────────────

_FEEDBACK_METHODS = {"tw3-rus", "greulich-pyle", "clinical", "other"}
_CONFIDENCE = {"low", "medium", "high"}
# A correction on a blurry WhatsApp photo is weaker evidence than one on a clean
# DICOM; low-trust domains are down-weighted in the accuracy read-out, not dropped.
_ADJUDICATION_SPREAD_MONTHS = 12  # raters disagreeing by >1yr on one image → review


class FeedbackRequest(BaseModel):
    corrected_age_years: float = Field(..., description="Clinician's corrected bone age, years")
    method: str = Field("clinical", description="tw3-rus | greulich-pyle | clinical | other")
    confidence: str = Field("medium", description="low | medium | high")
    rater_id: Optional[str] = Field(None, description="Who is correcting (enables consensus)")
    sex: Optional[str] = Field(None, description="boys | girls")
    chronological_age_years: Optional[float] = None
    ai_estimate_years: Optional[float] = Field(None, description="What the AI showed, for error tracking")
    ai_model_version: Optional[str] = None
    radiograph_id: Optional[int] = None
    assessment_id: Optional[int] = None
    image_hash: Optional[str] = None
    image_domain: Optional[str] = None
    note: Optional[str] = None


def _yr_to_months(years: Optional[float]) -> Optional[int]:
    return None if years is None else round(years * 12)


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)) -> dict:
    """Record a clinician's corrected bone age. Evidence only — never a patient result."""
    method = (req.method or "clinical").lower()
    if method not in _FEEDBACK_METHODS:
        raise HTTPException(status_code=422, detail=f"unsupported method: {req.method!r}")
    confidence = (req.confidence or "medium").lower()
    if confidence not in _CONFIDENCE:
        raise HTTPException(status_code=422, detail=f"confidence must be low/medium/high")
    corrected_m = _yr_to_months(req.corrected_age_years)
    if corrected_m is None or not (0 <= corrected_m <= 300):
        raise HTTPException(status_code=422, detail="corrected_age_years out of range (0–25 yr)")
    if req.sex is not None and req.sex not in SEXES:
        raise HTTPException(status_code=422, detail=f"unsupported sex: {req.sex!r}")

    row = BoneAgeFeedback(
        radiograph_id=req.radiograph_id,
        assessment_id=req.assessment_id,
        image_hash=req.image_hash,
        sex=req.sex,
        chronological_age_months=_yr_to_months(req.chronological_age_years),
        ai_estimate_months=_yr_to_months(req.ai_estimate_years),
        ai_model_version=req.ai_model_version,
        corrected_age_months=corrected_m,
        method=method,
        confidence=confidence,
        rater_id=(req.rater_id or None),
        image_domain=req.image_domain,
        note=(req.note or None),
        application_version=APP_VERSION,
    )
    db.add(row)
    db.flush()
    signed_err = None
    if row.ai_estimate_months is not None:
        signed_err = round((row.corrected_age_months - row.ai_estimate_months) / 12, 2)
    return {
        "ok": True,
        "id": row.id,
        "corrected_age_years": round(corrected_m / 12, 2),
        "ai_error_years": signed_err,  # + = AI under-estimated vs clinician
        "message": "Thanks — logged to improve accuracy. This does not change the patient's result.",
    }


def _mae(errs: list[float]) -> Optional[float]:
    return round(statistics.fmean(errs), 2) if errs else None


@router.get("/feedback/stats")
def feedback_stats(db: Session = Depends(get_db)) -> dict:
    """Monitoring read-out (report §6.2): running AI-vs-human error + per-image consensus.

    This is what 'daily learning' should really mean — watch the gap, don't silently
    mutate the model. MAE here is the live evidence that accuracy is (or isn't) improving.
    """
    rows = list(db.execute(select(BoneAgeFeedback)).scalars())
    total = len(rows)

    paired = [r for r in rows if r.ai_estimate_months is not None]
    abs_errs = [abs(r.corrected_age_months - r.ai_estimate_months) / 12 for r in paired]

    # Trend: MAE of the most recent third vs the rest (are we getting better?).
    paired_sorted = sorted(paired, key=lambda r: r.created_at or 0)
    recent_mae = older_mae = None
    if len(paired_sorted) >= 6:
        k = max(3, len(paired_sorted) // 3)
        recent = [abs(r.corrected_age_months - r.ai_estimate_months) / 12 for r in paired_sorted[-k:]]
        older = [abs(r.corrected_age_months - r.ai_estimate_months) / 12 for r in paired_sorted[:-k]]
        recent_mae, older_mae = _mae(recent), _mae(older)

    def _breakdown(key) -> dict:
        out: dict[str, dict] = {}
        for r in paired:
            k = getattr(r, key) or "unspecified"
            out.setdefault(k, []).append(abs(r.corrected_age_months - r.ai_estimate_months) / 12)
        return {k: {"n": len(v), "mae_years": _mae(v)} for k, v in out.items()}

    # Per-image consensus (report §7.2): group corrections on one image across raters.
    groups: dict[str, list[BoneAgeFeedback]] = {}
    for r in rows:
        gid = r.image_hash or (f"rg:{r.radiograph_id}" if r.radiograph_id else None)
        if gid:
            groups.setdefault(gid, []).append(r)
    consensus = []
    for gid, items in groups.items():
        raters = {i.rater_id for i in items if i.rater_id}
        ages = [i.corrected_age_months / 12 for i in items]
        spread = round(max(ages) - min(ages), 2)
        consensus.append({
            "image": gid,
            "n_corrections": len(items),
            "n_raters": len(raters),
            "median_age_years": round(statistics.median(ages), 2),
            "spread_years": spread,
            "needs_adjudication": len(raters) >= 2 and spread * 12 > _ADJUDICATION_SPREAD_MONTHS,
        })
    consensus.sort(key=lambda c: c["spread_years"], reverse=True)

    return {
        "total_feedback": total,
        "paired_with_ai": len(paired),
        "ai_vs_human_mae_years": _mae(abs_errs),
        "trend": {"recent_mae_years": recent_mae, "older_mae_years": older_mae,
                  "improving": (recent_mae is not None and older_mae is not None
                                and recent_mae < older_mae)},
        "by_method": _breakdown("method"),
        "by_image_domain": _breakdown("image_domain"),
        "by_confidence": _breakdown("confidence"),
        "consensus": consensus[:50],
        "note": ("Evidence log for monitoring + retraining. Corrections never change a "
                 "patient's reported bone age; model updates are a separate gated release."),
    }

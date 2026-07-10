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

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

from backend.ai import boneage
from backend.imaging import ImagingError, load_bytes
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
)
from backend.tw3.tables import TablesError

router = APIRouter(prefix="/api/bone-age", tags=["bone-age"])


def _provisional_curve(tables) -> bool:
    """The score→age curve is provisional if the version/source says so."""
    text = f"{tables.version} {tables.source_reference}".lower()
    return "provisional" in text or "digitized" in text


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

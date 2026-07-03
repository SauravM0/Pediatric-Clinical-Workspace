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
    RUS_BONES,
    SEXES,
    ScoringError,
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
    }


@router.post("/estimate")
async def estimate(file: UploadFile = File(...), sex: str = Form(...)) -> dict:
    """Stateless AI screening estimate for the top-of-page upload flow.

    Whole-image Greulich-Pyle style, NOT TW3 — a suggestion the doctor verifies.
    Works before any assessment exists; nothing is persisted here.
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
    return {"available": True, "source_format": loaded.source_format, **(result or {})}


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

"""Kidney-function API: eGFR and KDIGO staging (step 2).

The computation, every equation's age limits and the KDIGO heat map live in
``backend.renal``; this router only validates and serialises. A GET, because
nothing is stored -- so it needs read access, not write.
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from backend import renal
from backend.security.deps import clinical_access

router = APIRouter(prefix="/api/renal", tags=["renal"], dependencies=[Depends(clinical_access)])


@router.get("/egfr")
def egfr(
    sex: Literal["boys", "girls"] = Query(...),
    age: float = Query(..., ge=0.0, le=120.0),
    creatinine_mg_dl: float = Query(..., gt=0.0, le=25.0),
    height_cm: Optional[float] = Query(None, gt=0.0, le=250.0),
    weight_kg: Optional[float] = Query(None, gt=0.0, le=350.0),
    albuminuria: Optional[Literal["A1", "A2", "A3"]] = Query(None),
) -> dict:
    return renal.assess(age=age, sex=sex, scr_mg_dl=creatinine_mg_dl,
                        height_cm=height_cm, weight_kg=weight_kg, albuminuria=albuminuria)

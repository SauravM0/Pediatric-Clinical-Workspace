"""Vital-signs API: blood-pressure category for one reading (step 2).
Thresholds and the under-13 refusal live in ``backend.vitals``."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from backend import vitals
from backend.security.deps import clinical_access

router = APIRouter(prefix="/api/vitals", tags=["vitals"], dependencies=[Depends(clinical_access)])


@router.get("/blood-pressure")
def blood_pressure(
    age: float = Query(..., ge=0.0, le=120.0),
    sbp: float = Query(..., ge=40.0, le=300.0),
    dbp: float = Query(..., ge=20.0, le=200.0),
    sex: Optional[Literal["boys", "girls"]] = Query(None),
    height_cm: Optional[float] = Query(None, gt=0.0, le=250.0),
) -> dict:
    return vitals.assess(age=age, sbp=sbp, dbp=dbp, sex=sex, height_cm=height_cm)

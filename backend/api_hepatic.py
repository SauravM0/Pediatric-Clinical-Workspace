"""Liver API: FIB-4 (step 2). Computation and age limits live in ``backend.hepatic``."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend import hepatic
from backend.security.deps import clinical_access

router = APIRouter(prefix="/api/hepatic", tags=["hepatic"], dependencies=[Depends(clinical_access)])


@router.get("/fib4")
def fib4(
    age: float = Query(..., ge=0.0, le=120.0),
    ast: float = Query(..., gt=0.0, le=50000.0),
    alt: float = Query(..., gt=0.0, le=50000.0),
    platelets: float = Query(..., gt=0.0, le=5000.0, description="10^9/L (= 10^3/uL)"),
) -> dict:
    return hepatic.assess(age=age, ast=ast, alt=alt, platelets=platelets)

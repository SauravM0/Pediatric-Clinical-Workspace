"""Adult cardiovascular-risk API (QRISK3-2017), separate from the paediatric
modules. The computation + eligibility gate live in ``backend.cvd`` (audit F-3);
this router only validates the request and serialises the result."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, APIRouter
from pydantic import BaseModel, Field

from backend.cvd import qrisk3

from backend.security.deps import clinical_access

# Every route in this router requires an authenticated user with at least
# read access; mutating methods require write access (security phase, C.1).
# Applied at the router so a route added later is protected by construction.
router = APIRouter(prefix="/api/cvd", tags=["cvd"], dependencies=[Depends(clinical_access)])


class QRisk3Request(BaseModel):
    sex: str = Field(..., description="male/female (or boys/girls)")
    age: Optional[float] = None
    bmi: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    ethnicity: int = 1
    smoke: int = 0            # 0 non · 1 ex · 2 light · 3 moderate · 4 heavy
    diabetes: int = 0         # 0 none · 1 type1 · 2 type2
    cholesterol_ratio: Optional[float] = None
    systolic_bp: Optional[float] = None
    sbp_sd: Optional[float] = None
    townsend: Optional[float] = None
    AF: bool = False
    atypicalantipsy: bool = False
    corticosteroids: bool = False
    migraine: bool = False
    ra: bool = False
    renal: bool = False
    semi: bool = False
    sle: bool = False
    treatedhyp: bool = False
    fh_cvd: bool = False
    impotence2: bool = False


@router.post("/qrisk3")
def compute_qrisk3(req: QRisk3Request) -> dict:
    """QRISK3-2017 ten-year CVD risk. Returns ``available: False`` (no score) when
    the patient is outside the validated 25-84 adult range or BMI is missing, and
    lists any inputs filled with a population default in ``imputed_fields``."""
    return qrisk3(req.model_dump())

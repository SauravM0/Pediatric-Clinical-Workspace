"""Reference-data status: what every clinical number rests on (step 5).

Seven external references are needed for this product to be as accurate as its
engineering allows. None is bundled -- each is licensed, on request from its
authors, or must be transcribed -- and each has its own gated install path that
refuses to approximate. Until now their state was scattered over six status
functions and a validation endpoint no clinician would open.

This endpoint reads each gate's OWN status function (never a re-check), so it
cannot disagree with what the engine actually uses, and says for each one what
the clinic loses while it is missing and how to obtain it.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends

from backend.security.deps import clinical_access

router = APIRouter(prefix="/api/reference-data", tags=["reference-data"],
                   dependencies=[Depends(clinical_access)])


def _safe(fn: Callable[[], dict]) -> dict:
    """A broken reference file must show as inactive with its error, not 500
    the page that exists to show what is broken."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 -- reported, not swallowed
        return {"active": False, "reason": f"status check failed: {exc}"}


def _iap():
    from backend.growth import iap_lms_reference
    return iap_lms_reference.lms_status()


def _who():
    from backend.growth import who_lms_reference
    return who_lms_reference.lms_status()


def _velocity():
    from backend.growth import velocity_reference
    return velocity_reference.reference_status()


def _khamis_roche():
    from backend.clinical import prediction
    return prediction.khamis_roche_status()


def _tw3_points():
    from backend.tw3.letters_scoring import letters_status
    s = letters_status()
    return {"active": bool(s.get("scoring_ready")),
            "reason": "ok" if s.get("scoring_ready") else (
                "licensed TW3 point tables not entered"
                + (f"; provenance missing: {', '.join(s.get('missing_provenance') or [])}"
                   if s.get("missing_provenance") else ""))}


def _tw3_adult_height():
    from backend.tw3 import adult_height
    from backend.tw3.letters_scoring import load_letter_tables
    tables = load_letter_tables()
    gate = adult_height.licensing_gate(tables)
    calibrated = [s for s in ("boys", "girls") if adult_height.is_calibrated(s, tables)]
    active = gate["ok"] and bool(calibrated)
    reason = "ok" if active else ("% of adult height not entered" if not calibrated
                                  else "; ".join(gate["reasons"]))
    return {"active": active, "reason": reason, "sexes": calibrated}


def _aap_bp():
    from backend.vitals import aap_bp_reference
    return aap_bp_reference.status()


# (key, title, status fn, obtain, effect while missing, how-to document)
_REFERENCES = (
    ("iap_lms", "IAP 2015 L, M, S values (height, weight, BMI, 5–18 y)", _iap, "email the authors",
     "Indian centiles 5–18 y are fitted to published tables; 4 of 7 height/weight columns are "
     "interpolated (the drawn 25th centile is the 26.5th); tail z-scores carry ~0.07 SD error.",
     "backend/growth/data/IAP-LMS-REQUEST.md"),
    ("who_lms", "WHO 2006/2007 L, M, S tables", _who, "free download from WHO",
     "WHO centiles come from the rcpchgrowth package (AGPL-3.0) rather than WHO's own files.",
     "backend/growth/data/WHO-LMS-REQUEST.md"),
    ("velocity", "Indian height-velocity centiles (Khadilkar 2019)", _velocity, "email the authors",
     "Height velocity is shown without a centile; the low-velocity rule uses a 4 cm/yr rule of thumb "
     "at low confidence.", "backend/growth/data/VELOCITY-REFERENCE-REQUEST.md"),
    ("khamis_roche", "Khamis-Roche adult-height coefficients", _khamis_roche,
     "transcribe from the paper (two people)",
     "No adult-height prediction without an X-ray; only the mid-parental target is available.",
     "backend/clinical/KHAMIS-ROCHE-REQUEST.md"),
    ("tw3_points", "TW3 point tables and score→age conversion (licensed book)", _tw3_points,
     "buy the TW3 book (3rd ed., 2001)",
     "Bone age is TW3-C from a conference paper with a curve digitised from a figure — provisional, "
     "not Tanner TW3 (≈0.9–1.25 y off this centre's historical reports).",
     "backend/tw3/TW3-BOOK-REQUEST.md"),
    ("tw3_adult_height", "TW3 % of adult height by bone age (licensed book)", _tw3_adult_height,
     "buy the TW3 book; transcribe (two people)",
     "No adult-height prediction from skeletal maturity.", "backend/tw3/TW3-BOOK-REQUEST.md"),
    ("aap_bp", "AAP 2017 paediatric BP tables (Tables 4–5)", _aap_bp,
     "transcribe from the open-access guideline (two people)",
     "Children under 13 get no blood-pressure category.", "backend/vitals/AAP-BP-TABLES.md"),
)


@router.get("")
def reference_data_status() -> dict[str, Any]:
    items = []
    for key, title, fn, obtain, effect, doc in _REFERENCES:
        s = _safe(fn)
        items.append({
            "key": key, "title": title, "active": bool(s.get("active")),
            "reason": s.get("reason"), "obtain": obtain,
            "effect_while_missing": effect, "how_to": doc,
        })
    return {
        "items": items,
        "active_count": sum(i["active"] for i in items),
        "total": len(items),
        "note": ("Every inactive reference is REFUSED rather than approximated: the "
                 "workspace shows what it cannot compute instead of guessing. Each how-to "
                 "document gives the exact source, request wording and install command."),
    }

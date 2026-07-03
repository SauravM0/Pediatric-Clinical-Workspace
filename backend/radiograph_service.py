"""Attach an uploaded radiograph to an assessment (directive §13, §9.2).

Stores the immutable original + derived analysis/thumbnail, records a Radiograph
row, links it to the assessment, runs the quality pre-check and writes an audit
event. Duplicate uploads (same bytes for the same patient) are flagged, not
blocked — a repeat study of the same child is legitimate.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import RADIOGRAPH_DIR
from backend.imaging import image_hash, load_bytes, quality_precheck, store_radiograph
from backend.models import Radiograph, TW3Assessment
from backend.tw3 import AssessmentStatus
from backend.assessment_service import AssessmentError, _audit, get_assessment

_EXT_BY_FORMAT = {"DICOM": "dcm", "PNG": "png", "JPEG": "jpg", "BMP": "bmp"}


def attach_image(db: Session, assessment_id: int, raw: bytes, filename: str,
                 *, actor: str = "local-user") -> dict:
    a = get_assessment(db, assessment_id)
    if a.assessment_status in (AssessmentStatus.APPROVED.value,
                               AssessmentStatus.SUPERSEDED.value):
        raise AssessmentError("assessment is locked; open a revision to change the image")

    loaded = load_bytes(raw, filename)  # raises ImagingError on bad input
    digest = image_hash(raw)
    status, flags = quality_precheck(loaded)

    duplicate = db.execute(
        select(Radiograph).where(Radiograph.image_hash == digest)
        .where(Radiograph.patient_id == a.patient_id)
    ).scalars().first()

    rg = Radiograph(
        patient_id=a.patient_id,
        original_filename=filename or None,
        source_format=loaded.source_format,
        image_hash=digest,
        width=loaded.width, height=loaded.height, bit_depth=loaded.bit_depth,
        laterality=loaded.laterality, modality=loaded.modality,
        quality_status=status, quality_flags=json.dumps(flags),
        anonymisation_status="working_copy_deidentified",
        study_date=None,
    )
    db.add(rg)
    db.flush()  # assign id for the storage folder

    ext = _EXT_BY_FORMAT.get(loaded.source_format, "bin")
    paths = store_radiograph(RADIOGRAPH_DIR / str(rg.id), raw, loaded, ext)
    rg.internal_file_path = paths["original"]

    a.radiograph_id = rg.id
    a.quality_status = status

    _audit(db, assessment_id=a.id, patient_id=a.patient_id, event_type="upload",
           actor=actor, new={"radiograph_id": rg.id, "format": loaded.source_format,
                             "quality_status": status, "flags": flags,
                             "duplicate_of": duplicate.id if duplicate else None})
    db.flush()

    return {
        "radiograph_id": rg.id,
        "assessment_id": a.id,
        "source_format": loaded.source_format,
        "width": rg.width, "height": rg.height, "bit_depth": rg.bit_depth,
        "laterality": rg.laterality, "modality": rg.modality,
        "quality_status": status, "quality_flags": flags,
        "duplicate_of": duplicate.id if duplicate else None,
        "warnings": loaded.warnings,
        "thumbnail_url": f"/api/bone-age/radiographs/{rg.id}/thumbnail",
        "analysis_url": f"/api/bone-age/radiographs/{rg.id}/analysis",
    }


def radiograph_file(db: Session, radiograph_id: int, kind: str) -> str:
    """Return the on-disk path for a stored derivative ('thumbnail'|'analysis').
    Never serves the raw original (may be an undecoded DICOM / carry metadata)."""
    rg = db.get(Radiograph, radiograph_id)
    if rg is None or not rg.internal_file_path:
        raise AssessmentError(f"radiograph {radiograph_id} not found")
    folder = (RADIOGRAPH_DIR / str(rg.id))
    name = {"thumbnail": "thumb.png", "analysis": "analysis.png"}.get(kind)
    if name is None:
        raise AssessmentError(f"unknown image kind: {kind!r}")
    path = folder / name
    if not path.exists():
        raise AssessmentError("image derivative missing on disk")
    return str(path)

"""Image ingestion: DICOM / PNG / JPEG / BMP → normalised grayscale, plus an
immutable-storage layout and a deterministic quality pre-check (directive §13, §14).

Design rules honoured here:
* the original upload is stored byte-for-byte and never modified;
* a separate normalised 8-bit analysis image and a thumbnail are derived;
* DICOM is decoded deliberately (modality/VOI LUT, MONOCHROME1 inversion),
  not treated as an ordinary JPEG;
* identifying DICOM metadata is NOT copied into the working files;
* filenames are generated (never patient names).
Nothing here reaches the network.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Optional

import numpy as np
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 80 * 1024 * 1024  # 80 MB guard (directive §22 excessively-large upload)
_THUMB_MAX = 320
_ANALYSIS_MAX = 1024

_RASTER_EXT = {"png", "jpg", "jpeg", "bmp"}


class ImagingError(ValueError):
    """Raised when an upload cannot be read or is unsupported."""


@dataclass
class LoadedImage:
    analysis: np.ndarray  # 2D uint8 grayscale (normalised)
    width: int
    height: int
    bit_depth: int
    source_format: str  # 'DICOM' | 'PNG' | 'JPEG' | 'BMP'
    modality: Optional[str] = None
    laterality: Optional[str] = None
    study_date: Optional[str] = None
    is_color_source: bool = False
    warnings: list[str] = field(default_factory=list)


def image_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _looks_like_dicom(raw: bytes) -> bool:
    return len(raw) > 132 and raw[128:132] == b"DICM"


def _looks_like_raster(raw: bytes) -> bool:
    """Content sniff by magic bytes — so a misleading extension can't fool us."""
    return (raw[:8] == b"\x89PNG\r\n\x1a\n"  # PNG
            or raw[:3] == b"\xff\xd8\xff"      # JPEG
            or raw[:2] == b"BM")               # BMP


def _normalise_to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float64)
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-6:
        return np.zeros(arr.shape, dtype=np.uint8)
    return np.clip((arr - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)


def _load_dicom(raw: bytes) -> LoadedImage:
    import pydicom

    try:
        ds = pydicom.dcmread(io.BytesIO(raw), force=True)
    except Exception as exc:  # pragma: no cover - defensive
        raise ImagingError(f"unreadable DICOM: {exc}") from exc

    try:
        pixels = ds.pixel_array
    except Exception as exc:
        raise ImagingError(
            "This DICOM uses a compressed transfer syntax that the installed "
            "decoder cannot read. Export an uncompressed DICOM or a lossless PNG."
        ) from exc

    if pixels.ndim > 2:  # multi-frame / colour — take first frame, first plane
        pixels = pixels[0] if pixels.shape[0] < pixels.shape[-1] else pixels[..., 0]

    arr = pixels.astype(np.float64)
    try:
        from pydicom.pixels import apply_modality_lut, apply_voi_lut
    except Exception:  # pragma: no cover - pydicom <3 fallback
        from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
    try:
        arr = apply_modality_lut(arr, ds)
        arr = apply_voi_lut(arr, ds)
    except Exception:
        pass  # LUTs optional; fall back to raw pixels

    if str(getattr(ds, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
        arr = arr.max() - arr  # invert so bone is bright

    analysis = _normalise_to_uint8(arr)
    laterality = (getattr(ds, "ImageLaterality", None)
                  or getattr(ds, "Laterality", None) or None)
    return LoadedImage(
        analysis=analysis,
        width=int(analysis.shape[1]),
        height=int(analysis.shape[0]),
        bit_depth=int(getattr(ds, "BitsStored", 16) or 16),
        source_format="DICOM",
        modality=str(getattr(ds, "Modality", "") or "") or None,
        laterality=str(laterality) if laterality else None,
        study_date=str(getattr(ds, "StudyDate", "") or "") or None,
    )


def _load_raster(raw: bytes) -> LoadedImage:
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise ImagingError(f"unreadable image file: {exc}") from exc

    fmt = (img.format or "").upper()
    if fmt == "MPO":
        fmt = "JPEG"
    if fmt not in {"PNG", "JPEG", "BMP"}:
        raise ImagingError(f"unsupported image format: {img.format!r}")

    img = ImageOps.exif_transpose(img)
    is_color = img.mode not in ("L", "I", "I;16", "1")
    gray = img.convert("L")
    arr = np.asarray(gray)
    warnings: list[str] = []
    if is_color:
        warnings.append("colour_source_converted_to_grayscale")
    return LoadedImage(
        analysis=arr,
        width=int(img.width),
        height=int(img.height),
        bit_depth=8,
        source_format="JPEG" if fmt == "JPEG" else fmt,
        is_color_source=is_color,
        warnings=warnings,
    )


def load_bytes(raw: bytes, filename: str = "") -> LoadedImage:
    """Decode an upload into a normalised grayscale analysis image + metadata."""
    if not raw:
        raise ImagingError("empty upload")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ImagingError("upload exceeds the maximum allowed size")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    # Content wins over the extension (directive §25.2 misleading-extension case).
    if _looks_like_raster(raw):
        return _load_raster(raw)
    if _looks_like_dicom(raw) or ext == "dcm":
        return _load_dicom(raw)
    if ext in _RASTER_EXT:
        return _load_raster(raw)
    # Last resort: attempt a raster decode; ImagingError if that also fails.
    return _load_raster(raw)


def quality_precheck(img: LoadedImage) -> tuple[str, list[str]]:
    """Deterministic v1 quality gate (directive §14). Returns (status, flags).

    Statuses: accepted | accepted_with_warning | doctor_review_required.
    A truly unreadable image raises ImagingError earlier, so 'rejected' is not
    produced here; the doctor confirms or overrides warnings in the UI.
    """
    flags: list[str] = list(img.warnings)
    review = False

    if img.width < 200 or img.height < 200:
        flags.append("very_small_image")
        review = True
    aspect = img.width / max(img.height, 1)
    if aspect > 2.2 or aspect < 0.4:
        flags.append("unusual_framing")
        review = True
    if float(img.analysis.std()) < 15:
        flags.append("low_contrast")
        review = True
    if img.laterality and str(img.laterality).upper().startswith("R"):
        flags.append("laterality_right_check_left_hand")
        review = True

    if review:
        return "doctor_review_required", flags
    if flags:
        return "accepted_with_warning", flags
    return "accepted", flags


# ─────────────────────────────────────────────────────────────────────────────
# Image acceptability gate for the AI screening estimate (directive S-BA-6).
#
# Canonical quality-flag vocabulary, kept in sync with the product contract at
# bone_age_product_starter_pack/case_input_schema.json (a drift test asserts the
# two match). validation_protocol.md §4: "Do not silently generate a normal
# report after a quality failure" -- so a HARD flag makes the whole-hand AI
# estimate abstain and route to manual assessment, never emit a silent age.
# ─────────────────────────────────────────────────────────────────────────────
CANONICAL_QUALITY_FLAGS: Final[frozenset[str]] = frozenset({
    "WRONG_LATERALITY", "NON_PA_POSITION", "ROTATION", "MOTION_BLUR",
    "UNDEREXPOSED", "OVEREXPOSED", "CLIPPED_DISTAL_RADIUS_ULNA", "CLIPPED_DIGITS",
    "FOREIGN_OBJECT", "CAST_OR_HARDWARE", "FRACTURE", "SEVERE_DEFORMITY",
    "BONE_DYSPLASIA_SUSPECTED", "IMAGE_TOO_SMALL", "DUPLICATE", "OTHER",
})

# Flags that invalidate a whole-hand AI bone-age estimate (missing/altered
# anatomy, wrong body part, or an unanalysable image) -> abstain, manual review.
HARD_QUALITY_FLAGS: Final[frozenset[str]] = frozenset({
    "WRONG_LATERALITY", "NON_PA_POSITION", "CLIPPED_DISTAL_RADIUS_ULNA",
    "CLIPPED_DIGITS", "FOREIGN_OBJECT", "CAST_OR_HARDWARE", "FRACTURE",
    "SEVERE_DEFORMITY", "BONE_DYSPLASIA_SUSPECTED", "IMAGE_TOO_SMALL", "DUPLICATE",
})


def auto_quality_flags(img: LoadedImage) -> tuple[list[str], list[str]]:
    """Deterministic auto-detected quality flags + advisory notes.

    Only flags what can be determined RELIABLY without a validated classifier:
    IMAGE_TOO_SMALL (dimensions) and WRONG_LATERALITY (DICOM laterality). Anything
    diagnostic -- fracture, cast, clipping, deformity, dysplasia, rotation,
    exposure -- is left to clinician declaration; the app does not claim to
    auto-detect it (that needs a validated model; audit P2). Low contrast is an
    advisory NOTE, never a gating flag."""
    flags: list[str] = []
    if img.width < 200 or img.height < 200:
        flags.append("IMAGE_TOO_SMALL")
    if img.laterality and str(img.laterality).upper().startswith("R"):
        flags.append("WRONG_LATERALITY")
    notes: list[str] = list(img.warnings)
    if float(img.analysis.std()) < 12:
        notes.append("low_contrast_or_near_blank")
    return flags, notes


def gate_ai_estimate(auto_flags: list[str], declared_flags: list[str]) -> dict:
    """Combine auto + clinician-declared flags and decide whether a whole-hand AI
    estimate may be shown. Returns a block matching report_output_schema.json's
    image_quality section, plus the hard/soft split and provenance of each flag."""
    declared = sorted({f.strip().upper() for f in declared_flags if f and f.strip()})
    known = [f for f in declared if f in CANONICAL_QUALITY_FLAGS]
    unknown = [f for f in declared if f not in CANONICAL_QUALITY_FLAGS]
    all_flags = sorted(set(auto_flags) | set(known))
    hard = sorted(f for f in all_flags if f in HARD_QUALITY_FLAGS)
    soft = sorted(f for f in all_flags if f not in HARD_QUALITY_FLAGS)
    accepted = not hard
    reason = None if accepted else (
        "Image-quality gate failed (" + ", ".join(hard) + "). A whole-hand AI "
        "bone-age estimate is not valid on this film; manual assessment required."
    )
    return {
        "accepted": accepted,
        "flags": all_flags,
        "hard_flags": hard,
        "soft_flags": soft,
        "auto_flags": sorted(auto_flags),
        "declared_flags": known,
        "unknown_declared": unknown,
        "reason_for_rejection": reason,
    }


def store_radiograph(dest_dir: Path, raw: bytes, img: LoadedImage,
                     source_ext: str) -> dict[str, str]:
    """Write the immutable original + normalised analysis PNG + thumbnail into
    ``dest_dir`` using generated filenames. Returns the stored relative paths."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    original = dest_dir / f"original.{source_ext.lower()}"
    original.write_bytes(raw)  # byte-for-byte, never modified

    analysis_img = Image.fromarray(img.analysis, mode="L")
    analysis_copy = analysis_img.copy()
    analysis_copy.thumbnail((_ANALYSIS_MAX, _ANALYSIS_MAX))
    analysis_path = dest_dir / "analysis.png"
    analysis_copy.save(analysis_path, format="PNG")

    thumb = analysis_img.copy()
    thumb.thumbnail((_THUMB_MAX, _THUMB_MAX))
    thumb_path = dest_dir / "thumb.png"
    thumb.save(thumb_path, format="PNG")

    return {
        "original": str(original),
        "analysis": str(analysis_path),
        "thumbnail": str(thumb_path),
    }

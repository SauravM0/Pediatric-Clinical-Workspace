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
    # Acquisition-provenance signals, captured BEFORE grayscale conversion
    # throws them away. See detect_acquisition_domain.
    camera_exif: dict[str, str] = field(default_factory=dict)
    colour_spread: float = 0.0     # mean |channel - grey|, 0 for true grayscale


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

    exif = _camera_exif(img)
    img = ImageOps.exif_transpose(img)
    is_color = img.mode not in ("L", "I", "I;16", "1")
    spread = _colour_spread(img) if is_color else 0.0
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
        camera_exif=exif,
        colour_spread=spread,
    )


# EXIF tags a camera writes and an imaging workstation does not. Read before
# exif_transpose, which consumes the orientation tag.
_CAMERA_TAGS: Final[dict[int, str]] = {
    271: "Make", 272: "Model", 33437: "FNumber", 33434: "ExposureTime",
    34855: "ISOSpeedRatings", 37386: "FocalLength", 42036: "LensModel",
}


def _camera_exif(img: Image.Image) -> dict[str, str]:
    """Camera identification tags, if any. Deliberately narrow: only tags that
    indicate a photograph was taken, never anything patient-identifying."""
    try:
        raw = img.getexif()
    except Exception:
        return {}
    out: dict[str, str] = {}
    for tag, name in _CAMERA_TAGS.items():
        value = raw.get(tag)
        if value not in (None, "", b""):
            out[name] = str(value)[:64]
    return out


def _colour_spread(img: Image.Image) -> float:
    """Mean per-pixel deviation of R,G,B from their own grey, 0-255.

    A radiograph saved as RGB is grey in every pixel, so this is ~0 however
    large the file. A photograph of a film carries the room: wall tint, skin,
    and the lighting's colour temperature. This separates "stored as RGB" from
    "actually contains colour", which the is_color flag alone cannot.
    """
    small = img.convert("RGB").resize((64, 64))
    a = np.asarray(small, dtype=np.float32)
    return float(np.abs(a - a.mean(axis=2, keepdims=True)).mean())


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


# Above this mean channel deviation the image genuinely contains colour rather
# than being a grey image stored in three channels. A radiograph re-saved as RGB
# measures ~0; a phone photo of a film carries the room's colour cast. Set well
# clear of JPEG chroma noise, which lands under 1.
COLOUR_SPREAD_PHOTO_THRESHOLD: Final[float] = 3.0


def detect_acquisition_domain(img: LoadedImage) -> dict:
    """Was this a digital radiograph, or a photograph of a film?

    This is deliberately NOT the kind of judgement `auto_quality_flags` refuses
    to make. Fracture, cast, deformity and rotation are DIAGNOSTIC properties
    needing a validated classifier. How a file was acquired is not diagnostic --
    it is provenance, and it leaves deterministic traces:

    * **DICOM** is a radiograph by construction. Nothing else to decide.
    * **Camera EXIF** (Make/Model/FNumber/ISO/FocalLength) is written by a
      camera and not by an imaging workstation. Its presence is close to proof.
    * **Real colour** separates "a grey image stored as RGB" (spread ~0) from
      "a photograph containing a wall, a hand and warm indoor light".

    Returns the inferred domain, a confidence, and the evidence — so the caller
    can show a clinician WHY rather than asserting it.
    """
    evidence: list[str] = []

    if img.source_format == "DICOM":
        return {"domain": "digital_diagnostic", "confidence": "certain",
                "evidence": ["DICOM: a radiograph by construction"],
                "auto_detected": True}

    if img.camera_exif:
        shown = ", ".join(f"{k}={v}" for k, v in sorted(img.camera_exif.items())[:3])
        evidence.append(f"camera EXIF present ({shown})")
    if img.colour_spread >= COLOUR_SPREAD_PHOTO_THRESHOLD:
        evidence.append(
            f"image contains real colour (spread {img.colour_spread:.1f}, "
            f"threshold {COLOUR_SPREAD_PHOTO_THRESHOLD}) — a radiograph is grey "
            "in every pixel")

    if img.camera_exif and img.colour_spread >= COLOUR_SPREAD_PHOTO_THRESHOLD:
        return {"domain": "film_photo", "confidence": "high",
                "evidence": evidence, "auto_detected": True}
    if evidence:
        # One signal alone: a photo stripped of EXIF, or a colour-managed export.
        # Enough to warn on, not enough to assert.
        return {"domain": "film_photo", "confidence": "moderate",
                "evidence": evidence, "auto_detected": True}

    return {"domain": "unknown", "confidence": "none",
            "evidence": ["no camera EXIF and no real colour — consistent with a "
                         "digital export, but a stripped photo looks the same"],
            "auto_detected": False}


# ─────────────────────────────────────────────────────────────────────────────
# Is this image a radiograph at all?
#
# Measured 2026-08-14: the estimator returned a confident age for images with no
# anatomy in them whatsoever -- flat grey 0.6 yr, random noise 4.7 yr [3.2-6.3],
# a scanned document 0.4 yr -- all with accepted=True and no flag of any kind.
# In the UI that renders as a bone age, a 90% conformal interval and a green
# "Use as bone age" button, which is exactly the "silently generate a normal
# report after a quality failure" that validation_protocol.md §4 forbids.
#
# WHAT THIS IS NOT
# ----------------
# It is not a hand detector. It cannot tell a hand from a foot, a chest or an
# adult's wrist; those need a validated classifier and this project does not
# claim auto-detection it has not validated (see auto_quality_flags). It rejects
# only images with no plausible radiographic STRUCTURE -- the degenerate uploads
# a mis-picked file actually produces.
#
# WHY FOUR NARROW RULES AND NOT ONE SCORE
# ---------------------------------------
# Measured on the three real films available against five synthetic negatives,
# no single statistic separates them:
#
#   image            std     autocorr    entropy(32 bins)
#   real film        31.8    0.9926      3.68
#   real film        39.4    0.9977      4.02
#   real photo       61.3    0.9983      4.22
#   flat grey         0.0    0.0000      0.00
#   random noise     74.0    0.0034      5.00
#   document        108.9    0.8886      0.90
#   smooth gradient  73.7    1.0000      5.00
#
# `std` does not separate at all (a document out-scores every real film).
# `autocorr` catches noise and flat but the gradient scores 1.0000 -- HIGHER
# than any real image. Entropy catches the document and the ramp but not noise.
# So each rule targets one failure mode and the thresholds sit far from the real
# films rather than being fitted to them.
#
# CALIBRATION IS THIN AND THAT SHAPES THE THRESHOLDS
# --------------------------------------------------
# Three real positives is not a validation set. Every bound below is therefore
# placed to make a FALSE REJECT very unlikely, accepting that unusual-but-real
# images pass. Wrongly refusing a genuine film is worse than the bug: the
# clinician loses a working tool and learns to distrust the gate.
# ─────────────────────────────────────────────────────────────────────────────

# Below this the image is blank or near-blank. Real films measured 31.8-61.3.
STRUCTURE_MIN_STD: Final[float] = 8.0
# Neighbouring pixels must predict each other. Real films 0.9926-0.9990;
# random noise 0.0034. Anything optical is far above this.
STRUCTURE_MIN_AUTOCORR: Final[float] = 0.90
# A two-tone image (text on white) carries almost no grey structure. Real films
# 3.68-4.22 bits; the document 0.90.
STRUCTURE_MIN_ENTROPY: Final[float] = 1.5
# A flat histogram means every intensity is equally likely, which anatomy never
# produces. Real max 4.22; a linear ramp and uniform noise both hit 5.00.
STRUCTURE_MAX_ENTROPY: Final[float] = 4.75
# ...but high entropy alone must not condemn a busy film, so the ramp rule also
# requires near-perfect smoothness. Real films top out at 0.9990.
STRUCTURE_RAMP_AUTOCORR: Final[float] = 0.9995


def _structure_metrics(a: np.ndarray) -> dict[str, float]:
    """Cheap, deterministic descriptors of the analysis image."""
    x = a.astype(np.float32)

    def corr(u: np.ndarray, v: np.ndarray) -> float:
        u = u.ravel() - u.mean()
        v = v.ravel() - v.mean()
        d = float(np.sqrt((u * u).sum() * (v * v).sum()))
        return float((u * v).sum() / d) if d > 0 else 0.0

    hist = np.histogram(a, bins=32, range=(0, 255))[0].astype(np.float64)
    p = hist / max(hist.sum(), 1.0)
    nz = p[p > 0]
    return {
        "std": float(a.std()),
        "autocorr": min(corr(x[:, :-1], x[:, 1:]), corr(x[:-1, :], x[1:, :])),
        "entropy": float(-(nz * np.log2(nz)).sum()),
    }


def radiograph_structure_check(img: LoadedImage) -> dict:
    """Does this image plausibly contain radiographic structure?

    Returns ``plausible`` plus the measurement that decided it, so a refusal can
    show its working rather than asserting. Only degenerate images fail; see the
    block comment above for the deliberate limits of the claim.
    """
    m = _structure_metrics(img.analysis)
    detail = (f"std {m['std']:.1f}, neighbour correlation {m['autocorr']:.3f}, "
              f"intensity entropy {m['entropy']:.2f} bits")

    # Order matters for the WORDING, not the verdict. A document scan fails both
    # the two-tone and the correlation rule (measured entropy 0.90, autocorr
    # 0.889), and if the correlation rule is asked first the clinician is told
    # "this is noise" about a page of text. The most specific description wins.
    if m["std"] < STRUCTURE_MIN_STD:
        why = (f"the image is essentially blank ({detail}) — a radiograph varies "
               f"far more than this (measured 31.8–61.3 on real films)")
    elif m["entropy"] < STRUCTURE_MIN_ENTROPY:
        why = (f"the image is effectively two-tone ({detail}) — consistent with "
               f"text or a document scan rather than a film")
    elif m["autocorr"] < STRUCTURE_MIN_AUTOCORR:
        why = (f"neighbouring pixels are unrelated ({detail}) — this is noise, "
               f"not an optical image; real films measure above 0.99")
    elif m["entropy"] > STRUCTURE_MAX_ENTROPY and m["autocorr"] > STRUCTURE_RAMP_AUTOCORR:
        why = (f"every intensity is equally likely and the image is perfectly "
               f"smooth ({detail}) — a featureless gradient, not anatomy")
    else:
        return {"plausible": True, "reason": None, "evidence": [detail],
                "measurements": m}

    return {"plausible": False, "reason": why, "evidence": [detail],
            "measurements": m}


def auto_quality_flags(img: LoadedImage) -> tuple[list[str], list[str]]:
    """Deterministic auto-detected quality flags + advisory notes.

    Only flags what can be determined RELIABLY without a validated classifier:
    IMAGE_TOO_SMALL (dimensions) and WRONG_LATERALITY (DICOM laterality). Anything
    diagnostic -- fracture, cast, clipping, deformity, dysplasia, rotation,
    exposure -- is left to clinician declaration; the app does not claim to
    auto-detect it (that needs a validated model; audit P2). Low contrast is an
    advisory NOTE, never a gating flag.

    Acquisition provenance is deliberately NOT a new quality flag. The flag
    vocabulary is a contract pinned to case_input_schema.json, and "how was this
    acquired" is not the same kind of thing as "what is wrong with this film" --
    it already has its own field, `image_domain`. Detection therefore drives
    that field (see detect_acquisition_domain) and lands here only as evidence
    notes.
    """
    flags: list[str] = []
    if img.width < 200 or img.height < 200:
        flags.append("IMAGE_TOO_SMALL")
    if img.laterality and str(img.laterality).upper().startswith("R"):
        flags.append("WRONG_LATERALITY")

    notes: list[str] = list(img.warnings)
    domain = detect_acquisition_domain(img)
    if domain["domain"] == "film_photo":
        notes.extend(domain["evidence"])
    if float(img.analysis.std()) < 12:
        notes.append("low_contrast_or_near_blank")
    return flags, notes


def resolve_image_domain(img: LoadedImage, declared: Optional[str]) -> dict:
    """The domain to treat this image as, and how that was decided.

    Detection DEFAULTS the field; it does not overrule a clinician. If the
    clinician says "photo of a film" the answer is film_photo whatever the
    pixels suggest -- they were in the room. If they declared nothing, or left
    it 'unknown', detection fills it in, which is the whole point: the low-trust
    caveat used to depend on remembering to set a dropdown.

    A declared 'digital_diagnostic' that contradicts high-confidence detection
    is honoured but reported as a conflict, because silently overriding a
    clinician is worse than showing them the disagreement.
    """
    detected = detect_acquisition_domain(img)
    declared = (declared or "").strip().lower() or None
    if declared not in (None, "unknown", "digital_diagnostic", "compressed", "film_photo"):
        declared = None

    conflict = None
    if declared in (None, "unknown"):
        effective = detected["domain"] if detected["auto_detected"] else "unknown"
        source = "auto-detected" if detected["auto_detected"] else "undetermined"
    else:
        effective = declared
        source = "clinician-declared"
        if declared == "digital_diagnostic" and detected["domain"] == "film_photo":
            # Any confidence, not just high. Camera EXIF is routinely stripped by
            # messaging apps -- the phone photo that motivated this had none --
            # so colour alone is usually the whole case, and a true digital
            # export measures a spread of 0.00. Disagreeing with a declaration
            # of "digital diagnostic" is worth showing at that point.
            conflict = (
                "Declared as a digital diagnostic image, but this file shows "
                + " and ".join(detected["evidence"])
                + ". A scanner export does not produce those. Declaration "
                "honoured; check the source."
            )

    return {
        "domain": effective,
        "source": source,
        "declared": declared,
        "detected": detected["domain"],
        "confidence": detected["confidence"],
        "evidence": detected["evidence"],
        "conflict": conflict,
    }


def gate_ai_estimate(auto_flags: list[str], declared_flags: list[str],
                     structure: Optional[dict] = None) -> dict:
    """Combine auto + clinician-declared flags and decide whether a whole-hand AI
    estimate may be shown. Returns a block matching report_output_schema.json's
    image_quality section, plus the hard/soft split and provenance of each flag.

    ``structure`` is the result of :func:`radiograph_structure_check`. A failure
    there blocks the estimate WITHOUT inventing a new quality flag: the flag
    vocabulary is a contract pinned to case_input_schema.json, and "this file is
    not a radiograph" is not a finding about a film -- it is the same kind of
    statement as image_domain, which for the same reason got its own field
    rather than a flag. It is reported in ``structure_ok``/``structure_reason``.
    """
    declared = sorted({f.strip().upper() for f in declared_flags if f and f.strip()})
    known = [f for f in declared if f in CANONICAL_QUALITY_FLAGS]
    unknown = [f for f in declared if f not in CANONICAL_QUALITY_FLAGS]
    all_flags = sorted(set(auto_flags) | set(known))
    hard = sorted(f for f in all_flags if f in HARD_QUALITY_FLAGS)
    soft = sorted(f for f in all_flags if f not in HARD_QUALITY_FLAGS)

    structure_ok = True if structure is None else bool(structure.get("plausible", True))
    accepted = not hard and structure_ok

    if not structure_ok:
        reason = (
            "This file does not look like a radiograph: "
            + str(structure.get("reason"))
            + ". No bone age is shown — check the file, or grade the bones manually."
        )
    elif hard:
        reason = (
            "Image-quality gate failed (" + ", ".join(hard) + "). A whole-hand AI "
            "bone-age estimate is not valid on this film; manual assessment required."
        )
    else:
        reason = None

    return {
        "structure_ok": structure_ok,
        "structure_reason": None if structure_ok else structure.get("reason"),
        "structure_measurements": (structure or {}).get("measurements"),
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

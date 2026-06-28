"""Local bone-age inference helpers.

This module intentionally runs without network access or paid API keys.  The
default estimator is a transparent local baseline, not a validated medical
device model.  It keeps the upload/inference workflow working while leaving a
single integration point for a real trained model later.
"""

from __future__ import annotations

import io
import math
import os
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from PIL import Image, ImageFilter, ImageOps

APP_ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = (
    "Local research estimate only - NOT a certified radiology report. "
    "Verify independently with Greulich-Pyle atlas or TW3 scoring before any "
    "clinical decision."
)


@dataclass(frozen=True)
class ImageFeatures:
    width: int
    height: int
    mean_intensity: float
    contrast: float
    edge_density: float
    dark_fraction: float
    bright_fraction: float
    aspect_ratio: float


def _load_grayscale(image_bytes: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("L")
    width, height = img.size
    max_dim = int(os.environ.get("BONE_AGE_MAX_IMAGE_DIM", "768"))
    scale = max_dim / max(width, height)
    if scale < 1:
        img = img.resize((max(1, int(width * scale)), max(1, int(height * scale))))
    return img


def _image_features(img: Image.Image) -> ImageFeatures:
    pixels = list(img.getdata())
    avg = mean(pixels)
    contrast = pstdev(pixels)
    edge_img = img.filter(ImageFilter.FIND_EDGES)
    edge_pixels = list(edge_img.getdata())
    edge_density = sum(1 for px in edge_pixels if px > 32) / len(edge_pixels)
    dark_fraction = sum(1 for px in pixels if px < 45) / len(pixels)
    bright_fraction = sum(1 for px in pixels if px > 210) / len(pixels)
    width, height = img.size
    return ImageFeatures(
        width=width,
        height=height,
        mean_intensity=avg,
        contrast=contrast,
        edge_density=edge_density,
        dark_fraction=dark_fraction,
        bright_fraction=bright_fraction,
        aspect_ratio=width / max(height, 1),
    )


def _quality_label(features: ImageFeatures) -> str:
    if features.width < 160 or features.height < 160:
        return "suboptimal: image is very small"
    if features.contrast < 18:
        return "suboptimal: low contrast"
    if features.edge_density < 0.035:
        return "suboptimal: limited bony edge signal"
    if features.aspect_ratio > 1.6 or features.aspect_ratio < 0.35:
        return "suboptimal: unusual hand-wrist framing"
    return "adequate"


def _parse_age(chronological_age: str) -> float | None:
    try:
        value = float(chronological_age)
    except (TypeError, ValueError):
        return None
    if math.isfinite(value) and 0 < value <= 25:
        return value
    return None


def _sex_bias(sex: str) -> float:
    if sex == "girls":
        return 0.15
    if sex == "boys":
        return -0.05
    return 0.0


def _baseline_estimate(features: ImageFeatures, sex: str, chronological_age: str) -> float:
    chrono = _parse_age(chronological_age)

    if chrono is None:
        # A weak image-only fallback. Pediatric bone-age films are normally
        # interpreted with age and sex context; without age this is deliberately
        # conservative and low-confidence.
        texture = min(max((features.edge_density - 0.04) / 0.18, 0.0), 1.0)
        density = min(max((features.bright_fraction - 0.04) / 0.38, 0.0), 1.0)
        return round(2.0 + (0.65 * texture + 0.35 * density) * 14.0 + _sex_bias(sex), 1)

    contrast_term = min(max((features.contrast - 35) / 80, -1.0), 1.0)
    edge_term = min(max((features.edge_density - 0.08) / 0.16, -1.0), 1.0)
    exposure_term = min(max((features.mean_intensity - 120) / 90, -1.0), 1.0)
    adjustment = 0.45 * contrast_term + 0.35 * edge_term + 0.20 * exposure_term
    estimate = chrono + adjustment + _sex_bias(sex)
    return round(min(max(estimate, 0.5), 19.0), 1)


def _confidence(features: ImageFeatures, chronological_age: str) -> str:
    if _parse_age(chronological_age) is None:
        return "low"
    if _quality_label(features) != "adequate":
        return "low"
    return "low"


def _model_status() -> dict[str, Any]:
    local_model_path = os.environ.get("LOCAL_BONE_AGE_MODEL_PATH", "").strip()
    if not local_model_path:
        return {
            "kind": "local_baseline",
            "configured": True,
            "trained_weights_loaded": False,
            "path": None,
        }

    path = Path(local_model_path)
    return {
        "kind": "external_local_model",
        "configured": path.exists(),
        "trained_weights_loaded": path.exists(),
        "path": str(path),
    }


def model_status() -> dict[str, Any]:
    return _model_status()


def predict_bone_age(image_bytes: bytes, sex: str, chronological_age: str) -> dict[str, Any]:
    img = _load_grayscale(image_bytes)
    features = _image_features(img)
    status = _model_status()

    if status["trained_weights_loaded"]:
        # A real trained local model can be wired here when weights are
        # available.  Keeping this explicit avoids silently pretending that a
        # generic image heuristic is a validated RSNA-trained network.
        raise RuntimeError(
            "LOCAL_BONE_AGE_MODEL_PATH is set, but this build does not yet include "
            "a runtime adapter for that model file."
        )

    estimate = _baseline_estimate(features, sex, chronological_age)
    quality = _quality_label(features)
    return {
        "bone_age_years": estimate,
        "confidence": _confidence(features, chronological_age),
        "key_findings": (
            "Local baseline used image contrast, bony-edge signal, exposure, sex, "
            "and chronological-age context; replace with trained weights for accuracy."
        ),
        "image_quality": quality,
        "model": "local-baseline-v1",
        "method": "Local baseline estimator; not Greulich-Pyle/TW3 validated",
        "disclaimer": DISCLAIMER,
        "local": True,
        "trained_weights_loaded": False,
        "features": {
            "width": features.width,
            "height": features.height,
            "contrast": round(features.contrast, 2),
            "edge_density": round(features.edge_density, 4),
        },
    }


def make_synthetic_hand_xray() -> bytes:
    """Create a deterministic test image for endpoint health checks."""
    img = Image.new("L", (360, 520), color=18)
    # Palm/metacarpals
    for x in [112, 148, 184, 220, 256]:
        for y in range(160, 390):
            radius = 8 if y < 300 else 11
            for dx in range(-radius, radius + 1):
                if dx * dx <= radius * radius:
                    img.putpixel((x + dx, y), 205)
    # Phalanges
    for x, length in [(105, 140), (145, 180), (185, 195), (225, 175), (265, 135)]:
        for y in range(55, 55 + length):
            radius = 7
            for dx in range(-radius, radius + 1):
                if dx * dx <= radius * radius:
                    img.putpixel((x + dx, y), 215)
    # Carpal cluster and distal radius/ulna
    for cx, cy, r in [(150, 410, 18), (190, 420, 16), (225, 408, 14), (170, 452, 20), (245, 455, 16)]:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img.putpixel((x, y), 210)
    for x in range(145, 183):
        for y in range(450, 515):
            img.putpixel((x, y), 200)
    for x in range(218, 246):
        for y in range(455, 515):
            img.putpixel((x, y), 195)

    img = img.filter(ImageFilter.GaussianBlur(radius=1.1))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

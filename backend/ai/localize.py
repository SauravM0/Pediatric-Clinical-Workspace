"""CPU bone-localization inference — PEA (Point Estimation of Anchor), ONNX.

Follows the PEA module of PEARLS (Zhang et al., J. Digital Imaging 2023): predict a
center point per RUS bone as a heatmap peak, refine with a sub-pixel offset, and
derive a square ROI around it. Used to auto-crop the 13 bones so the doctor
confirms/nudges instead of hunting — and to feed crops to the (future) staging AI.

Runtime here is pure numpy + onnxruntime (no torch). If no model is installed the
functions return None (honest degradation — the manual workflow is unaffected).
Decoding MUST match training (backend/ai/train_localizer.py).
"""

from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from backend.tw3 import RUS_BONES

_MODELS_DIR = Path(__file__).with_name("models")
MODEL_PATH = _MODELS_DIR / "localizer.onnx"
META_PATH = _MODELS_DIR / "localizer.json"

IMG_SIZE = 512          # network input (paper uses 512)
STRIDE = 4              # heatmap is IMG_SIZE / STRIDE per side
DEFAULT_BOX_FRAC = 0.16  # ROI side as a fraction of the image (doctor adjusts)
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def model_available() -> bool:
    return MODEL_PATH.exists()


def model_metadata() -> Optional[dict]:
    if META_PATH.exists():
        try:
            return json.loads(META_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _point_names() -> list[str]:
    """Bone code per output channel (from metadata, else the canonical 13 RUS)."""
    meta = model_metadata() or {}
    names = meta.get("point_names")
    return list(names) if names else list(RUS_BONES)


def preprocess(image: Image.Image | bytes, size: int = IMG_SIZE):
    """Return (1x3xNxN float32 tensor, orig_w, orig_h). Resized ignoring aspect
    ratio (points are mapped back per-axis at decode time)."""
    if isinstance(image, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image))
    image = ImageOps.exif_transpose(image).convert("L")
    orig_w, orig_h = image.size
    img = image.resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = np.stack([arr, arr, arr], axis=-1)
    arr = (arr - _MEAN) / _STD
    arr = np.transpose(arr, (2, 0, 1))[np.newaxis].astype(np.float32)
    return arr, orig_w, orig_h


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def decode(heatmap: np.ndarray, offset: np.ndarray, orig_w: int, orig_h: int,
           *, box_frac: float = DEFAULT_BOX_FRAC, names: Optional[list[str]] = None) -> list[dict]:
    """Heatmap[C,h,w] + offset[2,h,w] → one center point + ROI box per channel,
    in ORIGINAL image pixels. Single instance per bone (per-channel argmax)."""
    if heatmap.ndim == 4:
        heatmap, offset = heatmap[0], offset[0]
    C, h, w = heatmap.shape
    prob = _sigmoid(heatmap)
    names = names or _point_names()
    # heatmap cell → original pixels (combines stride + resize back)
    sx, sy = orig_w / w, orig_h / h
    side = box_frac * (orig_w + orig_h) / 2.0
    out: list[dict] = []
    for c in range(C):
        flat = int(np.argmax(prob[c]))
        py, px = divmod(flat, w)
        off_x = float(offset[0, py, px]) if offset.shape[0] >= 1 else 0.0
        off_y = float(offset[1, py, px]) if offset.shape[0] >= 2 else 0.0
        cx = (px + off_x) * sx
        cy = (py + off_y) * sy
        x0, y0 = cx - side / 2, cy - side / 2
        x1, y1 = cx + side / 2, cy + side / 2
        out.append({
            "bone_code": names[c] if c < len(names) else f"pt{c}",
            "cx": round(cx, 1), "cy": round(cy, 1),
            "box": [round(max(0.0, x0), 1), round(max(0.0, y0), 1),
                    round(min(float(orig_w), x1), 1), round(min(float(orig_h), y1), 1)],
            "confidence": round(float(prob[c, py, px]), 4),
        })
    return out


@lru_cache(maxsize=1)
def _session():
    import onnxruntime as ort

    return ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])


def predict_boxes(image: Image.Image | bytes) -> Optional[dict]:
    """Auto-localize the RUS bones, or None if no model is installed."""
    if not model_available():
        return None
    meta = model_metadata() or {}
    x, orig_w, orig_h = preprocess(image, int(meta.get("input_size", IMG_SIZE)))
    sess = _session()
    outs = sess.run(None, {sess.get_inputs()[0].name: x})
    # outputs: heatmap, offset (by name if present, else positional)
    named = {o.name: v for o, v in zip(sess.get_outputs(), outs)}
    heatmap = named.get("heatmap", outs[0])
    offset = named.get("offset", outs[1] if len(outs) > 1 else np.zeros((1, 2, *heatmap.shape[-2:]), np.float32))
    boxes = decode(np.asarray(heatmap), np.asarray(offset), orig_w, orig_h,
                   box_frac=float(meta.get("box_frac", DEFAULT_BOX_FRAC)))
    return {
        "model_version": meta.get("model_version", "localizer-unknown"),
        "input_size": int(meta.get("input_size", IMG_SIZE)),
        "boxes": boxes,
    }

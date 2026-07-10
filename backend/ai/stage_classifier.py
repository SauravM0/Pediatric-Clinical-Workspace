"""Per-bone TW3 stage classifier inference — PEARLS RL module, ONNX/CPU.

Given a CROP of one bone, predict its maturity stage (A–I) with an ordinal model
that respects stage order. One model file per bone under models/stager/. This is
the AI that would auto-fill the per-bone stages the doctor confirms.

Honest degradation: if no model is installed for a bone, returns None — the doctor
stages that bone manually. Runtime is pure numpy + onnxruntime (no torch).
Preprocessing MUST match training (backend/ai/train_stager.py).
"""

from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from backend.tw3 import LETTER_STAGES

_DIR = Path(__file__).with_name("models") / "stager"
IMG_SIZE = 128
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _model_path(bone: str) -> Path:
    return _DIR / f"{bone}.onnx"


def _meta_path(bone: str) -> Path:
    return _DIR / f"{bone}.json"


def model_available(bone: str) -> bool:
    return _model_path(bone).exists()


def available_bones() -> list[str]:
    if not _DIR.exists():
        return []
    return sorted(p.stem for p in _DIR.glob("*.onnx"))


def model_metadata(bone: str) -> Optional[dict]:
    p = _meta_path(bone)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def preprocess(image: Image.Image | bytes, size: int = IMG_SIZE) -> np.ndarray:
    """Bone crop → normalised 1x3xNxN float32 tensor (same as training)."""
    if isinstance(image, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image))
    img = ImageOps.exif_transpose(image).convert("L").resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = np.stack([arr, arr, arr], axis=-1)
    arr = (arr - _MEAN) / _STD
    arr = np.transpose(arr, (2, 0, 1))[np.newaxis]
    return arr.astype(np.float32)


@lru_cache(maxsize=24)
def _session(bone: str):
    import onnxruntime as ort

    return ort.InferenceSession(str(_model_path(bone)), providers=["CPUExecutionProvider"])


def predict_stage(image: Image.Image | bytes, bone_code: str) -> Optional[dict]:
    """Predict a bone's maturity stage from its crop, or None if no model installed.

    Returns top stage, second stage, per-stage probabilities and a confidence.
    Softmax/ordinal probability is NOT calibrated confidence — treat as a suggestion.
    """
    if not model_available(bone_code):
        return None
    meta = model_metadata(bone_code) or {}
    stages = meta.get("stages") or list(LETTER_STAGES)
    x = preprocess(image, int(meta.get("input_size", IMG_SIZE)))
    sess = _session(bone_code)
    probs = np.asarray(sess.run(None, {sess.get_inputs()[0].name: x})[0]).reshape(-1)
    probs = np.clip(probs, 1e-9, None)
    probs = probs / probs.sum()
    order = np.argsort(probs)[::-1]
    top = int(order[0])
    second = int(order[1]) if probs.size > 1 else top
    return {
        "bone_code": bone_code,
        "stage": stages[top] if top < len(stages) else str(top),
        "confidence": round(float(probs[top]), 4),
        "second_stage": stages[second] if second < len(stages) else None,
        "probabilities": {
            (stages[i] if i < len(stages) else str(i)): round(float(probs[i]), 4)
            for i in range(probs.size)
        },
        "model_version": meta.get("model_version", "stager-unknown"),
        "n_train": meta.get("n_train"),
    }

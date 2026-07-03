"""CPU bone-age screening inference (ONNX Runtime).

Whole-image Greulich-Pyle-style estimate from a hand radiograph + sex. Loaded
lazily; if no model file is present the app simply reports the estimate as
unavailable (honest degradation — the manual TW3 path is unaffected).

Preprocessing here MUST match training (backend/ai/train_boneage.py).
"""

from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

_MODELS_DIR = Path(__file__).with_name("models")
MODEL_PATH = _MODELS_DIR / "boneage_gp.onnx"
META_PATH = _MODELS_DIR / "boneage_gp.json"

IMG_SIZE = 160
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(image: Image.Image | bytes) -> np.ndarray:
    """Grayscale hand image → normalised 1x3x160x160 float32 tensor."""
    if isinstance(image, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image))
    img = ImageOps.exif_transpose(image).convert("L").resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = np.stack([arr, arr, arr], axis=-1)  # 3 channels
    arr = (arr - _MEAN) / _STD
    arr = np.transpose(arr, (2, 0, 1))  # CHW
    return arr[np.newaxis, :, :, :].astype(np.float32)


def model_metadata() -> Optional[dict]:
    if META_PATH.exists():
        try:
            return json.loads(META_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def model_available() -> bool:
    return MODEL_PATH.exists()


@lru_cache(maxsize=1)
def _session():
    import onnxruntime as ort

    return ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])


def predict_months(image: Image.Image | bytes, is_male: bool) -> Optional[dict]:
    """Return the screening estimate, or None if no model is installed."""
    if not model_available():
        return None
    sess = _session()
    x = preprocess(image)
    sex = np.array([[1.0 if is_male else 0.0]], dtype=np.float32)
    inputs = {i.name: v for i, v in zip(sess.get_inputs(), (x, sex))}
    months = float(sess.run(None, inputs)[0].reshape(-1)[0])
    months = max(0.0, min(months, 240.0))
    meta = model_metadata() or {}
    return {
        "bone_age_months": round(months),
        "bone_age_years": round(months / 12, 1),
        "model_version": meta.get("model_version", "boneage-gp-unknown"),
        "method": "Greulich-Pyle whole-image estimate (screening, not TW3)",
        "val_mae_months": meta.get("val_mae_months"),
    }

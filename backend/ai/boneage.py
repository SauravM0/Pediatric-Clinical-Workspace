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


def preprocess(image: Image.Image | bytes, size: int | None = None) -> np.ndarray:
    """Grayscale hand image → normalised 1x3xNxN float32 tensor (N = model input)."""
    if isinstance(image, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image))
    n = size or IMG_SIZE
    img = ImageOps.exif_transpose(image).convert("L").resize((n, n))
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
    meta = model_metadata() or {}
    # Run the pipeline the MODEL declares, not whatever is globally current
    # (M4.1/M4.2). A model is only valid with the preprocessing it was trained
    # under, so the model chooses -- the registry then decides whether its
    # calibrated intervals are still usable.
    from . import preprocess as _prep
    from . import registry as _registry

    spec = _registry.load_spec()
    size = int(meta.get("input_size", IMG_SIZE))
    version = spec.preprocessing_version if spec else _prep.PREPROCESSING_V1
    x = _prep.run(image, size, version).tensor
    policy = _registry.resolve_interval_policy(spec)
    sex = np.array([[1.0 if is_male else 0.0]], dtype=np.float32)
    inputs = {i.name: v for i, v in zip(sess.get_inputs(), (x, sex))}
    months = float(sess.run(None, inputs)[0].reshape(-1)[0])
    months = max(0.0, min(months, 240.0))

    # Patient-level uncertainty (directive S-BA-5). Prefer a split-CONFORMAL
    # interval calibrated on the held-out val set (guaranteed >= coverage), which
    # boneage.calibrate_conformal writes into the metadata. Fall back to a plain
    # +/-MAE band ONLY when no conformal calibration is present -- and label it as
    # an approximation, never a calibrated interval.
    from . import conformal as _conformal

    mae = meta.get("val_mae_months")
    # Prefer a subgroup-conditional (Mondrian) conformal interval when calibrated,
    # else a marginal conformal interval, else a labelled +/-MAE approximation
    # (directive S-BA-5 / Plan 3 WI-3). Pure selection -- see conformal.select_interval.
    sel = _conformal.select_interval(meta, is_male, months)
    interval_kind, half, coverage = sel["kind"], sel["half"], sel["coverage"]
    if not policy.conformal_allowed and interval_kind.startswith("conformal"):
        # Preprocessing changed since calibration: the quantile no longer
        # delivers its nominal coverage, so the interval is withdrawn rather
        # than served with a coverage claim it cannot honour (M4.1).
        interval_kind, half, coverage = "withheld_pipeline_mismatch", None, None
    ci_low_months, ci_high_months = _conformal.interval(months, half)

    return {
        "bone_age_months": round(months),
        "bone_age_years": round(months / 12, 1),
        "model_version": meta.get("model_version", "boneage-gp-unknown"),
        "method": "Greulich-Pyle whole-image estimate (screening, not TW3)",
        "val_mae_months": mae,
        "uncertainty_months": None if half is None else round(half, 1),
        "interval_kind": interval_kind,   # "conformal_grouped" | "conformal" | "mae_approx" | "none"
        "interval_coverage": coverage,    # e.g. "0.90" for a conformal interval
        "interval_group": sel["group"],   # e.g. "boys:>8-12y" when subgroup-calibrated
        "interval_group_fallback": sel["fallback"],  # True if the group fell back to marginal
        "ci_low_years": None if ci_low_months is None else round(ci_low_months / 12, 1),
        "ci_high_years": None if ci_high_months is None else round(ci_high_months / 12, 1),
        "population_note": (
            "Model trained on the RSNA (US) dataset, not India-calibrated. Published "
            "data show Greulich-Pyle skeletal age runs ~0.5-0.7 yr delayed in Indian "
            "children (more in boys). Treat as a screening suggestion; confirm with TW3."
        ),
        "trained_on": meta.get("trained_on"),
        "preprocessing_version": version,
        "conformal_allowed": policy.conformal_allowed,
        "conformal_status": policy.reason,
    }

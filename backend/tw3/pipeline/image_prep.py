"""
Image preparation for training/inference: DICOM/PNG -> normalized grayscale PNG.

Kept dependency-guarded on purpose: this environment has no imaging libraries, so
these functions raise a clear, actionable error until you install the extras
(see requirements-ml.txt). The data/label layer works without them.
"""
from __future__ import annotations
from pathlib import Path

_MISSING = (
    "Image preparation needs 'pydicom' + 'pillow' + 'numpy'. "
    "Install with:  pip install -r backend/tw3/requirements-ml.txt"
)


def load_image(path: str):
    """Load a DICOM (.dcm) or standard image → 2D numpy array (float, 0..1)."""
    p = Path(path)
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(_MISSING) from exc

    if p.suffix.lower() == ".dcm":
        try:
            import pydicom
        except Exception as exc:
            raise RuntimeError(_MISSING) from exc
        arr = pydicom.dcmread(str(p)).pixel_array.astype("float32")
    else:
        try:
            from PIL import Image
        except Exception as exc:
            raise RuntimeError(_MISSING) from exc
        arr = np.asarray(Image.open(p).convert("L"), dtype="float32")

    lo, hi = arr.min(), arr.max()
    return (arr - lo) / (hi - lo + 1e-6)


def preprocess(path: str, size: int = 512):
    """Load + resize to (size, size) for a model. Returns a numpy array."""
    from PIL import Image  # noqa: local import, guarded by load_image message
    import numpy as np
    arr = load_image(path)
    img = Image.fromarray((arr * 255).astype("uint8")).resize((size, size))
    return np.asarray(img, dtype="float32") / 255.0

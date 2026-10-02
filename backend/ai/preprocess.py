"""Versioned image preprocessing for bone-age inference (M4.2).

Two pipelines live here, and both are kept forever:

* ``prep-1.0-minmax`` reproduces exactly what the incumbent model was trained
  and calibrated with -- grayscale, resize, divide by 255, ImageNet
  normalisation (``train_boneage._load_all_images``). Despite the version name
  there is NO min/max contrast stretch; an earlier docstring said there was.
  It is not deleted when a better one arrives, because a model is only valid
  with the preprocessing it saw during training. A stored conformal quantile is
  a property of *model + pipeline*, not of the model alone.
* ``prep-2.0-clahe-seg`` is the improved pipeline: percentile windowing, CLAHE,
  hand segmentation with background suppression, and rotation normalisation.

Why percentile windowing replaces global min/max: min/max is destroyed by a
single outlier pixel. One bright annotation marker, a collimator edge, or a hot
pixel compresses the entire diagnostic range of the hand into a fraction of the
output scale. Clipping to the 1st/99th percentile is robust to both.

**Version binding is the safety property.** ``registry.py`` refuses to serve a
conformal interval when the active pipeline's version does not match the one the
model's quantiles were computed under. Without that, changing preprocessing
silently degrades interval coverage with no signal at all -- the numbers keep
coming out, they are just quietly wrong.

No OpenCV: CLAHE and connected components are implemented on numpy/scipy so the
dependency set stays as it is. The implementations are tested against their
defining properties rather than against a reference library.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

PREPROCESSING_V1 = "prep-1.0-minmax"
PREPROCESSING_V2 = "prep-2.0-clahe-seg"
CURRENT_PREPROCESSING = PREPROCESSING_V1

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass(frozen=True)
class PreprocessResult:
    tensor: np.ndarray
    version: str
    notes: tuple[str, ...] = ()


# ── primitives ──────────────────────────────────────────────────────────────

def percentile_window(arr: np.ndarray, low: float = 1.0, high: float = 99.0) -> np.ndarray:
    """Clip to a percentile window and rescale to [0, 1].

    Robust replacement for global min/max: a single saturated pixel cannot
    compress the rest of the image.
    """
    lo, hi = np.percentile(arr, [low, high])
    if hi - lo < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr.astype(np.float32) - lo) / (hi - lo), 0.0, 1.0)


def clahe(arr: np.ndarray, *, tiles: int = 8, clip_limit: float = 2.0) -> np.ndarray:
    """Contrast-limited adaptive histogram equalisation on a [0,1] array.

    Per-tile histograms are clipped at ``clip_limit`` x the mean bin count and
    the excess is redistributed, which is what stops plain adaptive
    equalisation from amplifying noise in flat regions. Tile transforms are
    bilinearly interpolated so no tile boundary appears in the output.
    """
    h, w = arr.shape
    bins = 256
    quantised = np.clip((arr * (bins - 1)).astype(np.int32), 0, bins - 1)

    ty, tx = max(1, h // tiles), max(1, w // tiles)
    n_y, n_x = max(1, h // ty), max(1, w // tx)

    luts = np.zeros((n_y, n_x, bins), dtype=np.float32)
    for iy in range(n_y):
        for ix in range(n_x):
            y0, y1 = iy * ty, (iy + 1) * ty if iy < n_y - 1 else h
            x0, x1 = ix * tx, (ix + 1) * tx if ix < n_x - 1 else w
            tile = quantised[y0:y1, x0:x1]
            hist = np.bincount(tile.ravel(), minlength=bins).astype(np.float32)

            limit = clip_limit * hist.sum() / bins
            excess = np.maximum(hist - limit, 0).sum()
            hist = np.minimum(hist, limit) + excess / bins

            cdf = np.cumsum(hist)
            cdf = (cdf - cdf[0]) / max(cdf[-1] - cdf[0], 1e-6)
            luts[iy, ix] = cdf

    # Map every pixel through its tile LUT, then bilinearly blend between the
    # four surrounding tile centres.
    yy = np.clip((np.arange(h) - ty / 2) / ty, 0, n_y - 1)
    xx = np.clip((np.arange(w) - tx / 2) / tx, 0, n_x - 1)
    y0 = np.floor(yy).astype(int); y1 = np.minimum(y0 + 1, n_y - 1)
    x0 = np.floor(xx).astype(int); x1 = np.minimum(x0 + 1, n_x - 1)
    wy = (yy - y0)[:, None]; wx = (xx - x0)[None, :]

    def take(iy, ix):
        return luts[iy[:, None], ix[None, :], quantised]

    out = ((1 - wy) * (1 - wx) * take(y0, x0)
           + (1 - wy) * wx * take(y0, x1)
           + wy * (1 - wx) * take(y1, x0)
           + wy * wx * take(y1, x1))
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _otsu(arr: np.ndarray) -> float:
    hist, edges = np.histogram(arr, bins=256, range=(0.0, 1.0))
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total == 0:
        return 0.5
    omega = np.cumsum(hist) / total
    mids = (edges[:-1] + edges[1:]) / 2
    mu = np.cumsum(hist * mids) / total
    mu_t = mu[-1]
    denom = omega * (1 - omega)
    with np.errstate(divide="ignore", invalid="ignore"):
        sigma_b = np.where(denom > 1e-12, (mu_t * omega - mu) ** 2 / denom, 0.0)
    return float(mids[int(np.nanargmax(sigma_b))])


def segment_hand(arr: np.ndarray) -> tuple[np.ndarray, bool]:
    """Largest bright connected component as a boolean mask.

    Returns ``(mask, ok)``. **Fails open**: if no plausible component is found
    the mask is all-True and ``ok`` is False, so the caller proceeds on the
    unsegmented image. A segmentation bug must never feed a black frame to the
    model and get back a confident wrong age.
    """
    threshold = _otsu(arr)
    binary = arr > threshold
    binary = ndimage.binary_opening(binary, np.ones((3, 3)))
    labels, count = ndimage.label(binary)
    if count == 0:
        return np.ones_like(arr, dtype=bool), False

    sizes = ndimage.sum(binary, labels, range(1, count + 1))
    largest = int(np.argmax(sizes)) + 1
    mask = labels == largest

    # A hand should occupy a substantial share of a hand radiograph. Anything
    # tiny or near-total means the threshold found something else.
    fraction = mask.mean()
    if not (0.05 <= fraction <= 0.95):
        return np.ones_like(arr, dtype=bool), False

    mask = ndimage.binary_fill_holes(mask)
    mask = ndimage.binary_closing(mask, np.ones((5, 5)))
    return mask, True


def rotation_angle(mask: np.ndarray) -> float:
    """Principal-axis angle in degrees needed to stand the hand upright."""
    ys, xs = np.nonzero(mask)
    if len(xs) < 10:
        return 0.0
    coords = np.stack([xs - xs.mean(), ys - ys.mean()])
    cov = np.cov(coords)
    if not np.all(np.isfinite(cov)):
        return 0.0
    _, vecs = np.linalg.eigh(cov)
    major = vecs[:, -1]
    angle = np.degrees(np.arctan2(major[1], major[0]))
    return float(90.0 - angle if angle >= 0 else -90.0 - angle)


# ── pipelines ───────────────────────────────────────────────────────────────

def _to_gray(image: Image.Image | bytes) -> Image.Image:
    if isinstance(image, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image))
    return ImageOps.exif_transpose(image).convert("L")


def _to_tensor(arr01: np.ndarray) -> np.ndarray:
    rgb = np.stack([arr01, arr01, arr01], axis=-1)
    rgb = (rgb - _MEAN) / _STD
    return np.transpose(rgb, (2, 0, 1))[np.newaxis].astype(np.float32)


def preprocess_v1(image: Image.Image | bytes, size: int) -> PreprocessResult:
    """Exactly the incumbent pipeline. Do not 'improve' this in place -- the
    deployed model's weights and conformal quantiles both assume it."""
    img = _to_gray(image).resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return PreprocessResult(_to_tensor(arr), PREPROCESSING_V1)


def preprocess_v2(image: Image.Image | bytes, size: int, *,
                  use_clahe: bool = True, use_segmentation: bool = True,
                  use_rotation: bool = True) -> PreprocessResult:
    """Percentile window -> CLAHE -> segment -> rotate -> pad square -> resize."""
    notes: list[str] = []
    arr = np.asarray(_to_gray(image), dtype=np.float32)
    arr = percentile_window(arr)

    if use_clahe:
        arr = clahe(arr)

    mask = np.ones_like(arr, dtype=bool)
    if use_segmentation:
        mask, ok = segment_hand(arr)
        if ok:
            arr = arr * mask
        else:
            notes.append("segmentation_failed_open")

    if use_rotation and mask.any():
        angle = rotation_angle(mask)
        if abs(angle) > 5.0:
            arr = ndimage.rotate(arr, angle, reshape=True, order=1, mode="constant", cval=0.0)
            notes.append(f"rotated_{angle:.1f}deg")

    # Pad to square before resizing so the hand's aspect ratio is preserved --
    # a non-square resize distorts bone lengths, which is the signal.
    h, w = arr.shape
    side = max(h, w)
    square = np.zeros((side, side), dtype=np.float32)
    square[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = arr

    resized = np.asarray(
        Image.fromarray((np.clip(square, 0, 1) * 255).astype(np.uint8)).resize((size, size)),
        dtype=np.float32) / 255.0
    return PreprocessResult(_to_tensor(resized), PREPROCESSING_V2, tuple(notes))


_PIPELINES = {PREPROCESSING_V1: preprocess_v1, PREPROCESSING_V2: preprocess_v2}


def available_versions() -> tuple[str, ...]:
    return tuple(_PIPELINES)


def run(image: Image.Image | bytes, size: int, version: str) -> PreprocessResult:
    if version not in _PIPELINES:
        raise ValueError(
            f"unknown preprocessing version {version!r}; known: {', '.join(_PIPELINES)}"
        )
    return _PIPELINES[version](image, size)

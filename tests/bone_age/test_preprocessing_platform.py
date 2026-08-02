"""Preprocessing pipelines, model registry, and the calibration binding (M4).

The headline result this suite exists to protect: the improved pipeline makes
the INCUMBENT model dramatically worse, because that model was trained and
calibrated under the original one. See test_v2_must_not_be_switched_on_for_the
_incumbent_model for the measured numbers.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from backend.ai import preprocess, registry


def _hand_like(size: int = 256, *, bright_marker: bool = False) -> Image.Image:
    """A crude hand-ish bright blob on a dark field."""
    arr = np.zeros((size, size), dtype=np.float32)
    arr[60:210, 100:160] = 0.6                      # palm
    for i, x in enumerate(range(100, 160, 12)):     # fingers
        arr[20 + i * 3:70, x:x + 7] = 0.7
    arr += np.random.default_rng(0).normal(0, 0.01, arr.shape)
    if bright_marker:
        arr[5:12, 5:12] = 50.0                      # saturated annotation marker
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))


# ── percentile windowing ────────────────────────────────────────────────────

def _raw_hand(*, marker_value: float | None = None) -> np.ndarray:
    """A raw float radiograph-like array, NOT round-tripped through uint8.

    The round-trip is what a real 12/16-bit DICOM does not do: a hot pixel or a
    bright annotation really can sit orders of magnitude above the tissue range,
    which is exactly the case min/max scaling mishandles.
    """
    arr = np.full((128, 128), 200.0, dtype=np.float32)          # dark background
    arr[30:100, 45:85] = 1400.0                                  # hand tissue
    arr[35:95, 50:80] += np.random.default_rng(3).normal(0, 60, (60, 30))
    if marker_value is not None:
        arr[2:6, 2:6] = marker_value                             # saturated marker
    return arr


def test_percentile_window_is_robust_to_a_single_bright_marker():
    """The reason global min/max was replaced: one saturated pixel compresses
    the whole diagnostic range of the hand into a sliver of the output scale."""
    clean = _raw_hand()
    marked = _raw_hand(marker_value=60000.0)
    # Select the tissue SPATIALLY. A brightness threshold would also select the
    # marker itself, and then the statistic measures the marker's own spread
    # rather than the contrast available across the hand.
    tissue = np.zeros_like(marked, dtype=bool)
    tissue[35:95, 50:80] = True

    minmax = (marked - marked.min()) / (marked.max() - marked.min())
    windowed = preprocess.percentile_window(marked)
    reference = preprocess.percentile_window(clean)

    assert minmax[tissue].std() < 0.01, "the synthetic outlier did not crush min/max"
    assert windowed[tissue].std() > minmax[tissue].std() * 5, (
        "percentile windowing did not restore contrast lost to the outlier"
    )
    # And it lands close to the un-marked image: the marker is ignored, not merely survived.
    assert abs(windowed[tissue].mean() - reference[tissue].mean()) < 0.15


def test_percentile_window_outputs_unit_range():
    out = preprocess.percentile_window(np.asarray(_hand_like(), dtype=np.float32))
    assert 0.0 <= out.min() and out.max() <= 1.0


def test_percentile_window_handles_a_blank_image():
    assert preprocess.percentile_window(np.full((32, 32), 7.0, dtype=np.float32)).max() == 0.0


# ── CLAHE ───────────────────────────────────────────────────────────────────

def test_clahe_increases_local_contrast():
    """Measured WITHIN the tissue region. Global std is the wrong statistic on a
    mostly-black frame -- CLAHE redistributes locally, and a large dark
    background can dominate a whole-image spread either way."""
    arr = preprocess.percentile_window(_raw_hand())
    out = preprocess.clahe(arr)
    tissue = arr > 0.5
    assert out[tissue].std() > arr[tissue].std(), "no local contrast gain in the tissue"
    assert 0.0 <= out.min() and out.max() <= 1.0


def test_clahe_clip_limit_bounds_amplification():
    """Contrast-LIMITED: a lower clip limit must amplify less. Without the limit
    this is plain adaptive equalisation, which blows up noise in flat regions."""
    arr = preprocess.percentile_window(_raw_hand())
    gentle = preprocess.clahe(arr, clip_limit=1.0)
    aggressive = preprocess.clahe(arr, clip_limit=8.0)
    tissue = arr > 0.5
    assert gentle[tissue].std() <= aggressive[tissue].std() + 1e-6


def test_clahe_leaves_no_tile_seams():
    """Tile transforms are bilinearly blended; a visible grid would mean the
    interpolation is wrong and would show as structure the model can latch onto."""
    arr = np.full((128, 128), 0.5, dtype=np.float32)
    arr += np.random.default_rng(1).normal(0, 0.05, arr.shape)
    out = preprocess.clahe(np.clip(arr, 0, 1), tiles=8)
    col_jumps = np.abs(np.diff(out.mean(axis=0)))
    assert col_jumps.max() < 10 * np.median(col_jumps) + 0.05


# ── segmentation ────────────────────────────────────────────────────────────

def test_segmentation_finds_the_hand():
    arr = preprocess.percentile_window(np.asarray(_hand_like(), dtype=np.float32))
    mask, ok = preprocess.segment_hand(arr)
    assert ok and 0.05 < mask.mean() < 0.95


def test_segmentation_fails_open_on_a_blank_image():
    """A segmentation bug must never feed a black frame to the model and get
    back a confident wrong age."""
    mask, ok = preprocess.segment_hand(np.zeros((64, 64), dtype=np.float32))
    assert ok is False
    assert mask.all(), "failing closed would blank the image"


def test_segmentation_fails_open_when_the_component_is_implausible():
    arr = np.zeros((64, 64), dtype=np.float32)
    arr[0:2, 0:2] = 1.0        # a speck, not a hand
    mask, ok = preprocess.segment_hand(arr)
    assert ok is False and mask.all()


def test_rotation_angle_is_zero_for_an_upright_hand():
    arr = preprocess.percentile_window(np.asarray(_hand_like(), dtype=np.float32))
    mask, _ = preprocess.segment_hand(arr)
    assert abs(preprocess.rotation_angle(mask)) < 20.0


# ── pipelines ───────────────────────────────────────────────────────────────

def test_v1_reproduces_the_incumbent_preprocessing_exactly():
    """v1 must not drift: the deployed weights and conformal quantiles both
    assume it. Compared against the original implementation in boneage.py."""
    from backend.ai import boneage

    img = _hand_like()
    assert np.allclose(preprocess.preprocess_v1(img, 224).tensor,
                       boneage.preprocess(img, 224), atol=1e-6)


@pytest.mark.parametrize("version", preprocess.available_versions())
def test_every_pipeline_returns_a_model_shaped_tensor(version):
    r = preprocess.run(_hand_like(), 224, version)
    assert r.tensor.shape == (1, 3, 224, 224)
    assert r.tensor.dtype == np.float32
    assert r.version == version


def test_v2_preserves_aspect_ratio_by_padding():
    """A non-square resize distorts bone lengths, which are the signal."""
    tall = Image.fromarray(
        (np.asarray(_hand_like(), dtype=np.float32)[:, 60:200]).astype(np.uint8))
    assert preprocess.run(tall, 224, preprocess.PREPROCESSING_V2).tensor.shape == (1, 3, 224, 224)


def test_unknown_pipeline_version_is_rejected():
    with pytest.raises(ValueError, match="unknown preprocessing version"):
        preprocess.run(_hand_like(), 224, "prep-99")


# ── the measured finding ────────────────────────────────────────────────────

def test_v2_must_not_be_switched_on_for_the_incumbent_model():
    """Measured on 200 images of the locked RSNA test set (seed 42):

        prep-1.0-minmax      MAE  8.92 mo   75.5% within 12mo
        prep-2.0-clahe-seg   MAE 33.34 mo   18.0% within 12mo

    A 3.7x degradation. The incumbent learned its features under global min/max
    on unsegmented, unrotated images; CLAHE + segmentation + rotation is a large
    distribution shift at inference time.

    This corrects the engineering report's estimate that preprocessing would buy
    1-2 months of MAE -- that holds for a model TRAINED under the new pipeline,
    not for one retro-fitted with it. The pipeline is therefore built, versioned
    and tested, but NOT active: it ships with retraining, or with a model that
    declares it.
    """
    assert preprocess.CURRENT_PREPROCESSING == preprocess.PREPROCESSING_V1, (
        "the active pipeline was switched to v2. Measured on the locked test set, "
        "that raises the incumbent model's MAE from 8.9 to 33.3 months. v2 is only "
        "valid for a model trained or fine-tuned under it -- see backend/ai/DIGIBONE.md."
    )


# ── registry and the calibration binding ────────────────────────────────────

def test_incumbent_spec_loads_and_declares_a_pipeline():
    spec = registry.load_spec("boneage_gp")
    assert spec is not None
    assert spec.input_size == 224
    # Pre-M4 metadata carries no version; it must default to v1 (what it was
    # actually calibrated under), never to whatever is current.
    assert spec.preprocessing_version == preprocess.PREPROCESSING_V1


def test_conformal_is_allowed_when_the_pipeline_matches():
    spec = registry.load_spec("boneage_gp")
    policy = registry.resolve_interval_policy(spec, preprocess.PREPROCESSING_V1)
    assert policy.conformal_allowed is True


def test_conformal_is_refused_across_a_pipeline_change():
    """THE safety property of M4.1. A conformal quantile is a property of
    model + preprocessing; serving it after a pipeline change gives an interval
    whose stated coverage is not the coverage it delivers, with no signal."""
    spec = registry.load_spec("boneage_gp")
    policy = registry.resolve_interval_policy(spec, preprocess.PREPROCESSING_V2)
    assert policy.conformal_allowed is False
    assert "calibrated under" in policy.reason
    assert "Re-run calibrate_conformal" in policy.reason


def test_uncalibrated_model_is_refused_conformal_intervals():
    spec = registry.load_spec("boneage_gp")
    bare = registry.ModelSpec(
        model_id="x", kind="screening", method="greulich-pyle",
        onnx_path=spec.onnx_path, input_size=224,
        preprocessing_version=preprocess.PREPROCESSING_V1, population="test",
    )
    assert registry.resolve_interval_policy(bare).conformal_allowed is False


def test_describe_exposes_the_active_pipeline_and_every_model():
    body = registry.describe()
    assert body["active_preprocessing"] == preprocess.CURRENT_PREPROCESSING
    assert preprocess.PREPROCESSING_V2 in body["available_preprocessing"]
    assert any(m["model_id"] for m in body["models"])
    for m in body["models"]:
        assert "conformal_allowed" in m and "preprocessing_version" in m

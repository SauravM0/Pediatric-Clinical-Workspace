"""Calibrate split-conformal intervals for the bone-age model on the RSNA val
split, and write the quantiles into the model metadata (directive S-BA-5).

Reproduces training's exact, deterministic held-out split (numpy default_rng(42),
first 15%), runs the shipped ONNX model on those images with the same
preprocessing the trainer used, and stores conformal half-widths for several
coverage levels in ``boneage_gp.json`` under "conformal". boneage.predict_months
then returns a coverage-guaranteed interval instead of a +/-MAE band.

Run:  python -m backend.ai.calibrate_conformal
Needs the preprocessed image cache the trainer wrote
(``backend/ai/models/_img_cache_<size>_<n>.npz``) and the ONNX model. No GPU.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import boneage, conformal

_MEAN = boneage._MEAN
_STD = boneage._STD
_COVERAGE_LEVELS = (0.80, 0.90, 0.95)
_VAL_FRACTION = 0.15
_SPLIT_SEED = 42


def _find_cache(img_size: int, n_images: int) -> Path:
    exact = boneage.MODEL_PATH.with_name(f"_img_cache_{img_size}_{n_images}.npz")
    if exact.exists():
        return exact
    # fall back to any cache for this input size
    cands = sorted(boneage.MODEL_PATH.parent.glob(f"_img_cache_{img_size}_*.npz"))
    if not cands:
        raise SystemExit(
            f"No preprocessed image cache found (looked for {exact.name}). "
            "Run the trainer once to build it, or point at the RSNA cache."
        )
    return cands[-1]


def _val_indices(n: int) -> np.ndarray:
    rng = np.random.default_rng(_SPLIT_SEED)
    idx = rng.permutation(n)
    n_val = max(1, int(_VAL_FRACTION * n))
    return idx[:n_val]


def _predict_batch(imgs_u8: np.ndarray, sex: np.ndarray) -> np.ndarray:
    """Run the ONNX model on cached uint8 images with the trainer's preprocessing."""
    sess = boneage._session()
    in_names = [i.name for i in sess.get_inputs()]
    mean = _MEAN.reshape(3, 1, 1)
    std = _STD.reshape(3, 1, 1)
    preds = np.empty(len(imgs_u8), dtype=np.float32)
    for i, g in enumerate(imgs_u8):
        arr = g.astype(np.float32) / 255.0
        chw = np.stack([arr, arr, arr], axis=0)      # 3xHxW (same as trainer)
        chw = (chw - mean) / std
        x = chw[np.newaxis].astype(np.float32)
        s = np.array([[float(sex[i])]], dtype=np.float32)
        out = sess.run(None, {in_names[0]: x, in_names[1]: s})[0]
        preds[i] = float(np.asarray(out).reshape(-1)[0])
    return np.clip(preds, 0.0, 240.0)


def main() -> None:
    if not boneage.model_available():
        raise SystemExit("No ONNX model at backend/ai/models/boneage_gp.onnx")
    meta = boneage.model_metadata() or {}
    img_size = int(meta.get("input_size", boneage.IMG_SIZE))
    n_images = int(meta.get("n_images", 0))

    cache = _find_cache(img_size, n_images)
    print(f"Cache: {cache.name}")
    d = np.load(cache)
    imgs, sex, y = d["imgs"], d["sex"].reshape(-1), d["y"].reshape(-1)
    val = _val_indices(len(y))
    print(f"Val split: {len(val)} / {len(y)} images (seed {_SPLIT_SEED}, {_VAL_FRACTION:.0%})")

    preds = _predict_batch(imgs[val], sex[val])
    residuals = np.abs(preds - y[val])
    mae = float(residuals.mean())
    print(f"Recomputed val MAE: {mae:.1f} months (metadata says {meta.get('val_mae_months')})")

    cal = conformal.calibrate(residuals, _COVERAGE_LEVELS)
    for cov_str, q in cal["quantiles"].items():
        emp = conformal.empirical_coverage(residuals, q)
        print(f"  target {cov_str} -> +/-{q:.1f} mo ({q/12:.2f} y), empirical coverage {emp:.3f}")

    # Subgroup-conditional (Mondrian) calibration: sex x predicted-age-band
    # (Plan 3 WI-3). The band uses the PREDICTED age so the same group rule is
    # available at inference. Small groups fall back to the marginal quantile.
    sex_val = sex[val]
    groups = [conformal.bucket(bool(sex_val[i] > 0.5), float(preds[i]))
              for i in range(len(preds))]
    grouped = conformal.calibrate_grouped(residuals, groups, _COVERAGE_LEVELS)
    print("Subgroup (Mondrian) calibration (q90 per sex x age-band):")
    for g, gc in sorted(grouped["groups"].items()):
        tag = " [fallback->marginal]" if gc.get("fallback") else ""
        print(f"  {g}: n={gc['n_calib']}  q90=+/-{gc['quantiles'].get('0.90')} mo{tag}")

    meta["conformal"] = {
        "method": "split-conformal (absolute residual)",
        "dataset": f"RSNA val split (seed {_SPLIT_SEED}, first {_VAL_FRACTION:.0%})",
        "recomputed_val_mae_months": round(mae, 1),
        "n_calib": cal["n_calib"],
        "quantiles_months": cal["quantiles"],
        "by_group": grouped["groups"],
        "min_group": grouped["min_group"],
        "default_coverage": "0.90",
    }
    boneage.META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote conformal quantiles to {boneage.META_PATH.name}")


if __name__ == "__main__":
    main()

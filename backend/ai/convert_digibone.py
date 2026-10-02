"""Convert digiBONE PyTorch weights to ONNX, with parity proven (M4.3).

    python -m backend.ai.convert_digibone --weights digibone.pth \\
        --out backend/ai/models/boneage_digibone.onnx \\
        --parity-images /path/to/100_hand_radiographs

    digiBONE — https://github.com/goellab/digiBONE — MIT licence.
    Frontiers Endocrinol 2026, doi 10.3389/fendo.2026.1757571.

Why a converter rather than a dependency
-----------------------------------------
digiBONE ships PyTorch weights; this project's inference path is ONNX Runtime
only, deliberately. Adding ``torch`` to requirements takes the deployable from
~200 MB to over 2 GB and pulls a training framework into a clinical inference
path. So conversion happens offline on a machine that already has torch, and
only the ``.onnx`` plus its metadata JSON is committed.

The parity assertion is the point of this file
-----------------------------------------------
A conversion that silently changes the numbers is worse than no conversion: the
published 4.7/4.9-month figures, the conformal calibration and the release-gate
decision would all be attached to a model that is not the one that ran. So the
converter runs BOTH models over real images and refuses to write the ONNX unless
they agree to ``PARITY_TOL_MONTHS``.

It refuses on synthetic noise, too. Random tensors exercise a different part of
the input distribution than radiographs do, and a conversion bug in, say, an
interpolation or padding op can be invisible on noise and material on hands.

What this file does NOT know
----------------------------
digiBONE's exact architecture, input size and normalisation are not documented
in its README, and this project does not hold the weights. Those are read from
the checkpoint and from ``--input-size`` / ``--arch`` rather than guessed;
``--dry-run`` prints what was inferred so it can be checked before a real run.
Anything this file assumed and got wrong would produce a model that runs and is
wrong, which is why parity is measured against the source implementation rather
than against a specification written here.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

# Months. Tighter than any clinically meaningful difference by three orders of
# magnitude -- this is checking arithmetic equivalence, not agreement.
PARITY_TOL_MONTHS = 1e-3

# Below this, a parity run says more about the sample than the conversion.
MIN_PARITY_IMAGES = 100

SEGMENTS = ("short_bones", "carpals", "wrist")


class ConversionError(RuntimeError):
    """The conversion cannot be completed or cannot be trusted."""


def _require_torch():
    try:
        import torch  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ConversionError(
            "torch is not installed. This tool runs OFFLINE on a machine that has "
            "it (see requirements-ml.txt); torch is deliberately absent from the "
            "deployable, which is the whole reason this converter exists."
        ) from exc
    import torch

    return torch


def load_checkpoint(weights: Path, *, allow_arbitrary_pickle: bool = False) -> dict:
    """Read the checkpoint and report what it actually contains.

    Deliberately does not assume a layout. digiBONE's release format is not
    documented in its README, and a converter that guesses wrong produces a model
    that runs and is wrong.

    Loaded with ``weights_only=True``. Torch checkpoints are pickles, and
    unpickling one executes whatever it contains -- on a file downloaded from a
    third-party release page, on a machine with clinical data. Torch made this
    the default in 2.6 and this tool does not quietly undo it: a checkpoint that
    needs the unsafe path requires ``--allow-arbitrary-pickle`` and a deliberate
    decision, not a silent fallback.
    """
    torch = _require_torch()
    if not weights.exists():
        raise ConversionError(f"weights not found: {weights}")

    try:
        blob = torch.load(str(weights), map_location="cpu", weights_only=True)
    except Exception as exc:
        if not allow_arbitrary_pickle:
            raise ConversionError(
                f"could not read {weights.name} as a weights-only checkpoint: "
                f"{type(exc).__name__}: {exc}\n\n"
                "Either the file is not a torch checkpoint, or it embeds pickled "
                "objects that only the unsafe loader accepts. Unpickling executes "
                "arbitrary code, so this is not done automatically. Verify the "
                "download against digiBONE's published checksum, then re-run with "
                "--allow-arbitrary-pickle if you accept that."
            ) from exc
        try:
            blob = torch.load(str(weights), map_location="cpu", weights_only=False)
        except Exception as exc2:
            raise ConversionError(
                f"could not read {weights.name} even with the unsafe loader: "
                f"{type(exc2).__name__}: {exc2}"
            ) from exc2

    state = blob
    for key in ("state_dict", "model_state_dict", "model"):
        if isinstance(blob, dict) and key in blob:
            state = blob[key]
            break
    if not isinstance(state, dict):
        raise ConversionError(
            f"could not find a state dict in {weights.name}; top-level type is "
            f"{type(blob).__name__}. Inspect it and pass --arch explicitly."
        )
    return {
        "state_dict": state,
        "n_tensors": len(state),
        "keys_head": list(state)[:8],
        "extra_keys": [k for k in (blob if isinstance(blob, dict) else {})
                       if k not in ("state_dict", "model_state_dict", "model")],
    }


def build_model(arch: str, state_dict: dict):  # pragma: no cover - needs torch
    """Instantiate the architecture and load the weights STRICTLY.

    ``strict=True`` on purpose: a silently-ignored key mismatch is exactly how a
    converted model ends up running with randomly-initialised layers and
    producing plausible-looking numbers.
    """
    torch = _require_torch()
    import torchvision

    factory = getattr(torchvision.models, arch, None)
    if factory is None:
        raise ConversionError(
            f"unknown architecture {arch!r}. Pass the name used by digiBONE's own "
            "inference script (SGP_bone_age.py)."
        )
    model = factory(weights=None)
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing or unexpected:
        raise ConversionError(
            f"state dict does not match {arch!r}: {len(missing)} missing and "
            f"{len(unexpected)} unexpected tensors. First missing: {missing[:5]}. "
            "Loading anyway would leave layers randomly initialised and still "
            "produce plausible-looking bone ages."
        )
    model.eval()
    return model


def check_parity(torch_model, onnx_path: Path, images: list[Path],
                 input_size: int, is_male_for: Optional[dict] = None) -> dict:  # pragma: no cover
    """Run both models over real radiographs and compare.

    Returns the measured worst difference. Raises if it exceeds tolerance or if
    too few real images were supplied.
    """
    import numpy as np
    import onnxruntime as ort
    import torch

    from . import preprocess as _prep

    if len(images) < MIN_PARITY_IMAGES:
        raise ConversionError(
            f"parity needs at least {MIN_PARITY_IMAGES} real radiographs, got "
            f"{len(images)}. Synthetic noise exercises a different part of the "
            "input distribution than hands do, and a bug in an interpolation or "
            "padding op can be invisible on noise and material on radiographs."
        )

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    worst = 0.0
    worst_image = None
    for path in images:
        tensor = _prep.run(path.read_bytes(), input_size,
                           _prep.CURRENT_PREPROCESSING).tensor
        sex = np.array([[1.0 if (is_male_for or {}).get(path.name, True) else 0.0]],
                       dtype=np.float32)
        with torch.no_grad():
            expected = float(torch_model(torch.from_numpy(tensor),
                                         torch.from_numpy(sex)).reshape(-1)[0])
        got = float(session.run(
            None, {i.name: v for i, v in zip(session.get_inputs(), (tensor, sex))}
        )[0].reshape(-1)[0])
        diff = abs(expected - got)
        if diff > worst:
            worst, worst_image = diff, path.name

    if worst > PARITY_TOL_MONTHS:
        raise ConversionError(
            f"ONNX output differs from PyTorch by {worst:.6f} months (worst: "
            f"{worst_image}), tolerance {PARITY_TOL_MONTHS}. The conversion changed "
            "the numbers, so every downstream figure -- the published accuracy, the "
            "conformal calibration, the release-gate decision -- would be attached "
            "to a model that is not the one that ran."
        )
    return {"n_images": len(images), "worst_abs_diff_months": worst,
            "worst_image": worst_image, "tolerance": PARITY_TOL_MONTHS}


def write_metadata(out: Path, *, model_version: str, input_size: int,
                   preprocessing_version: str, parity: dict,
                   population: str, method_key: str) -> Path:
    """Registry metadata beside the ONNX.

    ``conformal`` is deliberately absent. Quantiles do not transfer between
    models, and ``registry.resolve_interval_policy`` withholds intervals for an
    uncalibrated model -- which is the correct state until
    ``calibrate_conformal`` has been run against THIS model.
    """
    meta_path = out.with_suffix(".json")
    meta_path.write_text(json.dumps({
        "model_version": model_version,
        "kind": "screening",
        "method_key": method_key,
        "population": population,
        "input_size": input_size,
        "preprocessing_version": preprocessing_version,
        "trained_on": "RSNA + HCJMRI (Pune)",
        "source": "https://github.com/goellab/digiBONE",
        "licence": "MIT",
        "citation": "Frontiers Endocrinol 2026, doi 10.3389/fendo.2026.1757571",
        "converted_on": date.today().isoformat(),
        "parity": parity,
        "published_mad_months": {"sgp_male": 4.7, "sgp_female": 4.9,
                                 "full_hand_male": 5.7, "full_hand_female": 5.9},
        "note": (
            "Greulich-Pyle scale, NOT TW3. May be shown beside a TW3 bone age, "
            "never stored as one or averaged with one. Not conformally calibrated "
            "until calibrate_conformal has been run against this model; intervals "
            "are withheld until then."
        ),
    }, indent=2) + "\n", encoding="utf-8")
    return meta_path


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Convert digiBONE weights to ONNX.")
    p.add_argument("--weights", type=Path, required=True)
    p.add_argument("--out", type=Path,
                   default=Path(__file__).with_name("models") / "boneage_digibone.onnx")
    p.add_argument("--arch", default="",
                   help="torchvision architecture name used by digiBONE")
    p.add_argument("--input-size", type=int, default=0,
                   help="model input edge in pixels; required for a real run")
    p.add_argument("--parity-images", type=Path, default=None,
                   help=f"directory of >= {MIN_PARITY_IMAGES} real hand radiographs")
    p.add_argument("--method-key", default="segmental-greulich-pyle")
    p.add_argument("--population", default="Indian-HCJMRI + RSNA")
    p.add_argument("--model-version", default=f"digibone-sgp-{date.today():%Y%m%d}")
    p.add_argument("--dry-run", action="store_true",
                   help="inspect the checkpoint and report, converting nothing")
    p.add_argument("--allow-arbitrary-pickle", action="store_true",
                   help="permit torch's unsafe loader; executes code from the "
                        "checkpoint, so verify the download first")
    args = p.parse_args(argv)

    try:
        info = load_checkpoint(args.weights,
                               allow_arbitrary_pickle=args.allow_arbitrary_pickle)
    except ConversionError as exc:
        print(f"cannot convert: {exc}", file=sys.stderr)
        return 2

    print(f"checkpoint        {args.weights}")
    print(f"tensors           {info['n_tensors']}")
    print(f"first keys        {info['keys_head']}")
    if info["extra_keys"]:
        print(f"other top-level   {info['extra_keys']}")

    if args.dry_run:
        print("\ndry run: nothing written. Confirm the architecture and input size "
              "against digiBONE's SGP_bone_age.py, then re-run with --arch, "
              "--input-size and --parity-images.")
        return 0

    missing_args = [name for name, value in
                    (("--arch", args.arch), ("--input-size", args.input_size),
                     ("--parity-images", args.parity_images)) if not value]
    if missing_args:
        print(f"cannot convert: {', '.join(missing_args)} required for a real run. "
              "Parity against the source implementation is not optional — an "
              "unverified conversion invalidates every downstream number.",
              file=sys.stderr)
        return 2

    # Everything past here needs torch and the real weights, so it is exercised
    # by the operator rather than by CI. The failure modes it guards against are
    # asserted above in load_checkpoint/build_model/check_parity.
    try:  # pragma: no cover - requires torch + weights
        import torch

        from . import preprocess as _prep

        model = build_model(args.arch, info["state_dict"])
        args.out.parent.mkdir(parents=True, exist_ok=True)
        dummy = torch.zeros(1, 3, args.input_size, args.input_size)
        sex = torch.zeros(1, 1)
        torch.onnx.export(model, (dummy, sex), str(args.out),
                          input_names=["image", "sex"], output_names=["bone_age_months"],
                          dynamic_axes=None, opset_version=17)

        images = sorted(pp for pp in args.parity_images.iterdir()
                        if pp.suffix.lower() in (".png", ".jpg", ".jpeg", ".dcm"))
        parity = check_parity(model, args.out, images, args.input_size)
        meta = write_metadata(
            args.out, model_version=args.model_version, input_size=args.input_size,
            preprocessing_version=_prep.CURRENT_PREPROCESSING, parity=parity,
            population=args.population, method_key=args.method_key)
    except ConversionError as exc:  # pragma: no cover
        args.out.unlink(missing_ok=True)
        print(f"\nconversion REJECTED: {exc}", file=sys.stderr)
        return 1

    print(f"\nwrote             {args.out}")
    print(f"metadata          {meta}")
    print(f"parity            worst {parity['worst_abs_diff_months']:.2e} months "
          f"over {parity['n_images']} images")
    print(f"\nNot yet active. Evaluate on the locked test set, calibrate conformal "
          f"intervals against THIS model, take it through the release gate as a "
          f"CROSS_METHOD_ADOPTION, then set PCW_BONEAGE_MODEL={args.out.stem}.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

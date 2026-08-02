"""Model registry, and the binding that stops calibration drifting silently (M4.1).

The incumbent design assumed one model with one preprocessing path, so
``boneage_gp.json`` could store conformal quantiles as if they were a property
of the model. They are not. A conformal quantile is a property of **model +
preprocessing + calibration set**: change how images are prepared and the
residual distribution changes, so the stored quantile no longer delivers its
nominal coverage. Nothing detected that. The numbers kept coming out, they were
just quietly wrong -- the worst failure mode a calibrated interval can have,
because the whole point of the interval is that its coverage is trustworthy.

So a :class:`ModelSpec` records the preprocessing version its metrics were
computed under, and :func:`resolve_interval_policy` refuses to serve conformal
intervals when the active pipeline does not match. Refusing is safe: the caller
degrades to a labelled approximation, exactly as it already does for an
uncalibrated model.

Also carries ``population`` and ``method``, because M4's intended change is
adopting an Indian-trained model that uses a DIFFERENT method (segmental
Greulich-Pyle) from the incumbent. Comparing those on MAE alone would be a
category error -- see release_gate's comparison_basis.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import preprocess

_MODELS_DIR = Path(__file__).with_name("models")


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    kind: str                    # screening | localizer | stager
    method: str                  # greulich-pyle | segmental-greulich-pyle | tw3-rus
    onnx_path: Path
    input_size: int
    preprocessing_version: str
    population: str              # e.g. "RSNA-US", "Indian-HCJMRI", "mixed"
    metrics: dict[str, Any] = field(default_factory=dict)
    conformal: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def available(self) -> bool:
        return self.onnx_path.exists()

    def matches_active_pipeline(self, active: Optional[str] = None) -> bool:
        return self.preprocessing_version == (active or preprocess.CURRENT_PREPROCESSING)


def _spec_from_metadata(meta: dict, onnx_path: Path, model_id: str) -> ModelSpec:
    return ModelSpec(
        model_id=meta.get("model_version", model_id),
        kind=meta.get("kind", "screening"),
        method=meta.get("method_key", "greulich-pyle"),
        onnx_path=onnx_path,
        input_size=int(meta.get("input_size", 224)),
        # Models predating M4 carry no version. They were trained and calibrated
        # under the original pipeline by definition, so that is what they get --
        # assuming the CURRENT version instead would be the exact silent
        # mismatch this module exists to prevent.
        preprocessing_version=meta.get("preprocessing_version", preprocess.PREPROCESSING_V1),
        population=meta.get("population", "RSNA-US"),
        metrics={k: meta[k] for k in ("val_mae_months", "val_mae_years", "n_val")
                 if k in meta},
        conformal=meta.get("conformal", {}) or {},
        raw=meta,
    )


def load_spec(model_id: str = "boneage_gp") -> Optional[ModelSpec]:
    onnx_path = _MODELS_DIR / f"{model_id}.onnx"
    meta_path = _MODELS_DIR / f"{model_id}.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _spec_from_metadata(meta, onnx_path, model_id)


def list_specs() -> list[ModelSpec]:
    specs = []
    for meta_path in sorted(_MODELS_DIR.glob("*.json")):
        spec = load_spec(meta_path.stem)
        if spec is not None:
            specs.append(spec)
    return specs


@dataclass(frozen=True)
class IntervalPolicy:
    """Whether calibrated intervals may be served, and why not if not."""
    conformal_allowed: bool
    reason: str
    model_preprocessing: str
    active_preprocessing: str


def resolve_interval_policy(spec: Optional[ModelSpec],
                            active: Optional[str] = None) -> IntervalPolicy:
    active = active or preprocess.CURRENT_PREPROCESSING
    if spec is None:
        return IntervalPolicy(False, "no model metadata", "-", active)
    if not spec.conformal:
        return IntervalPolicy(False, "model is not conformally calibrated",
                              spec.preprocessing_version, active)
    if not spec.matches_active_pipeline(active):
        return IntervalPolicy(
            False,
            f"conformal quantiles were calibrated under {spec.preprocessing_version!r} "
            f"but the active pipeline is {active!r}. A quantile is a property of "
            "model + preprocessing; serving it across a pipeline change would give "
            "an interval whose stated coverage is not the coverage it delivers. "
            "Re-run calibrate_conformal under the active pipeline.",
            spec.preprocessing_version, active,
        )
    return IntervalPolicy(True, "ok", spec.preprocessing_version, active)


def describe() -> dict[str, Any]:
    """Registry state, for /api/bone-age/config and the monitoring view."""
    active = preprocess.CURRENT_PREPROCESSING
    out = []
    for spec in list_specs():
        policy = resolve_interval_policy(spec, active)
        out.append({
            "model_id": spec.model_id,
            "kind": spec.kind,
            "method": spec.method,
            "population": spec.population,
            "input_size": spec.input_size,
            "available": spec.available,
            "preprocessing_version": spec.preprocessing_version,
            "conformal_allowed": policy.conformal_allowed,
            "conformal_reason": policy.reason,
            "metrics": spec.metrics,
        })
    return {
        "active_preprocessing": active,
        "available_preprocessing": list(preprocess.available_versions()),
        "models": out,
    }

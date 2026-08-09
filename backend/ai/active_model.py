"""Which registered model actually serves inference (M4.3 / digiBONE).

The registry has always been able to hold several models -- ``list_specs``
enumerates them, ``ModelSpec`` records each one's method, population and
preprocessing. But the inference path did not consult it. ``boneage.py`` hard-
coded ``models/boneage_gp.onnx`` and ``load_spec()`` with its default id, so
converting digiBONE, registering it and calibrating it would have changed
nothing: the incumbent would still have answered every request.

That is the third time in this project a reference or model has been prepared
with no consumer (see the M1.1 IAP LMS path and TW3 adult-height prediction), so
the check is now a test rather than a habit.

Selection, and why it is an environment variable
------------------------------------------------
``PCW_BONEAGE_MODEL`` names the model id; unset means the incumbent. A
deployment-level switch rather than a stored setting on purpose: which model
reads a radiograph is an operational decision that must be identical for every
user of an installation and must not be changeable through the application by
someone who has not run the release gate.

Selection is validated, not trusted. An id naming a model that is missing, or
whose ONNX file is absent, falls back to the incumbent and says so -- a typo in
a deployment variable must not silently disable bone-age screening, and it must
never silently promote a model nobody validated.

Labels follow the model
-----------------------
The response used to carry a hardcoded method string and a hardcoded note
saying the model was RSNA-trained and "not India-calibrated". Both would have
survived a switch to digiBONE unchanged -- so an Indian-trained segmental model
would have been presented as a US-trained whole-image one, and the note telling
the clinician how far to trust it would have been describing a different model
entirely. :func:`describe_method` and :func:`population_note` derive them from
the spec instead.
"""
from __future__ import annotations

import os
from typing import Optional

from . import registry

INCUMBENT_ID = "boneage_gp"
ENV_VAR = "PCW_BONEAGE_MODEL"

# Human-readable method names. A method not listed here is reported verbatim
# rather than guessed at -- an unknown method must not be described as a known
# one, and "unrecognised" is a safe thing for a clinician to read.
METHOD_LABELS = {
    "greulich-pyle": "Greulich-Pyle whole-image estimate (screening, not TW3)",
    "segmental-greulich-pyle": (
        "Segmental Greulich-Pyle estimate — short bones, carpals and wrist "
        "assessed separately (screening, not TW3)"
    ),
    "tw3-rus": "TW3 RUS estimate",
}

# Population-specific caveats. The incumbent's note is the one that was
# previously hardcoded for every model.
_RSNA_NOTE = (
    "Model trained on the RSNA (US) dataset, not India-calibrated. Published "
    "data show Greulich-Pyle skeletal age runs ~0.5-0.7 yr delayed in Indian "
    "children (more in boys). Treat as a screening suggestion; confirm with TW3."
)
_INDIAN_NOTE = (
    "Model trained with Indian children in its development set, so the "
    "population offset that affects RSNA-only models is reduced. It remains a "
    "Greulich-Pyle screening estimate, NOT a TW3 bone age — the two are "
    "different standards and must never be averaged or substituted. Your "
    "clinic's films are still a different sample from the model's; the local "
    "validation cohort is what turns that from an assumption into a number."
)
_UNKNOWN_NOTE = (
    "Population of the training data is not declared in this model's metadata, "
    "so no population-specific caveat can be given. Treat the estimate as "
    "unvalidated for this clinic and rely on manual TW3."
)


def requested_id() -> Optional[str]:
    value = os.environ.get(ENV_VAR, "").strip()
    return value or None


def resolve() -> dict:
    """The model that will serve inference, and why.

    Never raises: bone-age screening degrading to the incumbent is preferable to
    an endpoint that 500s because a deployment variable has a typo.
    """
    wanted = requested_id()
    if wanted is None:
        spec = registry.load_spec(INCUMBENT_ID)
        return {"model_id": INCUMBENT_ID, "spec": spec, "requested": None,
                "fell_back": False,
                "reason": f"no {ENV_VAR} set; using the incumbent"}

    spec = registry.load_spec(wanted)
    if spec is None:
        return {"model_id": INCUMBENT_ID, "spec": registry.load_spec(INCUMBENT_ID),
                "requested": wanted, "fell_back": True,
                "reason": (f"{ENV_VAR}={wanted!r} is not registered "
                           f"(no models/{wanted}.json); using the incumbent")}
    if not spec.available:
        return {"model_id": INCUMBENT_ID, "spec": registry.load_spec(INCUMBENT_ID),
                "requested": wanted, "fell_back": True,
                "reason": (f"{ENV_VAR}={wanted!r} is registered but its ONNX file is "
                           f"missing ({spec.onnx_path.name}); using the incumbent")}
    return {"model_id": wanted, "spec": spec, "requested": wanted,
            "fell_back": False, "reason": "ok"}


def active_spec() -> Optional[registry.ModelSpec]:
    return resolve()["spec"]


def describe_method(spec: Optional[registry.ModelSpec]) -> str:
    if spec is None:
        return "unknown model"
    return METHOD_LABELS.get(
        spec.method, f"{spec.method} estimate (screening, not TW3) — unrecognised method key")


def population_note(spec: Optional[registry.ModelSpec]) -> str:
    if spec is None:
        return _UNKNOWN_NOTE
    population = (spec.population or "").lower()
    if "india" in population or "hcjmri" in population:
        return _INDIAN_NOTE
    if "rsna" in population:
        return _RSNA_NOTE
    return _UNKNOWN_NOTE


def is_tw3(spec: Optional[registry.ModelSpec]) -> bool:
    """Whether this model's output is on the TW3 scale.

    Nothing in the product currently sets this, and that is the point: every
    screening model here is Greulich-Pyle, so its output may be shown beside a
    TW3 bone age but never stored as one. ``assessment_service`` writes
    ``bone_age_months`` only from ``letters_scoring`` / TW3 scoring, and
    ``tw3/report.py`` carries the model's number under its own
    ``ai_screening_estimate_years`` key.
    """
    return (spec is not None) and spec.method.startswith("tw3")


def describe() -> dict:
    """Selection state, for /api/bone-age/config and the monitoring view."""
    resolution = resolve()
    spec = resolution["spec"]
    return {
        "model_id": resolution["model_id"],
        "requested": resolution["requested"],
        "fell_back": resolution["fell_back"],
        "reason": resolution["reason"],
        "env_var": ENV_VAR,
        "method": None if spec is None else spec.method,
        "method_label": describe_method(spec),
        "population": None if spec is None else spec.population,
        "population_note": population_note(spec),
        "is_tw3_scale": is_tw3(spec),
        "available": bool(spec and spec.available),
    }

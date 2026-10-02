"""Run the golden clinical vignettes in validation/clinical_vignettes.json (step 8).

Each vignette's expected values were derived by hand from the published source,
not from this code. ``run()`` evaluates every vignette through the SAME entry
points the API uses and reports, per vignette, whether the system agrees and
whether a clinician has signed it off. Shared by the test suite and by
``python -m backend.release_check``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VIGNETTES_PATH = Path(__file__).resolve().parents[1] / "validation" / "clinical_vignettes.json"


def _actual(module: str, inputs: dict) -> dict[str, Any]:
    if module == "egfr":
        from backend.renal import egfr
        r = egfr.assess(**inputs)
        if not r.get("available"):
            return {"available": False}
        return {"available": True, "equation": r["primary"]["equation"],
                "egfr": r["primary"]["value"], "gfr_category": r["gfr_category"]["code"]}
    if module == "fib4":
        from backend.hepatic import fib4
        r = fib4.assess(**inputs)
        return {"fib4": r.get("fib4"), "category": r.get("category")}
    if module == "bp":
        from backend.vitals import blood_pressure
        r = blood_pressure.assess(**inputs)
        return {"category": r.get("category"), "map": r.get("map")}
    if module == "who":
        from backend.growth import who_reference
        return {"value": who_reference.who_value_at_z(
            inputs["measure"], inputs["sex"], inputs["age_years"], inputs["z"])}
    raise ValueError(f"unknown vignette module {module!r}")


def _matches(expected: Any, actual: Any, tol: float) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return (isinstance(actual, (int, float)) and not isinstance(actual, bool)
                and abs(actual - expected) <= tol + 1e-12)
    return expected == actual


def load() -> dict:
    return json.loads(VIGNETTES_PATH.read_text(encoding="utf-8"))


def run() -> list[dict]:
    out = []
    for v in load()["vignettes"]:
        try:
            actual = _actual(v["module"], v["inputs"])
            error = None
        except Exception as exc:  # noqa: BLE001 -- reported, never swallowed
            actual, error = {}, f"{type(exc).__name__}: {exc}"
        mismatches = {k: {"expected": e, "actual": actual.get(k)}
                      for k, e in v["expected"].items()
                      if not _matches(e, actual.get(k), v.get("tolerance", 0))}
        signoff = v.get("signoff") or {}
        out.append({
            "id": v["id"], "module": v["module"], "description": v["description"],
            "passed": error is None and not mismatches,
            "error": error, "mismatches": mismatches,
            "signed_off": signoff.get("agrees") is True and bool(signoff.get("clinician"))
                          and bool(signoff.get("date")),
            "clinician_disagrees": signoff.get("agrees") is False,
        })
    return out

"""Install the Khamis-Roche regression coefficients (M5.3).

    python -m backend.clinical.ingest_khamis_roche coefficients.csv
    python -m backend.clinical.ingest_khamis_roche coefficients.csv --install \\
        --entered-by "Dr A Rao" --verified-by "Dr S Menon" --source "Khamis & Roche 1994, Table 2"
    python -m backend.clinical.ingest_khamis_roche --status

    Khamis HJ, Roche AF. Predicting adult stature without using skeletal age:
    the Khamis-Roche method. Pediatrics 1994;94(4):504-7.

The fifth and last of the ingestion tools, and the only one for a REGRESSION
---------------------------------------------------------------------------
The other four install distributions -- L, M, S triplets or percentage tables --
where a wrong value is wrong at one age. These are regression coefficients that
compose:

    adult height = intercept + b_height*height + b_weight*weight
                             + b_midparent*midparent

so a single transposed column produces a number that is confidently wrong at
every age at once, and looks like a height. That is why the gate is not just
"are the values in range" but "does the row COMPOSE": each age's coefficients
are applied to a reference child and the result has to be a possible adult
height. Coefficients can each be individually plausible and still not compose.

Why this one is worth entering
------------------------------
It is the only adult-height prediction in the product that needs no radiograph.
The TW3 percentage method (M2C) is more informative when a film exists, and the
mid-parental target answers a different question entirely -- see
prediction.adult_height_summary, which returns all three separately labelled.

Accepted input
--------------
CSV or JSON, one row per (sex, age) with the four coefficients:

    sex, age, intercept, height, weight, midparent

Header spellings are absorbed (`Sex`, `Age (years)`, `b_height`, `mid_parent`,
`MPH`, ...). The paper's tables are published per sex; either supply one file
with a sex column or two files and run the tool twice with --merge.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from backend.growth.ingest_iap_lms import IngestError, header_key

from . import prediction

COEFFICIENTS_PATH = prediction._COEFFICIENTS_PATH
PROVENANCE_KEY = "provenance"

_SEX_ALIASES = {
    "boy": "boys", "boys": "boys", "male": "boys", "m": "boys",
    "girl": "girls", "girls": "girls", "female": "girls", "f": "girls",
}
_COLUMN_ALIASES = {
    "sex": ("sex", "gender"),
    "age": ("age", "age_years", "age_yr", "years"),
    "intercept": ("intercept", "constant", "const", "b0", "a"),
    "height": ("height", "b_height", "b1", "stature", "ht"),
    "weight": ("weight", "b_weight", "b2", "wt"),
    "midparent": ("midparent", "mid_parent", "midparental", "mid_parental_height",
                  "b_midparent", "b3", "mph", "mid_parent_stature"),
}


def _resolve_columns(fieldnames) -> dict[str, str]:
    present = {header_key(f): f for f in fieldnames}
    resolved = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in present:
                resolved[canonical] = present[alias]
                break
    missing = [c for c in _COLUMN_ALIASES if c not in resolved and c != "sex"]
    if missing:
        raise IngestError(
            f"could not find column(s) {missing} in {sorted(present)}. Recognised: "
            + "; ".join(f"{k}={'/'.join(v)}" for k, v in _COLUMN_ALIASES.items())
        )
    return resolved


def normalise(source: Path, default_sex: Optional[str] = None) -> dict:
    """Parse into {'boys': {age: {...}}, 'girls': {...}}."""
    if source.suffix.lower() == ".json":
        blob = json.loads(source.read_text(encoding="utf-8"))
        rows = blob.get("rows", blob) if isinstance(blob, dict) else blob
        if not isinstance(rows, list):
            raise IngestError(f"{source.name}: expected a list of rows")
    else:
        with open(source, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(
                ln for ln in f if not ln.lstrip().startswith("#")))
    if not rows:
        raise IngestError(f"{source.name} has no data rows")

    cols = _resolve_columns(rows[0].keys())
    out: dict[str, dict[str, dict[str, float]]] = {"boys": {}, "girls": {}}
    for lineno, raw in enumerate(rows, start=2):
        if "sex" in cols and str(raw.get(cols["sex"], "")).strip():
            sex = _SEX_ALIASES.get(str(raw[cols["sex"]]).strip().lower())
        else:
            sex = default_sex
        if sex is None:
            raise IngestError(
                f"line {lineno}: no sex column and no --sex given, so this row "
                "cannot be filed. The paper publishes one table per sex."
            )
        try:
            age = float(raw[cols["age"]])
            row = {name: float(raw[cols[name]])
                   for name in ("intercept", "height", "weight", "midparent")}
        except (TypeError, ValueError, KeyError) as exc:
            raise IngestError(f"line {lineno}: {exc}") from exc
        # One decimal place, matching predict_adult_height's lookup key exactly
        # (`f"{round(age*2)/2:.1f}"`). Writing "10" where the consumer asks for
        # "10.0" produces a table that validates perfectly and whose every
        # lookup misses -- prediction stays silently unavailable with no fault
        # anywhere to find.
        out[sex][f"{round(age * 2) / 2:.1f}"] = row

    if not any(out.values()):
        raise IngestError(f"{source.name}: no usable rows")
    return out


def build_document(coefficients: dict, *, entered_by: str = "", verified_by: str = "",
                   note: str = "", source_note: str = "") -> dict:
    # `source_note`, not `source`: ingest()'s first positional argument is the
    # source FILE, and a provenance kwarg of the same name collides with it.
    return {
        "_about": (
            "Khamis-Roche regression coefficients, entered by a human from the "
            "published paper. Predicted adult height = intercept + "
            "b_height*height_cm + b_weight*weight_kg + b_midparent*midparent_cm."
        ),
        "reference": ("Khamis HJ, Roche AF. Predicting adult stature without using "
                      "skeletal age: the Khamis-Roche method. Pediatrics "
                      "1994;94(4):504-7."),
        "coefficients": coefficients,
        PROVENANCE_KEY: {
            "entered_on": date.today().isoformat(),
            "entered_by": entered_by,
            "verified_by": verified_by,
            "source": source_note,
            "note": note,
        },
    }


def ingest(source: Path, *, install: bool = False, default_sex: Optional[str] = None,
           merge: bool = False, compare: Optional[Path] = None, **provenance) -> dict:
    coefficients = normalise(source, default_sex)

    if merge and COEFFICIENTS_PATH.exists():
        existing = (json.loads(COEFFICIENTS_PATH.read_text(encoding="utf-8"))
                    .get("coefficients") or {})
        for sex in ("boys", "girls"):
            if not coefficients.get(sex):
                coefficients[sex] = existing.get(sex, {})

    counts = {sex: len(rows) for sex, rows in coefficients.items()}
    result: dict = {"source": str(source), "rows": counts, "installed": False}

    # Double entry, when asked for -- the same check offered for the licensed
    # TW3 percentages, and for the same reason: there is no second published
    # copy here to reconcile against, only another human reading.
    if compare is not None:
        other = normalise(compare, default_sex)
        diffs = []
        for sex in ("boys", "girls"):
            a, b = coefficients.get(sex, {}), other.get(sex, {})
            for age in sorted(set(a) | set(b)):
                if a.get(age) != b.get(age):
                    diffs.append({"sex": sex, "age": age,
                                  "first": a.get(age), "second": b.get(age)})
        result["double_entry"] = {"compared_with": str(compare),
                                  "differences": diffs, "match": not diffs}

    result["problems"] = prediction.coefficient_problems(
        {"coefficients": coefficients})

    blocked = bool(result["problems"]) or (
        compare is not None and not result["double_entry"]["match"])
    result["verdict"] = {"ok": not blocked,
                         "reason": "ok" if not blocked else "fix the problems above"}

    if install and not blocked:
        COEFFICIENTS_PATH.write_text(
            json.dumps(build_document(coefficients, **provenance), indent=2) + "\n",
            encoding="utf-8")
        prediction.reset_cache()
        result["installed"] = True
        result["status"] = prediction.khamis_roche_status()
    return result


def _print(result: dict) -> None:
    print(f"source            {result['source']}")
    for sex, n in result["rows"].items():
        print(f"  {sex:<6} {n} age row(s)")

    if result.get("double_entry"):
        de = result["double_entry"]
        print(f"\ndouble entry      {'MATCH' if de['match'] else 'MISMATCH'} "
              f"vs {de['compared_with']}")
        for d in de["differences"][:8]:
            print(f"  {d['sex']} @ {d['age']}: {d['first']} vs {d['second']}")

    if result["problems"]:
        print(f"\nproblems ({len(result['problems'])}):")
        for p in result["problems"][:12]:
            print(f"  - {p}")

    v = result["verdict"]
    print(f"\nverdict           {'PASS' if v['ok'] else 'FAIL'} — {v['reason']}")
    if result["installed"]:
        print(f"\nINSTALLED to {COEFFICIENTS_PATH}")
        print("Khamis-Roche prediction is live on /api/patients/{id}/adult-height.")
    elif v["ok"]:
        print("\nChecks passed. Re-run with --install.")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Install the Khamis-Roche adult-height coefficients.")
    p.add_argument("source", type=Path, nargs="?")
    p.add_argument("--install", action="store_true")
    p.add_argument("--sex", choices=("boys", "girls"),
                   help="for a file covering one sex with no sex column")
    p.add_argument("--merge", action="store_true",
                   help="keep the other sex's already-installed rows")
    p.add_argument("--compare", type=Path, default=None,
                   help="second independent transcription to diff against")
    p.add_argument("--entered-by", default="")
    p.add_argument("--verified-by", default="")
    p.add_argument("--source", dest="source_note", default="")
    p.add_argument("--note", default="")
    p.add_argument("--status", action="store_true",
                   help="print whether prediction is live, and why not")
    args = p.parse_args(argv)

    if args.status or args.source is None:
        print(json.dumps(prediction.khamis_roche_status(), indent=2))
        return 0 if prediction.khamis_roche_status()["active"] else 1

    try:
        result = ingest(args.source, install=args.install, default_sex=args.sex,
                        merge=args.merge, compare=args.compare,
                        entered_by=args.entered_by, verified_by=args.verified_by,
                        source_note=args.source_note, note=args.note)
    except IngestError as exc:
        print(f"cannot ingest: {exc}", file=sys.stderr)
        return 2

    _print(result)
    return 0 if result["verdict"]["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

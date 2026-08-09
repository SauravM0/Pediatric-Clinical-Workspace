"""Install the IAP 2015 L,M,S values and prove they are usable (M1.1).

    python -m backend.growth.ingest_iap_lms path/to/whatever_the_authors_sent.csv
    python -m backend.growth.ingest_iap_lms path/to/file.csv --install \\
        --supplied-by "Dr A Khadilkar (HCJMRI)" --received "2026-08-09"

Why this exists rather than "edit the CSV by hand"
--------------------------------------------------
The file is 162 rows (2 sexes x 3 measures x 27 ages) of numbers that are
meaningless to the eye -- an L of 0.87 and an L of 0.78 look equally plausible,
and only one of them is the reference a child gets scored against. Hand-editing
puts the reproduction gate in the position of catching typing mistakes, which it
can do, but only after the fact and without saying where. This normalises the
authors' format, reports coverage BEFORE judging anything, then runs the gate
and refuses to install a file that fails it.

Nothing here can force activation. ``iap_lms_reference.lms_available()`` gates on
the reproduction check independently, so the worst this tool can do is decline to
install a good file -- never install a bad one.

Accepted input
--------------
Any CSV with one row per (sex, measure, age) and recognisable column names:

    sex        sex, gender, Sex          -> boy(s) / girl(s) / m / f
    measure    measure, parameter, var   -> height / weight / bmi (+ synonyms)
    age        age, age_years, age_yr    -> 5.0 .. 18.0 in 0.5 steps
    L, M, S    L/lambda/l, M/mu/median, S/sigma/cv

Excel files are not read directly on purpose -- "Save As CSV" is one step for the
operator and removes a parsing dependency from the clinical path.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from . import iap_lms_reference as lms
from . import iap_table_consistency as consistency
from . import measures as _measures

PROVENANCE_PATH = lms.LMS_PATH.parent / "iap_2015_lms_provenance.json"

_SEX_ALIASES = {
    "boy": "boy", "boys": "boy", "male": "boy", "m": "boy",
    "girl": "girl", "girls": "girl", "female": "girl", "f": "girl",
}
_MEASURE_ALIASES = {
    "height": "height", "ht": "height", "stature": "height", "height_cm": "height",
    "weight": "weight", "wt": "weight", "weight_kg": "weight",
    "bmi": "bmi", "body_mass_index": "bmi", "bmi_kgm2": "bmi",
}
_COLUMN_ALIASES = {
    "sex": ("sex", "gender"),
    "measure": ("measure", "parameter", "param", "variable", "var"),
    "age": ("age", "age_years", "age_yr", "age_y", "ageyears"),
    "L": ("l", "lambda", "skew"),
    "M": ("m", "mu", "median"),
    "S": ("s", "sigma", "cv", "coefficient_of_variation"),
}


class IngestError(ValueError):
    """The supplied file cannot be turned into a usable LMS table."""


def header_key(name: str) -> str:
    """Reduce a header to a comparable key.

    Real headers carry units and punctuation -- 'Age (years)', 'M (median)',
    'S / sigma'. Stripping a parenthesised tail and then all non-alphanumerics
    absorbs those without needing an alias per spelling.

    Public because ``ingest_velocity_reference`` shares it: both tools face the
    same problem of absorbing whatever spelling an author's export happens to
    use, and two copies would drift.
    """
    base = re.sub(r"\(.*?\)", " ", (name or ""))
    return re.sub(r"[^a-z0-9]+", "_", base.strip().lower()).strip("_")


def _resolve_columns(fieldnames: Iterable[str]) -> dict[str, str]:
    """Map canonical name -> the header actually present."""
    present = {header_key(f): f for f in fieldnames}
    resolved: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in present:
                resolved[canonical] = present[alias]
                break
    missing = [c for c in _COLUMN_ALIASES if c not in resolved]
    if missing:
        raise IngestError(
            f"could not find column(s) {missing} in {sorted(present)}. "
            f"Recognised names per field: "
            + "; ".join(f"{k}={'/'.join(v)}" for k, v in _COLUMN_ALIASES.items())
        )
    return resolved


def normalise(source: Path) -> list[tuple[str, str, float, float, float, float]]:
    """Parse any accepted layout into canonical rows. Raises on anything odd."""
    with open(source, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise IngestError(f"{source} has no header row")
        cols = _resolve_columns(reader.fieldnames)

        rows = []
        for lineno, raw in enumerate(reader, start=2):
            if not (raw.get(cols["sex"]) or "").strip():
                continue
            sex_raw = str(raw[cols["sex"]]).strip().lower()
            measure_raw = str(raw[cols["measure"]]).strip().lower().replace(" ", "_")
            sex = _SEX_ALIASES.get(sex_raw)
            measure = _MEASURE_ALIASES.get(measure_raw)
            if sex is None:
                raise IngestError(f"line {lineno}: unrecognised sex {sex_raw!r}")
            if measure is None:
                raise IngestError(
                    f"line {lineno}: unrecognised measure {measure_raw!r}; "
                    f"expected one of {sorted(set(_MEASURE_ALIASES.values()))}"
                )
            try:
                age = round(float(raw[cols["age"]]), 2)
                l = float(raw[cols["L"]])
                m = float(raw[cols["M"]])
                s = float(raw[cols["S"]])
            except (TypeError, ValueError) as exc:
                raise IngestError(f"line {lineno}: {exc}") from exc
            rows.append((sex, measure, age, l, m, s))

    if not rows:
        raise IngestError(f"{source} contains a header but no data rows")
    return rows


def coverage(rows) -> dict:
    """What is present and what is missing, BEFORE any verdict is passed.

    Reported separately from the gate because "your file is missing girls' BMI
    above 14y" and "your file's numbers are wrong" are different problems with
    different fixes, and a single pass/fail conflates them.
    """
    have: dict[tuple[str, str], set[float]] = {}
    for sex, measure, age, *_ in rows:
        have.setdefault((sex, measure), set()).add(age)

    report, complete = {}, True
    for sex in ("boy", "girl"):
        for measure in _measures.IAP_TABLE_KEYS:
            ages = have.get((sex, measure), set())
            missing = [a for a in lms.REQUIRED_AGES if a not in ages]
            extra = sorted(a for a in ages if a not in lms.REQUIRED_AGES)
            complete = complete and not missing
            report[f"{sex}/{measure}"] = {
                "present": len(ages),
                "required": len(lms.REQUIRED_AGES),
                "missing_ages": missing,
                "unexpected_ages": extra,
            }
    return {"complete": complete, "series": report}


def _sanity(rows) -> list[str]:
    """Cheap structural checks that catch a mis-mapped column immediately.

    An S of 5.0 or an M of 0.12 means L/M/S landed in the wrong columns -- which
    the reproduction gate would also catch, but as an opaque "does not reproduce"
    rather than "your sigma column is your lambda column".
    """
    problems = []
    for sex, measure, age, l, m, s in rows:
        where = f"{sex}/{measure}@{age}"
        if m <= 0:
            problems.append(f"{where}: M={m} must be positive")
        if not (0 < s < 1.0):
            problems.append(
                f"{where}: S={s} is outside (0, 1). S is a coefficient of "
                "variation, typically 0.03-0.25 — a value here usually means the "
                "L/M/S columns are mapped the wrong way round."
            )
        if abs(l) > 5:
            problems.append(f"{where}: L={l} is implausible for Cole's lambda")
        expected = _measures.PLAUSIBLE_MEDIAN_RANGE[measure]
        if not (expected[0] <= m <= expected[1]):
            problems.append(
                f"{where}: M={m} is outside the plausible {expected} for {measure} "
                "— check the measure column and the unit"
            )
    return problems


def write_canonical(rows, destination: Path) -> int:
    ordered = sorted(rows, key=lambda r: (r[0], r[1], r[2]))
    with open(destination, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sex", "measure", "age_years", "L", "M", "S"])
        for sex, measure, age, l, m, s in ordered:
            w.writerow([sex, measure, f"{age:g}", f"{l:.6f}", f"{m:.6f}", f"{s:.6f}"])
    return len(ordered)


def evaluate(candidate: Path) -> dict:
    """Run the real activation gate against a candidate file.

    Points ``iap_lms_reference`` at the candidate, asks it the same question it
    will be asked in production, and puts it back. Deliberately the production
    code path rather than a reimplementation -- a gate that is re-derived here
    could pass while the real one fails.
    """
    original = lms.LMS_PATH
    lms.LMS_PATH = candidate
    lms.reset_cache()
    try:
        loaded = lms._load()
        if loaded is None:
            return {"ok": False, "reason": "file parsed to nothing usable"}
        report = lms._reproduction()
        return {**report, "available": lms.lms_available()}
    finally:
        lms.LMS_PATH = original
        lms.reset_cache()


def ingest(source: Path, *, install: bool = False, supplied_by: str = "",
           received: str = "", note: str = "") -> dict:
    rows = normalise(source)
    cov = coverage(rows)
    problems = _sanity(rows)

    result = {
        "source": str(source),
        "rows_read": len(rows),
        "coverage": cov,
        "sanity_problems": problems,
        "installed": False,
    }
    if not cov["complete"] or problems:
        result["gate"] = {"ok": False, "reason": "not evaluated — fix the above first"}
        return result

    staged = source.parent / (source.stem + ".canonical.csv")
    write_canonical(rows, staged)
    result["staged"] = str(staged)
    result["gate"] = evaluate(staged)

    if install and result["gate"].get("ok"):
        shutil.copyfile(staged, lms.LMS_PATH)
        lms.reset_cache()
        PROVENANCE_PATH.write_text(json.dumps({
            "installed_on": date.today().isoformat(),
            "source_file": source.name,
            "supplied_by": supplied_by,
            "received": received,
            "note": note,
            "rows": len(rows),
            "gate": {k: result["gate"][k] for k in ("checked", "worst", "tolerance")
                     if k in result["gate"]},
        }, indent=2) + "\n", encoding="utf-8")
        result["installed"] = True
        result["provenance"] = str(PROVENANCE_PATH)
    return result


def _print(result: dict) -> None:
    print(f"source            {result['source']}")
    print(f"rows read         {result['rows_read']}")

    cov = result["coverage"]
    print(f"coverage          {'complete' if cov['complete'] else 'INCOMPLETE'}")
    for name, info in cov["series"].items():
        flag = "" if not info["missing_ages"] else \
            f"   MISSING {len(info['missing_ages'])}: {info['missing_ages'][:6]}"
        print(f"  {name:<14} {info['present']}/{info['required']}{flag}")

    if result["sanity_problems"]:
        print(f"\nstructural problems ({len(result['sanity_problems'])}):")
        for p in result["sanity_problems"][:10]:
            print(f"  - {p}")

    gate = result.get("gate", {})
    print(f"\ngate              {'PASS' if gate.get('ok') else 'FAIL'}  — {gate.get('reason')}")
    if "worst" in gate:
        print(f"  judged {gate['checked']} cells against columns "
              f"{gate.get('gate_centiles')}")
        for measure, worst in sorted(gate["worst"].items()):
            tol = gate["tolerance"][measure]
            print(f"    {measure:<7} worst {worst:.4f}  tolerance {tol}  "
                  f"{'ok' if worst <= tol else 'OVER'}")
    if gate.get("advisory_worst"):
        print(f"  advisory ({gate['advisory_checked']} cells, not judged — "
              "columns the CSVs reconstructed):")
        for measure, worst in sorted(gate["advisory_worst"].items()):
            print(f"    {measure:<7} worst {worst:.4f}")

    if result["installed"]:
        print(f"\nINSTALLED to {lms.LMS_PATH}")
        print(f"provenance   {result['provenance']}")
        print("The LMS path is now live for every consumer of iap_reference.")
    elif gate.get("ok"):
        print("\nGate passed. Re-run with --install to put it in place.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalise, verify and install the IAP 2015 L,M,S values.")
    parser.add_argument("source", type=Path, help="CSV supplied by the authors")
    parser.add_argument("--install", action="store_true",
                        help="install on a PASS (without this, reports only)")
    parser.add_argument("--supplied-by", default="", help="who provided the file")
    parser.add_argument("--received", default="", help="date received, YYYY-MM-DD")
    parser.add_argument("--note", default="", help="free-text provenance note")
    parser.add_argument("--consistency", action="store_true",
                        help="print the CSV column-consistency diagnosis and exit")
    args = parser.parse_args(argv)

    if args.consistency:
        print(json.dumps(consistency.consistency_report(), indent=2))
        return 0

    try:
        result = ingest(args.source, install=args.install,
                        supplied_by=args.supplied_by, received=args.received,
                        note=args.note)
    except IngestError as exc:
        print(f"cannot ingest: {exc}", file=sys.stderr)
        return 2

    _print(result)
    return 0 if result.get("gate", {}).get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

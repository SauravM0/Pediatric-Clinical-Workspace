"""Install the Indian height-velocity reference and prove it is usable (M1.3).

    python -m backend.growth.ingest_velocity_reference received.csv
    python -m backend.growth.ingest_velocity_reference received.csv --install \\
        --supplied-by "Dr A Khadilkar (HCJMRI)" --received 2026-08-09

    Khadilkar V, Khadilkar A, Arya A, et al. Height Velocity Percentiles in
    Indian Children Aged 5-17 Years. Indian Pediatr 2019;56(1):23-8.

Sibling of ``ingest_iap_lms``, and deliberately the same shape: normalise the
supplier's spelling, report coverage before judging any number, run the REAL
activation gate rather than a reimplementation of it, refuse to install a file
that fails, and record who supplied it.

Two things differ, both because velocity is a different kind of reference
---------------------------------------------------------------------------
**The gate is a shape check, not a reproduction check.** M1.1 could ask "do
these parameters regenerate the published percentile table?" because the table
is in the repo. Here there is no table to reproduce -- so the gate asks whether
the installed median peaks where the paper says it does (boys 6.8 cm/yr at
13.5y, girls 6.6 at 10.5y). That is weaker, and it is honest about being
weaker: it catches the failures that actually happen (sex columns swapped,
distance values entered instead of velocity, an off-by-one age column) and it
cannot certify precision. Provenance carries the rest, as in M1.1.

**A velocity table can be accepted as monotone-looking nonsense.** A distance
reference is checked against 27 ages of published values; a velocity reference
has a distinctive shape -- a mid-childhood decline, a pubertal peak, then a
fall to near zero -- and a file that lacks that shape is not this reference
whatever its peak happens to be. So the shape is checked too, not just the peak.

Accepted input
--------------
One row per (sex, age) with recognisable headers:

    sex     sex, gender          -> boy(s) / girl(s) / m / f
    age     age, age_years       -> 5.0 .. 17.5
    L, M, S L/lambda, M/mu/median, S/sigma/cv    (M in cm/year)
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np

from . import velocity_reference as vr
from .ingest_iap_lms import IngestError, header_key

PROVENANCE_PATH = vr.REFERENCE_PATH.parent / "indian_height_velocity_provenance.json"

# Ages the reference should cover. The paper runs 5-17y; 17.5 is the module's
# own AGE_MAX. Coverage is reported against 0.5y steps but not demanded at every
# one -- published velocity tables are sometimes annual, and _load already
# refuses a table too sparse to interpolate across the peak.
MIN_AGES_PER_SEX = 8

_SEX_ALIASES = {
    "boy": "boy", "boys": "boy", "male": "boy", "m": "boy",
    "girl": "girl", "girls": "girl", "female": "girl", "f": "girl",
}
_COLUMN_ALIASES = {
    "sex": ("sex", "gender"),
    "age": ("age", "age_years", "age_yr", "age_y", "ageyears", "age_at_midpoint"),
    "L": ("l", "lambda", "skew"),
    "M": ("m", "mu", "median", "median_velocity", "velocity"),
    "S": ("s", "sigma", "cv", "coefficient_of_variation"),
}

# Upper bound only. A median velocity above this is not a velocity: a DISTANCE
# table entered by mistake reads as 100+, which is the error this catches.
#
# There is deliberately NO meaningful lower bound beyond "positive". The first
# draft used 0.5 cm/year and it rejected a perfectly good table, because by 17.5y
# the median velocity genuinely approaches zero -- growth stops. A floor here
# would have refused the authors' real file at exactly the ages where it is
# behaving correctly.
MAX_PLAUSIBLE_VELOCITY = 15.0


def _resolve_columns(fieldnames) -> dict[str, str]:
    present = {header_key(f): f for f in fieldnames}
    resolved = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in present:
                resolved[canonical] = present[alias]
                break
    missing = [c for c in _COLUMN_ALIASES if c not in resolved]
    if missing:
        raise IngestError(
            f"could not find column(s) {missing} in {sorted(present)}. "
            "Recognised: " + "; ".join(f"{k}={'/'.join(v)}" for k, v in _COLUMN_ALIASES.items())
        )
    return resolved


def normalise(source: Path) -> list[tuple[str, float, float, float, float]]:
    with open(source, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(
            ln for ln in f if not ln.lstrip().startswith("#")
        )
        if not reader.fieldnames:
            raise IngestError(f"{source} has no header row")
        cols = _resolve_columns(reader.fieldnames)

        rows = []
        for lineno, raw in enumerate(reader, start=2):
            if not (raw.get(cols["sex"]) or "").strip():
                continue
            sex = _SEX_ALIASES.get(str(raw[cols["sex"]]).strip().lower())
            if sex is None:
                raise IngestError(f"line {lineno}: unrecognised sex {raw[cols['sex']]!r}")
            try:
                age = round(float(raw[cols["age"]]), 2)
                l, m, s = (float(raw[cols[k]]) for k in ("L", "M", "S"))
            except (TypeError, ValueError) as exc:
                raise IngestError(f"line {lineno}: {exc}") from exc
            rows.append((sex, age, l, m, s))

    if not rows:
        raise IngestError(f"{source} contains a header but no data rows")
    return rows


def coverage(rows) -> dict:
    have: dict[str, list[float]] = {}
    for sex, age, *_ in rows:
        have.setdefault(sex, []).append(age)

    report, complete = {}, True
    for sex in ("boy", "girl"):
        ages = sorted(have.get(sex, []))
        in_range = [a for a in ages if vr.AGE_MIN <= a <= vr.AGE_MAX]
        enough = len(in_range) >= MIN_AGES_PER_SEX
        # The pubertal peak is the part that matters; a table that stops before
        # it can still look well-covered on a count alone.
        peak_age = vr.EXPECTED_PEAK[{"boy": "boys", "girl": "girls"}[sex]]["age_years"]
        spans_peak = bool(in_range) and in_range[0] <= peak_age <= in_range[-1]
        complete = complete and enough and spans_peak
        report[sex] = {
            "ages": len(in_range),
            "minimum": MIN_AGES_PER_SEX,
            "range": [in_range[0], in_range[-1]] if in_range else None,
            "spans_pubertal_peak": spans_peak,
            "out_of_range_ages": [a for a in ages if not (vr.AGE_MIN <= a <= vr.AGE_MAX)],
        }
    return {"complete": complete, "series": report}


def _sanity(rows) -> list[str]:
    """Structural checks, so a mis-mapped column says which column."""
    problems = []
    for sex, age, l, m, s in rows:
        where = f"{sex}@{age}"
        if m <= 0:
            problems.append(f"{where}: M={m} cm/year — a median velocity must be positive")
        elif m > MAX_PLAUSIBLE_VELOCITY:
            problems.append(
                f"{where}: M={m} cm/year exceeds {MAX_PLAUSIBLE_VELOCITY}. M is a "
                "median VELOCITY — a value in the hundreds means a distance "
                "(height) table was supplied instead."
            )
        if not (0 < s < 1.0):
            problems.append(
                f"{where}: S={s} is outside (0, 1); S is a coefficient of "
                "variation, so this usually means L/M/S are the wrong way round."
            )
        if abs(l) > 5:
            problems.append(f"{where}: L={l} is implausible for Cole's lambda")
    return problems


def _shape(rows) -> dict:
    """Does the median actually look like a velocity curve?

    A peak in the right place is necessary but not sufficient: a table could be
    flat with one bump. Real height velocity falls through mid-childhood, peaks
    at puberty, then drops steeply toward zero. Checking the fall AFTER the peak
    is the cheap discriminator -- it is the feature no distance curve and no
    flat table has.
    """
    out, ok = {}, True
    for sex_csv, sex in (("boy", "boys"), ("girl", "girls")):
        pts = sorted((a, m) for s, a, _l, m, _s in rows if s == sex_csv)
        if len(pts) < 3:
            out[sex] = {"ok": False, "reason": "too few ages to assess shape"}
            ok = False
            continue
        ages = np.array([p[0] for p in pts])
        med = np.array([p[1] for p in pts])
        i = int(np.argmax(med))
        after = med[i:]
        # From the peak to the end of the table the median must fall
        # substantially — puberty ends and growth stops.
        # bool(), not the numpy scalar the comparison returns: this dict is
        # json.dumps'd into the provenance record, and np.bool_ is not
        # serialisable — it would fail at --install, after the copy.
        falls = bool(len(after) >= 2 and (after[-1] < 0.75 * med[i]))
        out[sex] = {
            "ok": falls,
            "peak_cm_per_year": round(float(med[i]), 2),
            "peak_age_years": round(float(ages[i]), 2),
            "final_cm_per_year": round(float(med[-1]), 2),
            "reason": "ok" if falls else (
                "the median does not fall away after its peak. Height velocity "
                "drops steeply once puberty ends, so a table that stays high is "
                "not a velocity reference (or stops before growth does)."
            ),
        }
        ok = ok and falls
    return {"ok": ok, "series": out}


def write_canonical(rows, destination: Path) -> int:
    ordered = sorted(rows, key=lambda r: (r[0], r[1]))
    with open(destination, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sex", "age_years", "L", "M", "S"])
        for sex, age, l, m, s in ordered:
            w.writerow([sex, f"{age:g}", f"{l:.6f}", f"{m:.6f}", f"{s:.6f}"])
    return len(ordered)


def evaluate(candidate: Path) -> dict:
    """Run the production activation gate against a candidate file."""
    original = vr.REFERENCE_PATH
    vr.REFERENCE_PATH = candidate
    vr.reset_cache()
    try:
        if vr._load() is None:
            return {"ok": False, "reason": "file parsed to nothing usable"}
        check = vr._peak_check()
        return {**check, "available": vr.reference_available()}
    except vr.VelocityReferenceError as exc:
        return {"ok": False, "reason": str(exc)}
    finally:
        vr.REFERENCE_PATH = original
        vr.reset_cache()


def ingest(source: Path, *, install: bool = False, supplied_by: str = "",
           received: str = "", note: str = "") -> dict:
    rows = normalise(source)
    cov = coverage(rows)
    problems = _sanity(rows)
    shape = _shape(rows)

    result = {
        "source": str(source),
        "rows_read": len(rows),
        "coverage": cov,
        "sanity_problems": problems,
        "shape": shape,
        "installed": False,
    }
    if not cov["complete"] or problems or not shape["ok"]:
        result["gate"] = {"ok": False, "reason": "not evaluated — fix the above first"}
        return result

    staged = source.parent / (source.stem + ".canonical.csv")
    write_canonical(rows, staged)
    result["staged"] = str(staged)
    result["gate"] = evaluate(staged)

    if install and result["gate"].get("ok"):
        shutil.copyfile(staged, vr.REFERENCE_PATH)
        vr.reset_cache()
        PROVENANCE_PATH.write_text(json.dumps({
            "installed_on": date.today().isoformat(),
            "source_file": source.name,
            "supplied_by": supplied_by,
            "received": received,
            "note": note,
            "rows": len(rows),
            "reference": "Khadilkar et al., Indian Pediatr 2019;56(1):23-8",
            "peak_check": result["gate"].get("observed"),
        }, indent=2) + "\n", encoding="utf-8")
        result["installed"] = True
        result["provenance"] = str(PROVENANCE_PATH)
    return result


def _print(result: dict) -> None:
    print(f"source            {result['source']}")
    print(f"rows read         {result['rows_read']}")

    cov = result["coverage"]
    print(f"coverage          {'complete' if cov['complete'] else 'INCOMPLETE'}")
    for sex, info in cov["series"].items():
        peak = "spans peak" if info["spans_pubertal_peak"] else "DOES NOT SPAN PUBERTAL PEAK"
        print(f"  {sex:<6} {info['ages']} ages (min {info['minimum']}), "
              f"range {info['range']}, {peak}")

    if result["sanity_problems"]:
        print(f"\nstructural problems ({len(result['sanity_problems'])}):")
        for p in result["sanity_problems"][:10]:
            print(f"  - {p}")

    shape = result["shape"]
    print(f"\nshape             {'ok' if shape['ok'] else 'NOT A VELOCITY CURVE'}")
    for sex, info in shape["series"].items():
        if "peak_cm_per_year" in info:
            print(f"  {sex:<6} peak {info['peak_cm_per_year']} cm/yr at "
                  f"{info['peak_age_years']}y, ends at {info['final_cm_per_year']}")
        if not info["ok"]:
            print(f"         {info['reason']}")

    gate = result.get("gate", {})
    print(f"\ngate              {'PASS' if gate.get('ok') else 'FAIL'}  — {gate.get('reason')}")
    for sex, info in (gate.get("observed") or {}).items():
        print(f"  {sex:<6} observed {info['observed']}  expected {info['expected']}  "
              f"{'match' if info['matches'] else 'MISMATCH'}")

    if result["installed"]:
        print(f"\nINSTALLED to {vr.REFERENCE_PATH}")
        print(f"provenance   {result['provenance']}")
        print("LOW_HEIGHT_VELOCITY now scores against a centile instead of the "
              "4 cm/year floor.")
    elif gate.get("ok"):
        print("\nGate passed. Re-run with --install to put it in place.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalise, verify and install the Indian height-velocity reference.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--install", action="store_true",
                        help="install on a PASS (without this, reports only)")
    parser.add_argument("--supplied-by", default="")
    parser.add_argument("--received", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)

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

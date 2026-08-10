"""Install WHO's published L,M,S tables and prove they match the incumbent (M1.4).

    python -m backend.growth.ingest_who_lms --from-who /path/to/who_downloads
    python -m backend.growth.ingest_who_lms --from-installed-rcpchgrowth
    python -m backend.growth.ingest_who_lms --gate          # report only

Fourth ingestion tool, and the one with a licensing question attached
----------------------------------------------------------------------
There are two ways to obtain these tables and they are NOT equivalent:

``--from-who`` reads WHO's own published files. This is the correct provenance:
the WHO Multicentre Growth Reference Study tables are published by WHO for
exactly this use, and the resulting CSVs are WHO's data attributed to WHO.

``--from-installed-rcpchgrowth`` lifts the same numbers out of the installed
package. It exists because it makes the equivalence gate trivially passable and
lets the engine be verified today -- but ``rcpchgrowth`` is **AGPL-3.0**, and
whether extracting its bundled data files creates an obligation is a question
about that licence, not about this code. The underlying numbers are WHO's and
factual, which is a strong argument, but it is not this tool's call to make. So
the bootstrap records ``source: rcpchgrowth-<version>`` in the provenance file
and prints the caveat, and the acquisition doc recommends the WHO route before
distributing anything.

Either way the gate is the same: the tables must reproduce rcpchgrowth's output
across a dense grid before the WHO path activates.

Accepted input for --from-who
-----------------------------
Any CSV or JSON per (sex, measure) with an age column and L, M, S columns.
Recognised age spellings include ``age_years``, ``decimal_age``, ``Age``,
``Month`` and ``Day`` -- WHO publishes some tables by month and some by day, so
the unit is inferred from the column name and the value range, and reported
back for checking rather than assumed silently.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from . import measures as _measures
from . import who_lms_reference as who_lms
from .ingest_iap_lms import IngestError, header_key

PROVENANCE_PATH = who_lms._DATA_DIR / "PROVENANCE.json"

_SEX_ALIASES = {
    "boy": "boys", "boys": "boys", "male": "boys", "m": "boys", "1": "boys",
    "girl": "girls", "girls": "girls", "female": "girls", "f": "girls", "2": "girls",
}
_MEASURE_ALIASES = {
    "height": "height", "length": "height", "stature": "height",
    "lhfa": "height", "hfa": "height", "lfa": "height",
    "weight": "weight", "wfa": "weight",
    "bmi": "bmi", "bfa": "bmi", "bmifa": "bmi",
}

# Age columns, with the unit each implies. WHO ships some tables by day and
# some by month; guessing wrong scales every age by 30x, which the gate would
# catch but only after an opaque failure.
_AGE_COLUMNS = {
    "age_years": 1.0, "decimal_age": 1.0, "age": None,      # None -> infer
    "month": 1 / 12, "agemos": 1 / 12, "months": 1 / 12,
    "day": 1 / 365.25, "days": 1 / 365.25, "agedays": 1 / 365.25,
}


def _infer_age_scale(column: str, values: list[float]) -> tuple[float, str]:
    """Years per unit, and how it was decided."""
    declared = _AGE_COLUMNS.get(column)
    if declared is not None:
        return declared, f"column name {column!r}"
    top = max(values) if values else 0.0
    if top <= 20:
        return 1.0, f"max value {top:g} -> years"
    if top <= 240:
        return 1 / 12, f"max value {top:g} -> months"
    return 1 / 365.25, f"max value {top:g} -> days"


def _classify(path: Path) -> tuple[Optional[str], Optional[str]]:
    """(sex, measure) from a filename, or (None, None) when not decidable."""
    tokens = re.split(r"[^a-z0-9]+", path.stem.lower())
    sex = next((_SEX_ALIASES[t] for t in tokens if t in _SEX_ALIASES), None)
    measure = next((_MEASURE_ALIASES[t] for t in tokens if t in _MEASURE_ALIASES), None)
    return sex, measure


def _rows_from(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        blob = json.loads(path.read_text(encoding="utf-8"))
        data = blob.get("data", blob) if isinstance(blob, dict) else blob
        if not isinstance(data, list):
            raise IngestError(f"{path.name}: expected a list of rows under 'data'")
        return data
    with open(path, newline="", encoding="utf-8-sig") as f:
        # WHO's text tables are sometimes tab-separated.
        sample = f.read(4096)
        f.seek(0)
        delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
        return list(csv.DictReader(f, delimiter=delimiter))


def normalise_file(path: Path) -> tuple[str, str, list[tuple[float, float, float, float]], str]:
    """(sex, measure, [(age_years, L, M, S)], how the age unit was decided)."""
    sex, measure = _classify(path)
    if sex is None or measure is None:
        raise IngestError(
            f"cannot tell which table {path.name} is. Include the sex and the "
            "measure in the filename, e.g. who_boys_height.csv"
        )

    rows = _rows_from(path)
    if not rows:
        raise IngestError(f"{path.name} has no rows")

    keys = {header_key(k): k for k in rows[0]}
    age_key = next((keys[k] for k in _AGE_COLUMNS if k in keys), None)
    lms = {p: keys.get(p.lower()) for p in ("L", "M", "S")}
    if age_key is None or not all(lms.values()):
        raise IngestError(
            f"{path.name}: need an age column and L, M, S. Found {sorted(keys)}. "
            f"Recognised age columns: {sorted(_AGE_COLUMNS)}"
        )

    raw_ages = []
    triples = []
    for i, row in enumerate(rows, start=2):
        try:
            raw_ages.append(float(row[age_key]))
            triples.append((float(row[lms["L"]]), float(row[lms["M"]]), float(row[lms["S"]])))
        except (TypeError, ValueError) as exc:
            raise IngestError(f"{path.name} line {i}: {exc}") from exc

    scale, how = _infer_age_scale(header_key(age_key), raw_ages)
    out = [(round(a * scale, 6), l, m, s) for a, (l, m, s) in zip(raw_ages, triples)]
    out.sort(key=lambda r: r[0])
    return sex, measure, out, how


def write_table(sex: str, measure: str, rows: Iterable[tuple[float, float, float, float]]) -> Path:
    path = who_lms.table_path(measure, sex)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["age_years", "L", "M", "S"])
        for age, l, m, s in rows:
            w.writerow([f"{age:g}", f"{l:.6f}", f"{m:.6f}", f"{s:.6f}"])
    return path


def from_who(source: Path) -> dict:
    """Normalise every recognisable table in a directory of WHO downloads."""
    if not source.is_dir():
        raise IngestError(f"{source} is not a directory")
    candidates = [p for p in sorted(source.iterdir())
                  if p.suffix.lower() in (".csv", ".txt", ".tsv", ".json")]
    if not candidates:
        raise IngestError(f"no CSV/TXT/TSV/JSON files in {source}")

    merged: dict[tuple[str, str], dict[str, list]] = {}
    notes = []
    skipped = []
    for path in candidates:
        try:
            sex, measure, rows, how = normalise_file(path)
        except IngestError as exc:
            skipped.append(f"{path.name}: {exc}")
            continue
        if measure not in who_lms.MEASURES:
            skipped.append(f"{path.name}: {measure} is not charted here")
            continue
        # WHO splits under-five and over-five into separate studies whose ranges
        # OVERLAP; which band a file belongs to decides the handoff, so it is
        # tracked rather than merged away. See _write_merged.
        band = _band_of(path.name)
        merged.setdefault((sex, measure), {}).setdefault(band, []).extend(rows)
        notes.append(f"{path.name} -> {sex}/{measure} [{band}-five] "
                     f"({len(rows)} rows, age via {how})")

    written = _write_merged(merged)
    return {"written": written, "notes": notes, "skipped": skipped,
            "source": str(source), "provenance_source": "WHO published tables"}


def _write_merged(merged: dict[tuple[str, str], dict[str, list]]) -> list[str]:
    """One table per (sex, measure), with an explicit handoff between bands.

    WHO publishes under-five and over-five as two separate studies, and their
    ranges OVERLAP: the under-five table runs to ~5.081y while the over-five one
    starts at 5.0. They carry different L and S there -- two descriptions of the
    same age from two documents.

    Interleaving both into one interpolant is wrong and was measurably wrong: it
    put an over-five L/S row between two under-five neighbours, and the resulting
    kink moved the +-3 SD lines by up to 0.55 cm at exactly 5.0y. The median was
    fine, which is why only the tails showed it.

    So the overlap is resolved by RANGE, not by deduplication: under-five owns
    everything up to its own last age, over-five owns everything above. That is
    also what rcpchgrowth does, which is why the gate now agrees with it.
    """
    written = []
    for (sex, measure), bands in sorted(merged.items()):
        under = sorted(bands.get("under", []), key=lambda r: r[0])
        over = sorted(bands.get("over", []), key=lambda r: r[0])
        if under and over:
            handoff = under[-1][0]
            rows = under + [r for r in over if r[0] > handoff]
        else:
            rows = under or over
        # Any residual duplicate age would still break a monotone interpolant.
        by_age = {}
        for age, l, m, s in sorted(rows, key=lambda r: r[0]):
            by_age[round(age, 6)] = (l, m, s)
        flat = [(a, *by_age[a]) for a in sorted(by_age)]
        written.append(str(write_table(sex, measure, flat)))
    return written


def _band_of(name: str) -> str:
    """Which WHO study a file belongs to. Defaults to 'under' so a single
    combined file (some WHO exports are one table) is not silently split."""
    lowered = name.lower()
    if "over_five" in lowered or "over-five" in lowered or "5_19" in lowered:
        return "over"
    return "under"


def from_installed_rcpchgrowth() -> dict:
    """Bootstrap: lift the same WHO numbers out of the installed package.

    Convenience for verifying the engine today, not a substitute for WHO
    provenance -- see the module docstring on the AGPL question.
    """
    try:
        import rcpchgrowth as rg
    except ImportError as exc:
        raise IngestError("rcpchgrowth is not installed; nothing to bootstrap from") from exc

    from importlib.metadata import PackageNotFoundError, version
    try:
        installed = version("rcpchgrowth")
    except PackageNotFoundError:
        installed = "unknown"

    tables = Path(rg.__file__).parent / "data_tables" / "who"
    if not tables.is_dir():
        raise IngestError(f"expected WHO tables at {tables}")

    merged: dict[tuple[str, str], dict[str, list]] = {}
    notes = []
    for path in sorted(tables.glob("who_*_five_*.json")):
        sex, measure = _classify(path)
        if sex is None or measure is None or measure not in who_lms.MEASURES:
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        rows = [(float(r["decimal_age"]), float(r["L"]), float(r["M"]), float(r["S"]))
                for r in blob["data"]]
        band = _band_of(path.name)
        merged.setdefault((sex, measure), {}).setdefault(band, []).extend(rows)
        notes.append(f"{path.name} -> {sex}/{measure} [{band}-five] ({len(rows)} rows)")

    written = _write_merged(merged)
    return {"written": written, "notes": notes, "skipped": [],
            "source": str(tables),
            "provenance_source": f"rcpchgrowth-{installed} (bootstrap)",
            "licence_caveat": (
                "Extracted from an AGPL-3.0 package. The numbers themselves are "
                "WHO's published data, but confirm the licensing position before "
                "distributing these files -- or re-run with --from-who."
            )}


def run_gate() -> dict:
    who_lms.reset_cache()
    return who_lms.lms_status()


def write_provenance(result: dict, gate: dict) -> Path:
    PROVENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROVENANCE_PATH.write_text(json.dumps({
        "installed_on": date.today().isoformat(),
        "source": result.get("provenance_source"),
        "source_path": result.get("source"),
        "files": [Path(p).name for p in result.get("written", [])],
        "licence_caveat": result.get("licence_caveat"),
        "reference": "WHO Multicentre Growth Reference Study (WHO 2006 / 2007)",
        "gate": {k: gate.get(k) for k in ("active", "reason") if k in gate},
        "equivalence": {k: (gate.get("equivalence") or {}).get(k)
                        for k in ("checked", "worst", "tolerance")},
    }, indent=2) + "\n", encoding="utf-8")
    return PROVENANCE_PATH


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Install WHO LMS tables and check them against rcpchgrowth.")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--from-who", type=Path, metavar="DIR",
                     help="directory of WHO's published tables")
    src.add_argument("--from-installed-rcpchgrowth", action="store_true",
                     help="bootstrap from the installed package (see --help notes)")
    p.add_argument("--gate", action="store_true", help="run the gate only")
    args = p.parse_args(argv)

    if args.gate or (not args.from_who and not args.from_installed_rcpchgrowth):
        # Once, not twice: each run makes ~11k calls into the incumbent.
        gate = run_gate()
        print(json.dumps(gate, indent=2))
        return 0 if gate.get("active") else 1

    try:
        result = from_who(args.from_who) if args.from_who else from_installed_rcpchgrowth()
    except IngestError as exc:
        print(f"cannot ingest: {exc}", file=sys.stderr)
        return 2

    for note in result["notes"]:
        print(f"  {note}")
    for skip in result["skipped"]:
        print(f"  skipped {skip}", file=sys.stderr)
    print(f"\nwrote {len(result['written'])} table(s)")

    gate = run_gate()
    print(f"gate: {'PASS' if gate.get('active') else 'FAIL'} — {gate.get('reason')}")
    eq = gate.get("equivalence") or {}
    if eq.get("checked"):
        print(f"  {eq['checked']} points compared against rcpchgrowth")
        for measure, worst in sorted((eq.get("worst") or {}).items()):
            tol = eq["tolerance"][measure]
            mark = "ok" if worst <= tol else "OVER"
            print(f"    {measure:<7} worst {worst:.5f}  tolerance {tol}  {mark}"
                  f"   at {(eq.get('worst_at') or {}).get(measure, '?')}")

    print(f"provenance: {write_provenance(result, gate)}")
    if result.get("licence_caveat"):
        print(f"\nNOTE: {result['licence_caveat']}")
    if gate.get("active"):
        print("\nWHO tables are live. rcpchgrowth can now be removed from "
              "requirements.txt — do that as a SEPARATE step, since it is the "
              "oracle this gate depends on.")
    return 0 if gate.get("active") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

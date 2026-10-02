"""Install the AAP 2017 paediatric blood-pressure tables (step 5).

    python -m backend.vitals.ingest_aap_bp first.csv --compare second.csv
    python -m backend.vitals.ingest_aap_bp first.csv --compare second.csv --install \\
        --entered-by "Dr A Rao" --verified-by "Dr S Menon" \\
        --source "Flynn et al. Pediatrics 2017;140(3):e20171904, Tables 4-5"
    python -m backend.vitals.ingest_aap_bp --status

Accepted input: CSV, one row per (sex, age, height percentile) --

    sex, age, height_percentile, height_cm,
    sbp_50, sbp_90, sbp_95, sbp_95_12, dbp_50, dbp_90, dbp_95, dbp_95_12

Header spellings are absorbed (`Gender`, `Age (y)`, `Height %ile`, `SBP 95th+12`,
...). Lines starting with # are ignored. Ages 1-12 are required; 13-17 are
accepted and ignored (from 13 the guideline uses fixed thresholds).

What the checks can and cannot tell you
---------------------------------------
The gate is aap_bp_reference.table_problems, the SAME function the running app
uses to decide whether the table is usable -- not a reimplementation. It catches
missing cells, inches for centimetres, centiles out of order, a slipped row
(every "95th + 12" cell must equal its 95th cell + 12, which the paper
guarantees), and heights that do not grow with age.

It cannot tell a plausible wrong number from the right one: there is no second
published copy in this repository. That is what --compare (two independent
transcriptions, diffed cell by cell) and the recorded entered_by / verified_by
are for, and installation requires both people to be named and different.
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

from . import aap_bp_reference as ref

_SEX = {"boy": "boys", "boys": "boys", "male": "boys", "m": "boys",
        "girl": "girls", "girls": "girls", "female": "girls", "f": "girls"}
_COLS = {
    "sex": ("sex", "gender"),
    "age": ("age", "age_y", "age_years", "age_yr"),
    "height_percentile": ("height_percentile", "height_pct", "height_ile", "height_centile",
                          "ht_pct", "percentile_of_height"),
    "height_cm": ("height_cm", "height", "ht_cm"),
    "sbp_p50": ("sbp_50", "sbp_50th", "sbp_p50"),
    "sbp_p90": ("sbp_90", "sbp_90th", "sbp_p90"),
    "sbp_p95": ("sbp_95", "sbp_95th", "sbp_p95"),
    "sbp_p95_12": ("sbp_95_12", "sbp_95th_12", "sbp_95th_12_mm_hg", "sbp_p95_12", "sbp_95_plus_12"),
    "dbp_p50": ("dbp_50", "dbp_50th", "dbp_p50"),
    "dbp_p90": ("dbp_90", "dbp_90th", "dbp_p90"),
    "dbp_p95": ("dbp_95", "dbp_95th", "dbp_p95"),
    "dbp_p95_12": ("dbp_95_12", "dbp_95th_12", "dbp_95th_12_mm_hg", "dbp_p95_12", "dbp_95_plus_12"),
}


def normalise(source: Path) -> dict:
    """Parse to {'boys': {'7': {'50': {height_cm, sbp_p50, ...}}}, 'girls': {...}}."""
    with open(source, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(ln for ln in f if not ln.lstrip().startswith("#")))
    if not rows:
        raise IngestError(f"{source.name} has no data rows")
    present = {header_key(h): h for h in rows[0].keys()}
    cols = {}
    for canon, aliases in _COLS.items():
        hit = next((present[a] for a in aliases if a in present), None)
        if hit is None:
            raise IngestError(f"no column for {canon!r} in {sorted(present)}")
        cols[canon] = hit

    out: dict = {"boys": {}, "girls": {}}
    for lineno, raw in enumerate(rows, start=2):
        sex = _SEX.get(str(raw[cols["sex"]]).strip().lower())
        if sex is None:
            raise IngestError(f"line {lineno}: unrecognised sex {raw[cols['sex']]!r}")
        try:
            age = int(float(raw[cols["age"]]))
            pct = int(float(str(raw[cols["height_percentile"]]).strip().rstrip("th").rstrip("%")))
            cell = {k: float(raw[cols[k]]) for k in cols if k not in ("sex", "age", "height_percentile")}
        except (TypeError, ValueError) as exc:
            raise IngestError(f"line {lineno}: {exc}") from exc
        if pct not in ref.HEIGHT_PERCENTILES:
            raise IngestError(f"line {lineno}: height percentile {pct} is not one of {ref.HEIGHT_PERCENTILES}")
        if age not in ref.REQUIRED_AGES + ref.OPTIONAL_AGES:
            raise IngestError(f"line {lineno}: age {age} is outside 1-17")
        slot = out[sex].setdefault(str(age), {})
        if str(pct) in slot:
            raise IngestError(f"line {lineno}: duplicate row for {sex} age {age} h{pct}")
        slot[str(pct)] = cell
    return out


def build_document(rows: dict, *, entered_by: str = "", verified_by: str = "",
                   source_note: str = "", note: str = "") -> dict:
    return {
        "_about": ("AAP 2017 paediatric BP tables (ages 1-12 used), transcribed by the "
                   "clinic from the guideline and double-checked. Indexed by height in cm."),
        "reference": ref.REFERENCE,
        "rows": rows,
        "provenance": {"entered_on": date.today().isoformat(), "entered_by": entered_by,
                       "verified_by": verified_by, "source": source_note, "note": note},
        "checksum": ref.checksum(rows),
    }


def ingest(source: Path, *, install: bool = False, compare: Optional[Path] = None,
           **provenance) -> dict:
    rows = normalise(source)
    result: dict = {"source": str(source), "installed": False,
                    "rows": {s: sum(len(v) for v in rows[s].values()) for s in ref.SEXES}}
    if compare is not None:
        other = normalise(compare)
        diffs = []
        for sex in ref.SEXES:
            for age in sorted(set(rows[sex]) | set(other[sex]), key=int):
                for pct in map(str, ref.HEIGHT_PERCENTILES):
                    a = (rows[sex].get(age) or {}).get(pct)
                    b = (other[sex].get(age) or {}).get(pct)
                    if a != b:
                        diffs.append({"sex": sex, "age": age, "height_pct": pct, "first": a, "second": b})
        result["double_entry"] = {"compared_with": str(compare), "differences": diffs, "match": not diffs}

    doc = build_document(rows, **provenance)
    everything = ref.table_problems(doc)
    result["data_problems"] = [p for p in everything if not p.startswith("provenance")]
    result["provenance_problems"] = [p for p in everything if p.startswith("provenance")]
    data_ok = not result["data_problems"] and (compare is None or result["double_entry"]["match"])
    result["verdict"] = {"data_ok": data_ok,
                         "installable": data_ok and compare is not None and not result["provenance_problems"]}
    if install:
        if not result["verdict"]["installable"]:
            raise IngestError(
                "refusing to install: needs clean data, a matching --compare second "
                "transcription, and --entered-by / --verified-by (different people) / --source")
        ref.TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ref.TABLE_PATH.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        ref.reset_cache()
        result["installed"] = True
        result["status"] = ref.status()
    return result


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Install the AAP 2017 paediatric BP tables.")
    p.add_argument("source", type=Path, nargs="?")
    p.add_argument("--compare", type=Path)
    p.add_argument("--install", action="store_true")
    p.add_argument("--entered-by", default="")
    p.add_argument("--verified-by", default="")
    p.add_argument("--source", dest="source_note", default="")
    p.add_argument("--note", default="")
    p.add_argument("--status", action="store_true")
    a = p.parse_args(argv)
    if a.status or a.source is None:
        s = ref.status()
        print(json.dumps(s, indent=2, ensure_ascii=False))
        return 0 if s["active"] else 1
    try:
        r = ingest(a.source, install=a.install, compare=a.compare, entered_by=a.entered_by,
                   verified_by=a.verified_by, source_note=a.source_note, note=a.note)
    except IngestError as exc:
        print(f"cannot ingest: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=1, ensure_ascii=False, default=str))
    return 0 if r["verdict"]["data_ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

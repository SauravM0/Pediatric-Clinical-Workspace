"""Install the licensed TW3 percentage-of-adult-height table (M2C).

    python -m backend.tw3.ingest_adult_height percentages.csv
    python -m backend.tw3.ingest_adult_height percentages.csv --install \\
        --book-title "Assessment of Skeletal Maturity and Prediction of Adult Height (TW3)" \\
        --edition "3rd" --licensed-owner "Sunrise Children's Clinic, Pune" \\
        --entered-by "Dr A Rao" --verified-by "Dr S Menon" --verification-date 2026-08-09

    Tanner JM, Healy MJR, Goldstein H, Cameron N. Assessment of Skeletal
    Maturity and Prediction of Adult Height (TW3 Method), 3rd ed. 2001.

Third of the ingestion tools, and the only one for **copyrighted** values
-------------------------------------------------------------------------
The IAP LMS and velocity references are published data this project may hold
once an author supplies them. These percentages are not: they belong to the TW3
book and may only be entered by a clinic **from its own licensed copy**. So the
provenance fields here are not bookkeeping -- they are the legal basis for the
values being on disk at all, and ``--install`` refuses without them. Nothing in
this repository ships, or ever should ship, a populated ``pct_adult_height``.

That is also why this tool writes through ``letters_scoring.save_letter_tables``
rather than editing JSON: that path revalidates the whole file and rewrites the
checksum, so the entered values land tamper-locked. Hand-editing the JSON leaves
the checksum stale, which correctly disables the table -- and looks like the
tool failing rather than the lock working.

What is checked
---------------
1. **Structure** - two numeric columns, bone age and percent, per sex.
2. **Shape** - monotone rising and approaching 100% at maturity, via
   ``adult_height.shape_problems``. Catches fractions entered as percentages,
   transposed columns and a swapped sex column.
3. **Licensing** - every field in ``REQUIRED_PROVENANCE_FIELDS``, then the
   checksum lock that ``save_letter_tables`` applies.

There is no reproduction gate: unlike M1.1 there is no second copy of these
numbers to check against, and unlike M1.3 no published landmark. A clinic
transcribing from its own book is the authority, and the honest position is that
the tool verifies shape and licence, not accuracy. Enter twice and diff if the
values matter -- ``--compare`` does that for you.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

from backend.growth.ingest_iap_lms import IngestError, header_key

from . import adult_height as ah
from .letters_scoring import (
    REQUIRED_PROVENANCE_FIELDS, LetterTablesError, load_letter_tables,
    load_raw_tables, save_letter_tables,
)

_SEX_ALIASES = {
    "boy": "boys", "boys": "boys", "male": "boys", "m": "boys",
    "girl": "girls", "girls": "girls", "female": "girls", "f": "girls",
}
_COLUMN_ALIASES = {
    "sex": ("sex", "gender"),
    "bone_age": ("bone_age", "bone_age_years", "ba", "skeletal_age", "age", "age_years"),
    "percent": ("percent", "percent_attained", "attained", "pct", "percentage",
                "percent_of_adult_height", "pct_adult_height"),
}

# Tried only when no alias matches exactly. Book tables are transcribed by hand
# and the percent column in particular arrives spelled every possible way --
# '% attained', '% of adult ht', 'Percentage of Adult Height'. header_key strips
# the punctuation, so a distinctive token is a better final guess than adding
# another alias each time someone finds a new phrasing.
#
# Ordered MOST DISTINCTIVE FIRST and applied globally, not per-column, because
# the obvious per-column loop misassigns: 'age' is a substring of 'percentage',
# so a file headed 'Percentage of adult height' would hand the percent column to
# bone_age. Claiming 'attain'/'percent' before 'age' is ever considered removes
# that whole class of mistake -- and on a licensed-values import, silently
# reading the wrong column is the worst available failure.
_TOKEN_PRIORITY: tuple[tuple[str, str], ...] = (
    ("sex", "sex"), ("sex", "gender"),
    ("percent", "attain"), ("percent", "percent"), ("percent", "pct"),
    ("bone_age", "bone"), ("bone_age", "skeletal"),
    ("percent", "adult"),
    ("bone_age", "age"),
)


def _resolve_columns(fieldnames) -> dict[str, str]:
    present = {header_key(f): f for f in fieldnames}
    resolved = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in present:
                resolved[canonical] = present[alias]
                break

    taken = set(resolved.values())
    for canonical, token in _TOKEN_PRIORITY:
        if canonical in resolved:
            continue
        for key, original in present.items():
            if original not in taken and token in key:
                resolved[canonical] = original
                taken.add(original)
                break

    missing = [c for c in _COLUMN_ALIASES if c not in resolved]
    if missing:
        raise IngestError(
            f"could not find column(s) {missing} in {sorted(present)}. Recognised: "
            + "; ".join(f"{k}={'/'.join(v)}" for k, v in _COLUMN_ALIASES.items())
        )
    return resolved


def normalise(source: Path) -> dict[str, list[list[float]]]:
    """Parse into {'boys': [[bone_age, percent], ...], 'girls': [...]}."""
    with open(source, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(ln for ln in f if not ln.lstrip().startswith("#"))
        if not reader.fieldnames:
            raise IngestError(f"{source} has no header row")
        cols = _resolve_columns(reader.fieldnames)

        out: dict[str, list[list[float]]] = {"boys": [], "girls": []}
        for lineno, raw in enumerate(reader, start=2):
            if not (raw.get(cols["sex"]) or "").strip():
                continue
            sex = _SEX_ALIASES.get(str(raw[cols["sex"]]).strip().lower())
            if sex is None:
                raise IngestError(f"line {lineno}: unrecognised sex {raw[cols['sex']]!r}")
            try:
                bone_age = round(float(raw[cols["bone_age"]]), 2)
                percent = float(raw[cols["percent"]])
            except (TypeError, ValueError) as exc:
                raise IngestError(f"line {lineno}: {exc}") from exc
            out[sex].append([bone_age, percent])

    for sex in ("boys", "girls"):
        out[sex].sort(key=lambda p: p[0])
    if not any(out.values()):
        raise IngestError(f"{source} contains a header but no data rows")
    return out


class _Candidate:
    """Minimal stand-in exposing what adult_height's checks read."""

    def __init__(self, table: dict, provenance: dict, checksum_verified: bool):
        self.raw = {"pct_adult_height": table}
        self._provenance = provenance
        self.checksum_verified = checksum_verified

    def missing_provenance(self) -> list[str]:
        return [f for f in REQUIRED_PROVENANCE_FIELDS
                if not str((self._provenance or {}).get(f, "")).strip()]


def coverage(table: dict) -> dict:
    report, complete = {}, True
    for sex in ("boys", "girls"):
        anchors = table.get(sex) or []
        ages = [a[0] for a in anchors]
        usable = len(anchors) >= 2
        # The method refuses below MIN_BONE_AGE_YEARS anyway, so a table that
        # starts above it is not a defect -- one that STOPS early is, because
        # every prediction past its end is refused.
        complete = complete and usable
        report[sex] = {
            "anchors": len(anchors),
            "bone_age_range": [min(ages), max(ages)] if ages else None,
            "usable": usable,
        }
    return {"complete": complete, "series": report}


def _provenance_from_args(args) -> dict:
    return {
        "book_title": args.book_title,
        "edition": args.edition,
        "isbn": args.isbn,
        "pages": args.pages,
        "licensed_owner": args.licensed_owner,
        "entered_by": args.entered_by,
        "verified_by": args.verified_by,
        "verification_date": args.verification_date,
    }


def ingest(source: Path, *, install: bool = False,
           provenance: Optional[dict] = None,
           compare: Optional[Path] = None) -> dict:
    table = normalise(source)
    cov = coverage(table)

    result: dict = {
        "source": str(source),
        "anchors_read": sum(len(v) for v in table.values()),
        "coverage": cov,
        "installed": False,
    }

    # Double entry, when asked for. There is no published copy to check these
    # against, so two independent transcriptions differing is the only
    # transcription check available.
    if compare is not None:
        other = normalise(compare)
        diffs = []
        for sex in ("boys", "girls"):
            a = {p[0]: p[1] for p in table.get(sex, [])}
            b = {p[0]: p[1] for p in other.get(sex, [])}
            for age in sorted(set(a) | set(b)):
                if a.get(age) != b.get(age):
                    diffs.append({"sex": sex, "bone_age": age,
                                  "first": a.get(age), "second": b.get(age)})
        result["double_entry"] = {"compared_with": str(compare),
                                  "differences": diffs, "match": not diffs}

    shape: dict[str, list[str]] = {}
    for sex in ("boys", "girls"):
        if table.get(sex):
            shape[sex] = ah.shape_problems(sex, _Candidate(table, {}, False))
    result["shape_problems"] = {k: v for k, v in shape.items() if v}

    prov = provenance or {}
    missing = [f for f in REQUIRED_PROVENANCE_FIELDS if not str(prov.get(f, "")).strip()]
    result["missing_provenance"] = missing

    blocked = (not cov["complete"] or result["shape_problems"]
               or (compare is not None and not result["double_entry"]["match"]))
    if blocked:
        result["verdict"] = {"ok": False, "reason": "fix the problems above"}
        return result
    if missing:
        result["verdict"] = {
            "ok": False,
            "reason": ("these are copyrighted TW3 values; the licensed source must "
                       "be documented before they may be stored or used. Missing: "
                       + ", ".join(missing)),
        }
        return result

    result["verdict"] = {"ok": True, "reason": "ok"}

    if install:
        data = load_raw_tables()
        if not data:
            raise IngestError(
                "letters_tables.json is missing or unreadable; refusing to create "
                "it from scratch — the licensed table file must already exist"
            )
        data["pct_adult_height"] = {
            **{k: v for k, v in (data.get("pct_adult_height") or {}).items()
               if str(k).startswith("_")},          # keep the _fill warning
            "boys": table["boys"],
            "girls": table["girls"],
        }
        existing = data.get("provenance") or {}
        data["provenance"] = {**existing, **{k: v for k, v in prov.items() if v}}
        # save_letter_tables revalidates the whole file and rewrites the
        # checksum, so the values land tamper-locked in one step.
        saved = save_letter_tables(data)
        result["installed"] = True
        result["checksum_verified"] = saved.checksum_verified
        result["gate"] = ah.licensing_gate(saved)
    return result


def _print(result: dict) -> None:
    print(f"source            {result['source']}")
    print(f"anchors read      {result['anchors_read']}")
    for sex, info in result["coverage"]["series"].items():
        print(f"  {sex:<6} {info['anchors']} anchors, bone age {info['bone_age_range']}"
              f"{'' if info['usable'] else '   NEEDS AT LEAST 2'}")

    if result.get("double_entry"):
        de = result["double_entry"]
        print(f"\ndouble entry      {'MATCH' if de['match'] else 'MISMATCH'} "
              f"vs {de['compared_with']}")
        for d in de["differences"][:10]:
            print(f"  {d['sex']} @ {d['bone_age']}y: {d['first']} vs {d['second']}")

    if result["shape_problems"]:
        print("\nshape problems:")
        for sex, problems in result["shape_problems"].items():
            for p in problems:
                print(f"  - {p}")

    if result["missing_provenance"]:
        print(f"\nmissing provenance: {', '.join(result['missing_provenance'])}")

    v = result.get("verdict", {})
    print(f"\nverdict           {'PASS' if v.get('ok') else 'FAIL'} — {v.get('reason')}")

    if result["installed"]:
        print("\nINSTALLED into letters_tables.json under 'pct_adult_height'")
        print(f"checksum locked   {result['checksum_verified']}")
        print(f"licensing gate    {'open' if result['gate']['ok'] else result['gate']['reasons']}")
        print("Adult-height prediction from bone age is now live on "
              "/api/patients/{id}/adult-height.")
    elif v.get("ok"):
        print("\nChecks passed. Re-run with --install and the provenance flags.")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Install the licensed TW3 percentage-of-adult-height table.")
    p.add_argument("source", type=Path)
    p.add_argument("--install", action="store_true")
    p.add_argument("--compare", type=Path, default=None,
                   help="second independent transcription to diff against")
    p.add_argument("--book-title", default="")
    p.add_argument("--edition", default="")
    p.add_argument("--isbn", default="")
    p.add_argument("--pages", default="")
    p.add_argument("--licensed-owner", default="")
    p.add_argument("--entered-by", default="")
    p.add_argument("--verified-by", default="")
    p.add_argument("--verification-date", default="")
    p.add_argument("--status", action="store_true",
                   help="print whether the table is currently usable, and exit")
    args = p.parse_args(argv)

    if args.status:
        try:
            tables = load_letter_tables()
        except LetterTablesError as exc:
            print(json.dumps({"usable": False, "reason": str(exc)}, indent=2))
            return 1
        gate = ah.licensing_gate(tables)
        print(json.dumps({
            "entered": {s: ah.is_calibrated(s, tables) for s in ("boys", "girls")},
            "shape_problems": {s: ah.shape_problems(s, tables)
                               for s in ("boys", "girls") if ah.is_calibrated(s, tables)},
            "licensing_gate": gate,
        }, indent=2))
        return 0

    try:
        result = ingest(args.source, install=args.install,
                        provenance=_provenance_from_args(args), compare=args.compare)
    except (IngestError, LetterTablesError) as exc:
        print(f"cannot ingest: {exc}", file=sys.stderr)
        return 2

    _print(result)
    return 0 if result.get("verdict", {}).get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

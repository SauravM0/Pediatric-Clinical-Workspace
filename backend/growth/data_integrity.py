"""Data-integrity + source-verification for the IAP 2015 growth CSVs (audit GC-1).

Two guarantees, both permanent and enforced by tests/growth/test_iap_source.py:

1. **Drift lock (active now).** A committed checksum manifest (``checksums.json``)
   pins the *numeric content* of the six published-derived CSVs. The checksum is
   taken over the parsed numbers, not the raw bytes, so reformatting or
   CRLF/LF changes never false-alarm -- but changing any value does. Nothing can
   silently alter a percentile.

2. **Source verification (incremental, human-entered).** The QA suite proves the
   *engine reproduces the CSVs*; it does NOT prove the CSVs match the published
   Khadilkar 2015 paper. ``iap_2015_published_reference.json`` holds authoritative
   values entered by a human verifier DIRECTLY from the paper (an independent
   second source -- never copied from the CSVs). Every entered cell is enforced
   against the CSV; the file cannot be marked ``VERIFIED`` until every cell is
   covered. This operationalises the audit's "dual-person, cell-by-cell" GC-1
   requirement one cell at a time, matching the codebase's "gate + test now,
   lawful values entered later" discipline.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
MANIFEST_PATH = DATA_DIR / "checksums.json"
REFERENCE_PATH = DATA_DIR / "iap_2015_published_reference.json"

# The six published-derived CSVs. Height/weight carry p3..p97; BMI carries
# p3/p5/p10/p25/p50 plus the IOTF adult-equivalent 23/27 cutoffs.
CSV_FILES: tuple[str, ...] = (
    "boy_height_cm_IAP_5_18.csv",
    "girl_height_cm_IAP_5_18.csv",
    "boy_weight_kg_IAP_5_18.csv",
    "girl_weight_kg_IAP_5_18.csv",
    "boy_bmi_IAP_5_18.csv",
    "girl_bmi_IAP_5_18.csv",
)

_NON_NUMERIC = {"sex", "age_years"}


def parse_csv(path: Path) -> dict[float, dict[str, float]]:
    """Parse one CSV into {age_years: {column: float}} for numeric columns.

    Values are floats, so a whitespace/line-ending/column-reorder change does not
    alter the parsed content -- only a changed number does."""
    rows: dict[float, dict[str, float]] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            age = float(row["age_years"])
            rows[age] = {
                k: float(v) for k, v in row.items()
                if k not in _NON_NUMERIC and v not in (None, "")
            }
    return rows


def canonical_checksum(path: Path) -> str:
    """SHA-256 over the parsed numeric content (order-independent)."""
    rows = parse_csv(path)
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_manifest() -> dict[str, str]:
    return {name: canonical_checksum(DATA_DIR / name) for name in CSV_FILES}


def load_manifest() -> dict[str, str]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def numeric_cell_count() -> int:
    """Total number of verifiable numeric cells across all six CSVs."""
    return sum(len(cols) for name in CSV_FILES for cols in parse_csv(DATA_DIR / name).values())


if __name__ == "__main__":
    # Regenerate the manifest (run after an intentional, reviewed data change).
    MANIFEST_PATH.write_text(json.dumps(compute_manifest(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST_PATH} ({numeric_cell_count()} numeric cells across {len(CSV_FILES)} files)")

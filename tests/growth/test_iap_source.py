"""Source integrity + verification for the IAP 2015 growth CSVs (audit GC-1).

Two independent guarantees (see backend/growth/data/PROVENANCE.md):

  1. Drift lock  -- the CSV numeric content matches the committed checksum
     manifest, so no value can change silently.
  2. Source verification -- every authoritative value a human has entered from
     the published paper matches the CSV, and the reference cannot be marked
     VERIFIED until all cells are covered.
"""
import json

import pytest

from backend.growth import data_integrity as di

_DATA = di.DATA_DIR


# ── Guarantee 1: drift lock (active now) ─────────────────────────────────────

def test_manifest_covers_exactly_the_six_csvs():
    manifest = di.load_manifest()
    assert set(manifest) == set(di.CSV_FILES)


def test_csv_numeric_content_matches_manifest():
    """Any change to a percentile value (without a reviewed manifest regenerate)
    fails here -- nothing can silently alter the published-derived numbers."""
    manifest = di.load_manifest()
    for name in di.CSV_FILES:
        got = di.canonical_checksum(_DATA / name)
        assert got == manifest[name], (
            f"{name}: numeric content changed since the manifest was written. "
            f"If intentional, review the change then regenerate with "
            f"`python -m backend.growth.data_integrity`."
        )


def test_provenance_documents_every_csv():
    txt = (_DATA / "PROVENANCE.md").read_text(encoding="utf-8")
    for name in di.CSV_FILES:
        assert name in txt, f"{name} missing from PROVENANCE.md"


# ── Guarantee 2: verification against the published paper (incremental) ──────

def _load_reference() -> dict:
    return json.loads(di.REFERENCE_PATH.read_text(encoding="utf-8"))


def test_every_entered_reference_cell_matches_the_csv():
    """Enforce each value a verifier has entered from the paper. Passes trivially
    while none are entered (verification pending) but can NEVER regress once a
    cell is entered -- a paper-vs-CSV mismatch is a real transcription error."""
    ref = _load_reference()
    values = ref.get("values", {})
    entered = 0
    for name in di.CSV_FILES:
        cells = values.get(name, {})
        if not isinstance(cells, dict):
            continue
        csv_rows = di.parse_csv(_DATA / name)
        for age_str, cols in cells.items():
            if age_str.startswith("_") or not isinstance(cols, dict):
                continue
            age = float(age_str)
            assert age in csv_rows, f"{name}: reference age {age} not present in CSV"
            for col, published in cols.items():
                if published is None:
                    continue
                entered += 1
                got = csv_rows[age].get(col)
                assert got is not None, f"{name} @ {age}: column {col!r} not in CSV"
                assert got == pytest.approx(float(published), abs=1e-9), (
                    f"SOURCE MISMATCH {name} @ age {age} {col}: "
                    f"paper says {published}, CSV has {got}"
                )
    # Surfaced in -v output so the pending state is never mistaken for "done".
    print(f"\nGC-1 source verification: {entered}/{di.numeric_cell_count()} cells "
          f"confirmed against the paper (status={ref.get('status')!r}).")


def test_reference_cannot_be_marked_verified_until_fully_covered():
    """The file may only claim VERIFIED when every numeric cell has been entered
    and (by the test above) matched -- no premature 'verified' with partial data."""
    ref = _load_reference()
    if ref.get("status") != "VERIFIED":
        pytest.skip("source verification still pending (status != VERIFIED)")
    entered = sum(
        1
        for name in di.CSV_FILES
        for age_str, cols in ref["values"].get(name, {}).items()
        if not age_str.startswith("_") and isinstance(cols, dict)
        for v in cols.values()
        if v is not None
    )
    assert entered == di.numeric_cell_count(), (
        f"status=VERIFIED but only {entered}/{di.numeric_cell_count()} cells entered"
    )

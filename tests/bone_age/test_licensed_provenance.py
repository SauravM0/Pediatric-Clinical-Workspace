"""Licensed-reference provenance gate (directive 3.4).

Licensed TW3 values may not drive scoring without a documented, legally-owned
source (bone_age_product_starter_pack/licensed_reference_loader.json
"provenance_required"). Scoring turns on only when THREE independent gates pass:
values entered (calibrated) + reference films reproduce + provenance documented.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "prov_test.db"))

from backend.tw3.letters_scoring import (
    REQUIRED_PROVENANCE_FIELDS, build_from_dict, letters_status,
)

_FULL = {
    "book_title": "Assessment of Skeletal Maturity (TW3)",
    "edition": "3rd, 2001",
    "isbn": "978-0702025112",
    "licensed_owner": "Example Paediatric Clinic",
    "pages": "110-140",
    "entered_by": "Dr A. Rao",
    "verified_by": "Dr B. Shah",
    "verification_date": "2026-07-12",
}


def _tables(provenance):
    return build_from_dict({"method": "TW3-letters", "version": "v", "provenance": provenance})


def test_full_provenance_is_complete():
    t = _tables(_FULL)
    assert t.provenance_complete() is True
    assert t.missing_provenance() == []


def test_missing_any_required_field_blocks():
    for field in REQUIRED_PROVENANCE_FIELDS:
        partial = {**_FULL, field: ""}
        t = _tables(partial)
        assert t.provenance_complete() is False
        assert field in t.missing_provenance()


def test_optional_fields_are_not_gated():
    # isbn / pages may be blank without blocking (some editions lack an ISBN)
    t = _tables({**_FULL, "isbn": "", "pages": ""})
    assert t.provenance_complete() is True


def test_empty_provenance_lists_all_required_fields():
    t = _tables({})
    assert t.provenance_complete() is False
    assert set(t.missing_provenance()) == set(REQUIRED_PROVENANCE_FIELDS)


def test_shipped_tables_are_not_scoring_ready_and_report_missing_provenance():
    # The shipped letters_tables.json is uncalibrated AND has blank provenance.
    st = letters_status()
    assert st["scoring_ready"] is False
    assert st["provenance_complete"] is False
    assert set(st["missing_provenance"]) == set(REQUIRED_PROVENANCE_FIELDS)


def test_provenance_is_necessary_but_not_sufficient():
    # Filling provenance alone must NOT enable scoring while values are absent
    # (the calibration + reference-case gates still apply).
    t = _tables(_FULL)
    assert t.provenance_complete() is True
    assert t.any_calibrated() is False   # no points entered -> still not ready

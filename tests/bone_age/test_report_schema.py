"""Report <-> report_output_schema.json alignment + curve edition (Plan 1 WI-5/WI-6)."""
from backend.tw3 import RUS_BONES
from backend.tw3.report import build_report


def test_per_bone_rows_carry_schema_fields():
    rep = build_report("girls", {"radius": "H"}, {})
    row = next(r for r in rep["per_bone_results"] if r["bone_code"] == "radius")
    # report_output_schema.json per_bone_results fields:
    for key in ("manual_stage", "predicted_stage", "confidence_0_to_1", "accepted_by_clinician"):
        assert key in row
    assert row["manual_stage"] == "H"        # mirrors the doctor-confirmed stage
    assert row["predicted_stage"] is None    # AI (Plan 4) fills this later
    assert row["accepted_by_clinician"] is False


def test_per_bone_acceptance_roundtrips():
    rep = build_report("girls", {"radius": "H", "ulna": "G"}, {},
                       accepted={"radius": True})
    by = {r["bone_code"]: r for r in rep["per_bone_results"]}
    assert by["radius"]["accepted_by_clinician"] is True
    assert by["ulna"]["accepted_by_clinician"] is False


def test_definitive_curve_is_explicit_and_defaults_twiii():
    rep = build_report("boys", {b: "H" for b in RUS_BONES}, {})
    assert rep["method"]["definitive_curve"] == "twiii"
    rep2 = build_report("boys", {b: "H" for b in RUS_BONES}, {}, preferred_curve="twii")
    assert rep2["method"]["definitive_curve"] == "twii"


def test_carpal_age_reported_separately():
    rep = build_report("girls", {"radius": "H"}, {"capitate": "G"})
    assert "carpal_definitive_age_years" in rep
    assert "definitive_bone_age_years" in rep
    # both null on the uncalibrated shipped tables; the point is they are separate keys
    assert rep["carpal_definitive_age_years"] is None


def test_checksum_verified_surfaced_in_method():
    rep = build_report("girls", {"radius": "H"}, {})
    assert "checksum_verified" in rep["method"]

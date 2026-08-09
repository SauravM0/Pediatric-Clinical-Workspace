"""M2C ingestion: installing the licensed TW3 %-of-adult-height table.

Two things had to change before licensed values could be installed usefully:

1. ``backend/tw3/adult_height.py`` was computed by nothing -- the adult-height
   endpoint served only the mid-parental target and Khamis-Roche. Entering the
   licensed table would have changed no output. Same failure mode as M1.1.
2. ``is_calibrated`` asked only "are two anchors present". The percentages are
   copyrighted values in the same file as the RUS and carpal point tables,
   under the same licence, and those require documented provenance and a
   checksum lock before they may drive anything. This one did not.

The percentages used below are obvious round numbers invented for the test.
They are NOT the TW3 table, they never leave tmp_path or a monkeypatched file,
and no populated ``pct_adult_height`` may ever be committed.
"""
from __future__ import annotations

import csv
import json

import pytest

from backend.clinical import prediction
from backend.growth.ingest_iap_lms import IngestError
from backend.tw3 import adult_height as ah
from backend.tw3 import ingest_adult_height as ingest
from backend.tw3 import letters_scoring


# A monotone curve reaching ~100% at maturity. Illustrative arithmetic only.
_FIXTURE = {
    "boys": [[8.0, 70.0], [10.0, 78.0], [12.0, 86.0], [14.0, 94.0], [16.5, 99.5]],
    "girls": [[8.0, 74.0], [10.0, 83.0], [12.0, 92.0], [14.0, 98.0], [15.0, 99.5]],
}

_PROVENANCE = {
    "book_title": "Assessment of Skeletal Maturity and Prediction of Adult Height",
    "edition": "3rd",
    "licensed_owner": "Test Clinic",
    "entered_by": "Dr Test",
    "verified_by": "Dr Check",
    "verification_date": "2026-08-09",
}


def _write_supplier(path, table=None, *, headers=("Sex", "Bone Age (years)", "% attained")):
    table = table or _FIXTURE
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write("# transcribed from the clinic's licensed copy\n")
        w = csv.writer(f)
        w.writerow(headers)
        for sex, anchors in table.items():
            for bone_age, percent in anchors:
                w.writerow(["Male" if sex == "boys" else "Female", bone_age, percent])


class _Tables:
    """Stand-in for LetterTables with controllable licensing state."""

    def __init__(self, table=None, provenance=None, checksum_verified=True):
        self.raw = {"pct_adult_height": table if table is not None else _FIXTURE}
        self._p = _PROVENANCE if provenance is None else provenance
        self.checksum_verified = checksum_verified

    def missing_provenance(self):
        return [f for f in letters_scoring.REQUIRED_PROVENANCE_FIELDS
                if not str((self._p or {}).get(f, "")).strip()]


# ── the licensing gate ──────────────────────────────────────────────────────

def test_undocumented_values_do_not_produce_a_prediction():
    """The defect this milestone fixed.

    These are copyrighted values in the same file as the RUS tables. Before
    M2C a clinic could paste them in with no recorded source and no tamper-lock
    and get predictions, while RUS scoring from that same file stayed correctly
    disabled.
    """
    r = ah.predict("boys", 140.0, 12.0, _Tables(provenance={}))
    assert r.available is False
    assert "not fully documented" in r.status
    assert r.predicted_cm is None


def test_an_unlocked_table_does_not_produce_a_prediction():
    r = ah.predict("boys", 140.0, 12.0, _Tables(checksum_verified=False))
    assert r.available is False
    assert "checksum-locked" in r.status


def test_a_fully_licensed_table_does_produce_one():
    """The counterpart: the gate must not block a properly installed table."""
    r = ah.predict("boys", 140.0, 12.0, _Tables())
    assert r.available is True
    assert r.percent_attained == pytest.approx(86.0)
    assert r.predicted_cm == pytest.approx(140.0 / 0.86, abs=0.1)


def test_the_gate_names_every_missing_field():
    gate = ah.licensing_gate(_Tables(provenance={"book_title": "x"}, checksum_verified=False))
    assert gate["ok"] is False
    assert "entered_by" in gate["missing_provenance"]
    assert gate["checksum_verified"] is False
    assert len(gate["reasons"]) == 2


# ── shape checks ────────────────────────────────────────────────────────────

def test_fractions_entered_as_percentages_are_rejected():
    fractions = {"boys": [[8.0, 0.70], [12.0, 0.86], [16.5, 0.995]], "girls": []}
    problems = ah.shape_problems("boys", _Tables(table=fractions))
    assert any("percentages, not fractions" in p for p in problems)


def test_a_falling_curve_is_rejected():
    falling = {"boys": [[8.0, 94.0], [12.0, 86.0], [16.5, 70.0]], "girls": []}
    problems = ah.shape_problems("boys", _Tables(table=falling))
    assert any("falls from" in p for p in problems)


def test_a_table_that_never_reaches_maturity_is_rejected():
    """Every prediction from the top end of a truncated table is refused, so a
    table stopping at 80% is not usable even though it looks well-formed."""
    truncated = {"boys": [[8.0, 70.0], [10.0, 75.0], [12.0, 80.0]], "girls": []}
    problems = ah.shape_problems("boys", _Tables(table=truncated))
    assert any("approach 100" in p for p in problems)


def test_a_valid_curve_has_no_shape_problems():
    assert ah.shape_problems("boys", _Tables()) == []
    assert ah.shape_problems("girls", _Tables()) == []


# ── the ingestion tool ──────────────────────────────────────────────────────

def test_normalise_absorbs_a_supplier_format(tmp_path):
    src = tmp_path / "pct.csv"
    _write_supplier(src)
    table = ingest.normalise(src)
    assert len(table["boys"]) == 5 and len(table["girls"]) == 5
    assert table["boys"][0] == [8.0, 70.0]


@pytest.mark.parametrize("headers", [
    ("Sex", "Bone Age (years)", "% attained"),
    ("Gender", "Skeletal age", "Percentage of adult height"),
    ("sex", "BA", "% of adult ht"),
    ("Sex", "bone_age_years", "pct_adult_height"),
])
def test_column_resolution_survives_real_header_spellings(tmp_path, headers):
    """'age' is a substring of 'percentage', so a naive substring match hands the
    percent column to bone_age on the second case here. On a licensed-values
    import, silently reading the wrong column is the worst available failure."""
    src = tmp_path / "pct.csv"
    _write_supplier(src, headers=headers)
    table = ingest.normalise(src)
    assert table["boys"][0] == [8.0, 70.0], (
        f"columns resolved wrongly for {headers}: got {table['boys'][0]}"
    )
    assert table["girls"][-1] == [15.0, 99.5]


def test_unrecognised_columns_fail_with_the_accepted_names(tmp_path):
    src = tmp_path / "bad.csv"
    src.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(IngestError, match="percent"):
        ingest.normalise(src)


def test_an_unrecognisable_bone_age_column_refuses_rather_than_stealing_percent(tmp_path):
    """Measured, not hypothetical: with a per-column substring fallback, headers
    ('Gender', 'Maturity score', 'Percentage of adult height') resolve bone_age
    to the PERCENT column, because 'age' is inside 'percentage'. The import then
    reads adult-height percentages as bone ages and every prediction is wrong
    with no error anywhere.

    Claiming 'percent' before 'age' is considered turns that into an honest
    refusal naming the accepted spellings.
    """
    src = tmp_path / "ambiguous.csv"
    _write_supplier(src, headers=("Gender", "Maturity score", "Percentage of adult height"))
    with pytest.raises(IngestError) as exc:
        ingest.normalise(src)
    assert "bone_age" in str(exc.value)
    assert "skeletal_age" in str(exc.value), "the error must list what it accepts"


def test_install_is_refused_without_provenance(tmp_path):
    """Not a nicety: the provenance IS the legal basis for these values being
    on disk. Refusing here is the point of the tool."""
    src = tmp_path / "pct.csv"
    _write_supplier(src)
    result = ingest.ingest(src, install=True, provenance={})
    assert result["verdict"]["ok"] is False
    assert "copyrighted" in result["verdict"]["reason"]
    assert result["installed"] is False


def test_install_is_refused_for_a_bad_shape(tmp_path):
    src = tmp_path / "pct.csv"
    _write_supplier(src, {"boys": [[8.0, 0.70], [16.5, 0.995]], "girls": _FIXTURE["girls"]})
    result = ingest.ingest(src, install=True, provenance=_PROVENANCE)
    assert result["shape_problems"]
    assert result["installed"] is False


def test_double_entry_reports_the_differing_cells(tmp_path):
    """There is no published copy to check these against — two independent
    transcriptions differing is the only transcription check available."""
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"
    _write_supplier(first)
    typo = {k: [list(p) for p in v] for k, v in _FIXTURE.items()}
    typo["boys"][2][1] = 68.0                     # 86.0 mistyped
    _write_supplier(second, typo)

    result = ingest.ingest(first, compare=second, provenance=_PROVENANCE)
    assert result["double_entry"]["match"] is False
    diff = result["double_entry"]["differences"][0]
    assert diff["bone_age"] == 12.0 and diff["first"] == 86.0 and diff["second"] == 68.0
    assert result["verdict"]["ok"] is False


def test_matching_double_entry_passes(tmp_path):
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"
    _write_supplier(first)
    _write_supplier(second)
    result = ingest.ingest(first, compare=second, provenance=_PROVENANCE)
    assert result["double_entry"]["match"] is True
    assert result["verdict"]["ok"] is True


def test_install_writes_locked_values_and_activates_prediction(tmp_path, monkeypatch):
    """End to end, against a real letters_tables.json copy.

    Writes through save_letter_tables so the values land checksum-locked in one
    step -- hand-editing the JSON would leave the checksum stale, which
    correctly disables the table and looks like the tool failing.
    """
    real = letters_scoring._TABLES_PATH
    working = tmp_path / "letters_tables.json"
    working.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(letters_scoring, "_TABLES_PATH", working)

    before = letters_scoring.load_letter_tables()
    assert ah.predict("boys", 140.0, 12.0, before).available is False

    src = tmp_path / "pct.csv"
    _write_supplier(src)
    result = ingest.ingest(src, install=True, provenance=_PROVENANCE)

    assert result["installed"] is True
    assert result["checksum_verified"] is True
    assert result["gate"]["ok"] is True

    after = letters_scoring.load_letter_tables()
    r = ah.predict("boys", 140.0, 12.0, after)
    assert r.available is True, f"installed but still refused: {r.status}"
    assert r.predicted_cm == pytest.approx(140.0 / 0.86, abs=0.1)

    # The _fill warning against substituting Bayley-Pinneau values must survive.
    raw = json.loads(working.read_text(encoding="utf-8"))["pct_adult_height"]
    assert "Bayley-Pinneau" in raw.get("_fill", "")


def test_an_out_of_band_edit_after_install_disables_the_table(tmp_path, monkeypatch):
    """The tamper-lock, end to end. Editing a licensed value by hand after
    verification must not silently take effect."""
    real = letters_scoring._TABLES_PATH
    working = tmp_path / "letters_tables.json"
    working.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(letters_scoring, "_TABLES_PATH", working)

    src = tmp_path / "pct.csv"
    _write_supplier(src)
    assert ingest.ingest(src, install=True, provenance=_PROVENANCE)["installed"] is True

    data = json.loads(working.read_text(encoding="utf-8"))
    data["pct_adult_height"]["boys"][2][1] = 60.0        # hand-edited
    working.write_text(json.dumps(data, indent=2), encoding="utf-8")

    with pytest.raises(letters_scoring.LetterTablesError, match="checksum mismatch"):
        letters_scoring.load_letter_tables()


def test_the_repository_never_ships_populated_percentages():
    """These are copyrighted. The shipped slot must stay empty forever."""
    tables = letters_scoring.load_letter_tables()
    raw = tables.raw.get("pct_adult_height", {})
    assert raw.get("boys") == [] and raw.get("girls") == []


# ── the wiring: it must reach the endpoint ──────────────────────────────────

def test_adult_height_summary_reports_the_bone_age_method():
    """The M1.1 lesson applied. Before M2C this quantity was computed by
    backend/tw3/adult_height.py and surfaced nowhere, so installing the licensed
    table would have changed no output at all."""
    summary = prediction.adult_height_summary(
        "boys", 12.0, 140.0, 34.0, 160.0, 175.0, "measured", bone_age_years=12.0)
    assert "from_bone_age" in summary
    entry = summary["from_bone_age"]
    assert "skeletal maturity" in entry["label"]
    # Uninstalled here, so it must refuse with a reason rather than be absent.
    assert entry["available"] is False
    assert len(entry["status"]) > 40


def test_summary_keeps_the_three_quantities_separate():
    summary = prediction.adult_height_summary(
        "boys", 12.0, 140.0, 34.0, 160.0, 175.0, "measured", bone_age_years=12.0)
    assert {"from_bone_age", "genetic_target", "predicted_adult_height"} <= set(summary)
    assert "never present one as the other" in summary["note"]


def test_summary_still_works_without_a_bone_age():
    """Most patients have no radiograph; the other two must be unaffected."""
    summary = prediction.adult_height_summary(
        "boys", 12.0, 140.0, 34.0, 160.0, 175.0, "measured")
    assert summary["from_bone_age"]["available"] is False
    assert summary["genetic_target"] is not None


def test_the_endpoint_passes_the_bone_age_through():
    """Guard on the wiring itself: a summary computed without the snapshot's
    bone age silently degrades to 'no bone age available' for every patient."""
    import inspect

    from backend import api_clinical, clinical_service

    for module in (api_clinical, clinical_service):
        src = inspect.getsource(module)
        assert "bone_age_years=" in src and "adult_height_summary" in src, (
            f"{module.__name__} calls adult_height_summary without a bone age"
        )

"""M5.3: installing the Khamis-Roche coefficients.

The last gated reference in the product without an ingestion path, and the only
one that is a REGRESSION rather than a distribution. That difference drives the
gate: L,M,S triplets are wrong at one age, but coefficients compose, so a single
transposed column is confidently wrong at every age at once and still looks like
a height.

The coefficients below are invented for the test. They are never installed into
the repository -- only into tmp_path with the module's path monkeypatched.
"""
from __future__ import annotations

import csv
import json

import pytest

from backend.clinical import ingest_khamis_roche as ingest
from backend.clinical import prediction
from backend.growth.ingest_iap_lms import IngestError, header_key


def _plausible_rows():
    """A table shaped like the real thing: height dominant, midparent a
    minority share, weight small. Illustrative arithmetic only."""
    rows = []
    for sex in ("boys", "girls"):
        age = 4.0
        while age <= 17.5 + 1e-9:
            rows.append({
                "sex": sex, "age": round(age, 1),
                "intercept": 30.0, "height": 0.75,
                "weight": -0.05, "midparent": 0.30,
            })
            age += 0.5
    return rows


def _write(path, rows, headers=("sex", "age", "intercept", "height", "weight", "midparent")):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow([r[_canon(h)] for h in headers])


def _canon(header):
    """Map a written header back to the canonical field, using the SAME
    normaliser the tool uses -- rolling a second one here is how the first
    version of this helper produced 'age_(years)' and a KeyError."""
    key = header_key(header)
    for canonical, aliases in ingest._COLUMN_ALIASES.items():
        if key in aliases:
            return canonical
    return key


@pytest.fixture
def installed_path(tmp_path, monkeypatch):
    path = tmp_path / "khamis_roche_coefficients.json"
    monkeypatch.setattr(prediction, "_COEFFICIENTS_PATH", path)
    monkeypatch.setattr(ingest, "COEFFICIENTS_PATH", path)
    prediction.reset_cache()
    yield path
    prediction.reset_cache()


# ── inert and honest without data ───────────────────────────────────────────

def test_prediction_is_disabled_without_coefficients(installed_path):
    status = prediction.khamis_roche_status()
    assert status["active"] is False and status["file_present"] is False
    assert "ingest_khamis_roche" in status["reason"]

    r = prediction.predict_adult_height("boys", 10.0, 140.0, 34.0, 160.0, 175.0)
    assert r.available is False
    assert "not entered" in r.status


def test_a_malformed_file_says_so_instead_of_looking_uninstalled(installed_path):
    """The defect this milestone fixed. _coefficients() swallowed every
    exception, so a half-entered or corrupt table reported exactly what an
    absent one reports -- the single state nobody needs to debug."""
    installed_path.write_text("{not json", encoding="utf-8")
    prediction.reset_cache()

    status = prediction.khamis_roche_status()
    assert status["active"] is False
    assert status["file_present"] is True, "the file exists; saying otherwise is a lie"
    assert "not valid JSON" in status["reason"]

    r = prediction.predict_adult_height("boys", 10.0, 140.0, 34.0, 160.0, 175.0)
    assert "not valid JSON" in r.status


def test_a_file_without_a_coefficients_block_is_reported(installed_path):
    installed_path.write_text(json.dumps({"note": "todo"}), encoding="utf-8")
    prediction.reset_cache()
    assert "no 'coefficients' block" in prediction.khamis_roche_status()["reason"]


# ── the shape gate ──────────────────────────────────────────────────────────

def test_a_plausible_table_passes(installed_path, tmp_path):
    src = tmp_path / "kr.csv"
    _write(src, _plausible_rows())
    result = ingest.ingest(src, install=True)
    assert result["problems"] == []
    assert result["installed"] is True
    assert prediction.khamis_roche_available() is True


def test_transposed_columns_are_caught(installed_path, tmp_path):
    """Swapping height and midparent leaves every coefficient inside its bounds
    AND still composes to 191 cm -- a perfectly possible adult height.

    Measured, not assumed: the composition probe alone accepted this table. What
    catches it is dominance -- the child's own stature outweighs the parents' in
    this model, so a row where it does not is transposed.
    """
    rows = _plausible_rows()
    for r in rows:
        r["height"], r["midparent"] = r["midparent"], r["height"]
    src = tmp_path / "swapped.csv"
    _write(src, rows)

    result = ingest.ingest(src, install=True)
    assert result["problems"], "a transposed table was accepted"
    assert any("transposed" in p for p in result["problems"])
    assert result["installed"] is False


def test_composition_catches_rows_that_are_impossible_outright(installed_path, tmp_path):
    """The other half of the probe: parts in range, result not a human height."""
    rows = _plausible_rows()
    for r in rows:
        r["intercept"] = -110.0        # in range, but the row now predicts a toddler
    src = tmp_path / "impossible.csv"
    _write(src, rows)

    result = ingest.ingest(src)
    assert any("does not compose" in p for p in result["problems"])


def test_a_coefficient_out_of_range_is_caught(installed_path, tmp_path):
    rows = _plausible_rows()
    rows[0]["height"] = 25.0            # inches-vs-centimetres class of error
    src = tmp_path / "bad.csv"
    _write(src, rows)
    result = ingest.ingest(src)
    assert any("outside" in p and "height" in p for p in result["problems"])


def test_a_table_covering_only_part_of_the_range_is_flagged(installed_path, tmp_path):
    """Every age outside the entered rows is refused, so a short table silently
    disables most of the method rather than failing loudly."""
    rows = [r for r in _plausible_rows() if r["age"] <= 8.0]
    src = tmp_path / "short.csv"
    _write(src, rows)
    result = ingest.ingest(src)
    assert any("validated over" in p for p in result["problems"])


# ── the tool ────────────────────────────────────────────────────────────────

def test_header_spellings_are_absorbed(installed_path, tmp_path):
    src = tmp_path / "kr.csv"
    _write(src, _plausible_rows(),
           headers=("Gender", "Age (years)", "Constant", "b_height", "b_weight", "MPH"))
    table = ingest.normalise(src)
    assert len(table["boys"]) == 28 and len(table["girls"]) == 28


def test_a_file_with_no_sex_column_needs_an_explicit_sex(installed_path, tmp_path):
    """The paper publishes one table per sex, so a single-sex file is the normal
    case -- but filing it under a guess would be worse than refusing."""
    rows = [{k: v for k, v in r.items() if k != "sex"}
            for r in _plausible_rows() if True]
    src = tmp_path / "one_sex.csv"
    _write(src, rows, headers=("age", "intercept", "height", "weight", "midparent"))

    with pytest.raises(IngestError, match="--sex"):
        ingest.normalise(src)
    table = ingest.normalise(src, default_sex="boys")
    assert table["boys"] and not table["girls"]


def test_merge_keeps_the_other_sex(installed_path, tmp_path):
    boys = [r for r in _plausible_rows() if r["sex"] == "boys"]
    girls = [r for r in _plausible_rows() if r["sex"] == "girls"]
    b, g = tmp_path / "b.csv", tmp_path / "g.csv"
    _write(b, boys)
    _write(g, girls)

    assert ingest.ingest(b, install=True)["installed"] is True
    result = ingest.ingest(g, install=True, merge=True)
    assert result["installed"] is True
    table = json.loads(installed_path.read_text(encoding="utf-8"))["coefficients"]
    assert table["boys"] and table["girls"], "merge dropped a sex"


def test_one_sex_entered_predicts_for_that_sex_and_refuses_the_other(installed_path,
                                                                     tmp_path):
    """The paper publishes one table per sex and they are usually entered
    separately, so a single-sex install is a normal intermediate state.

    Blocking it would disable the sex that HAS been entered -- the opposite of
    useful -- and the other sex already refuses with its own message.
    """
    boys = [r for r in _plausible_rows() if r["sex"] == "boys"]
    src = tmp_path / "boys.csv"
    _write(src, boys)
    assert ingest.ingest(src, install=True)["installed"] is True

    status = prediction.khamis_roche_status()
    assert status["active"] is True
    assert status["sexes_entered"] == ["boys"] and status["sexes_missing"] == ["girls"]

    assert prediction.predict_adult_height(
        "boys", 10.0, 140.0, 34.0, 160.0, 175.0).available is True
    girls = prediction.predict_adult_height("girls", 10.0, 138.0, 33.0, 160.0, 175.0)
    assert girls.available is False and "no coefficient row" in girls.status


def test_double_entry_reports_the_differing_cells(installed_path, tmp_path):
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"
    _write(first, _plausible_rows())
    typo = _plausible_rows()
    typo[3]["intercept"] = 3.0
    _write(second, typo)

    result = ingest.ingest(first, compare=second)
    assert result["double_entry"]["match"] is False
    assert result["verdict"]["ok"] is False


def test_install_records_who_entered_and_verified(installed_path, tmp_path):
    src = tmp_path / "kr.csv"
    _write(src, _plausible_rows())
    ingest.ingest(src, install=True, entered_by="Dr A", verified_by="Dr B",
                  source_note="Table 2")
    blob = json.loads(installed_path.read_text(encoding="utf-8"))
    prov = blob[ingest.PROVENANCE_KEY]
    assert prov["entered_by"] == "Dr A" and prov["verified_by"] == "Dr B"
    assert "Khamis" in blob["reference"]


# ── it reaches the endpoint ─────────────────────────────────────────────────

def test_installing_makes_prediction_actually_appear(installed_path, tmp_path):
    """The M1.1 lesson: installing data must change output."""
    before = prediction.adult_height_summary(
        "boys", 10.0, 140.0, 34.0, 160.0, 175.0, "measured")
    assert before["predicted_adult_height"]["available"] is False

    src = tmp_path / "kr.csv"
    _write(src, _plausible_rows())
    assert ingest.ingest(src, install=True)["installed"] is True

    after = prediction.adult_height_summary(
        "boys", 10.0, 140.0, 34.0, 160.0, 175.0, "measured")
    entry = after["predicted_adult_height"]
    assert entry["available"] is True
    assert entry["predicted_cm"] == pytest.approx(
        30.0 + 0.75 * 140.0 + (-0.05) * 34.0 + 0.30 * 167.5, abs=0.1)
    assert entry["interval_cm"] == prediction.KR_INTERVAL_CM
    assert "interval, never the point estimate" in entry["interval_note"]


def test_outside_the_validated_age_range_is_still_refused(installed_path, tmp_path):
    src = tmp_path / "kr.csv"
    _write(src, _plausible_rows())
    ingest.ingest(src, install=True)
    r = prediction.predict_adult_height("boys", 2.0, 90.0, 14.0, 160.0, 175.0)
    assert r.available is False and "validated for ages" in r.status


def test_the_repository_ships_no_coefficients():
    """Published values a clinic enters from the paper, not something to vendor."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "backend/clinical/"], capture_output=True, text=True
    ).stdout.split()
    assert not [t for t in tracked if "khamis_roche_coefficients" in t], (
        f"coefficients are committed: {tracked}"
    )

"""M1.1 ingestion: the column-consistency finding, and the install path.

``test_iap_lms.py`` covers the LMS reference itself. This file covers the two
things that had to be built before real values could be installed:

1. the discovery that four of the seven height/weight columns in the IAP CSVs
   are reconstructed rather than sourced, which is what forced the gate to
   change; and
2. the ingestion path end-to-end -- normalise, report coverage, judge, install,
   and (the part that was missing entirely) actually take effect.

The fixture LMS used below is fitted to the CSVs' own p3/p50/p97 and lives only
in tmp_path. It is a test double, never a reference: see
``test_the_gate_cannot_distinguish_a_refit_from_the_real_values``, which pins
that limitation rather than papering over it.
"""
from __future__ import annotations

import csv
import json

import numpy as np
import pytest

from backend.growth import iap_lms_reference as lms
from backend.growth import iap_reference as legacy
from backend.growth import iap_table_consistency as tc
from backend.growth import ingest_iap_lms as ingest
from backend.growth import measures as _measures
from backend.growth import who_reference as who
from backend.growth.lms_core import lms_value_at_z


# ── the finding: which columns the CSVs actually source ─────────────────────

@pytest.mark.parametrize("sex", ["boys", "girls"])
@pytest.mark.parametrize("measure", ["height", "weight"])
def test_interior_columns_sit_inside_their_labels(sex, measure):
    """p25 is the 26.5th centile and p10 the 10.5th, in all four files.

    Pinned because it is the whole reason the gate excludes them. If a future
    correction to the CSVs makes this test fail, that is the good outcome --
    and GATE_EXCLUDED_CENTILES should then be emptied.
    """
    implied = tc.implied_centiles(measure, sex)
    assert implied[3] == pytest.approx(3.0, abs=0.01)
    assert implied[50] == pytest.approx(50.0, abs=0.01)
    assert implied[97] == pytest.approx(97.0, abs=0.01)

    assert implied[25] > 26.0, f"p25 implies {implied[25]:.2f}, expected ~26.5"
    assert implied[75] < 74.0, f"p75 implies {implied[75]:.2f}, expected ~73.5"
    assert implied[10] > 10.3
    assert implied[90] < 89.7


@pytest.mark.parametrize("sex", ["boys", "girls"])
@pytest.mark.parametrize("measure", ["height", "weight"])
def test_interior_columns_match_equal_z_spacing_not_their_labels(sex, measure):
    """The mechanism, not just the symptom.

    Dividing the p3..p97 z-range into six equal steps reproduces the interior
    columns to rounding; reading them at their nominal centile z does not, by a
    factor of four or more. That is what "reconstructed" means here.
    """
    worst_reconstructed = worst_nominal = 0.0
    for values in tc._rows(measure, sex):
        triplet = tc._fit_lms(values, (3, 50, 97))
        for centile, z_recon in tc.RECONSTRUCTED_Z.items():
            got_recon = lms_value_at_z(*triplet, z_recon)
            got_nominal = lms_value_at_z(*triplet, tc.Z_FOR_CENTILE[centile])
            worst_reconstructed = max(worst_reconstructed, abs(got_recon - values[centile]))
            worst_nominal = max(worst_nominal, abs(got_nominal - values[centile]))

    assert worst_reconstructed < 0.10, (
        f"equal-z spacing should reproduce the interior columns to rounding, "
        f"got {worst_reconstructed:.4f}"
    )
    assert worst_nominal > 4 * worst_reconstructed, (
        "the nominal centile z should be markedly WORSE than equal z-spacing; "
        f"nominal {worst_nominal:.4f} vs reconstructed {worst_reconstructed:.4f}"
    )


@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_the_same_probe_reads_a_genuine_lms_table_correctly(sex):
    """The control that makes the finding a statement about the data.

    WHO is a real LMS reference. Rounded to the same 0.1 unit the IAP CSVs
    carry and put through the identical procedure, every column must return its
    own label -- otherwise the probe, not the data, is what is wrong.
    """
    anchors = {3: -1.88079, 50: 0.0, 97: 1.88079}
    rows = []
    for i in range(27):
        age = round(5.0 + 0.5 * i, 1)
        vals = {c: who.who_value_at_z("height", sex, age, z)
                for c, z in {**anchors, 25: -0.67449, 75: 0.67449}.items()}
        if any(v is None for v in vals.values()):
            continue
        rows.append({c: round(v, 1) for c, v in vals.items()})
    assert rows, "no WHO coverage — the control proved nothing"

    from scipy.stats import norm
    from backend.growth.lms_core import lms_z_score

    for centile in (25, 75):
        zs = [lms_z_score(r[centile], *tc._fit_lms(r, (3, 50, 97))) for r in rows]
        implied = float(norm.cdf(np.mean(zs)) * 100)
        assert implied == pytest.approx(centile, abs=0.5), (
            f"the probe misreads WHO's p{centile} as {implied:.2f} — it cannot "
            "then be trusted about the IAP files"
        )


def test_bmi_columns_are_consistent_so_none_are_excluded():
    """BMI came from a different paper and is unaffected -- including its p25.
    So the finding is about four specific files, not about p25 as a concept."""
    assert tc.GATE_EXCLUDED_CENTILES["bmi"] == ()
    for sex in ("boys", "girls"):
        implied = tc.implied_centiles("bmi", sex)
        assert implied[25] == pytest.approx(25.0, abs=0.5)
        assert tc.gate_residual("bmi", sex) <= lms.REPRODUCTION_TOL["bmi"]


def test_gate_tolerance_is_reachable_on_the_columns_it_judges():
    """If a free three-parameter fit cannot reproduce the judged columns to the
    gate's own tolerance, then no supplied file could either, and the gate would
    reject the authors' real parameters for a defect in the CSVs. That was the
    state before the reconstructed columns were held out."""
    for measure in _measures.IAP_TABLE_KEYS:
        for sex in ("boys", "girls"):
            assert tc.gate_residual(measure, sex) <= lms.REPRODUCTION_TOL[measure], (
                f"{sex}/{measure}: the gate demands {lms.REPRODUCTION_TOL[measure]} "
                f"but the best possible fit leaves {tc.gate_residual(measure, sex):.4f}"
            )


def test_reconstructed_columns_are_reported_even_though_they_are_not_judged():
    report = tc.consistency_report()
    assert report["all_columns_consistent"] is False, (
        "the CSVs are known to be inconsistent; a clean report means the "
        "diagnosis stopped working"
    )
    for name in ("boys/height", "girls/weight"):
        entry = report["series"][name]
        assert 25 in entry["flagged_columns"] and 75 in entry["flagged_columns"]
        assert entry["gate_columns"] == [3, 50, 97]


# ── the ingestion path ──────────────────────────────────────────────────────

def _fixture_lms_rows():
    """An LMS fitted to the CSVs' own gate columns. A test double, not data."""
    rows = []
    for sex, csv_sex in (("boys", "boy"), ("girls", "girl")):
        for measure in _measures.IAP_TABLE_KEYS:
            cols = tc.gate_centiles(measure)
            ages = [float(r["age_years"]) for r in _read_csv(measure, sex)]
            for age, values in zip(ages, tc._rows(measure, sex)):
                l, m, s = tc._fit_lms(values, cols)
                rows.append((csv_sex, measure, age, l, m, s))
    return rows


def _read_csv(measure, sex):
    with open(tc._csv_path(measure, sex), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_supplier_format(path, rows):
    """Deliberately NOT the canonical schema: different header names, different
    sex words, different column order -- the shape a real supplier file arrives
    in, which is the thing normalise() has to absorb."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Gender", "Parameter", "Age (years)", "lambda", "mu", "sigma"])
        for sex, measure, age, l, m, s in rows:
            w.writerow(["Male" if sex == "boy" else "Female",
                        {"height": "Ht", "weight": "Wt", "bmi": "BMI"}[measure],
                        age, f"{l:.6f}", f"{m:.6f}", f"{s:.6f}"])


def test_normalise_absorbs_a_supplier_format(tmp_path):
    src = tmp_path / "from_authors.csv"
    _write_supplier_format(src, _fixture_lms_rows())
    rows = ingest.normalise(src)
    assert len(rows) == 162, f"expected 2 sexes x 3 measures x 27 ages, got {len(rows)}"
    assert {r[0] for r in rows} == {"boy", "girl"}
    assert {r[1] for r in rows} == {"height", "weight", "bmi"}


def test_unrecognised_columns_fail_with_the_accepted_names(tmp_path):
    src = tmp_path / "wrong.csv"
    src.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ingest.IngestError, match="lambda"):
        ingest.normalise(src)


def test_swapped_lms_columns_are_caught_structurally(tmp_path):
    """L, M and S in the wrong order still parses and still has full coverage.
    The reproduction gate would reject it, but only as 'does not reproduce' --
    the structural check says which column is wrong."""
    src = tmp_path / "swapped.csv"
    swapped = [(sex, measure, age, s, l, m)          # L<-S, M<-L, S<-M
               for sex, measure, age, l, m, s in _fixture_lms_rows()]
    _write_supplier_format(src, swapped)
    result = ingest.ingest(src)
    assert result["sanity_problems"], "a scrambled file passed the structural check"
    assert any("the wrong way round" in p or "outside the plausible" in p
               for p in result["sanity_problems"])
    assert result["installed"] is False


def test_incomplete_file_reports_what_is_missing_rather_than_a_bare_failure(tmp_path):
    src = tmp_path / "partial.csv"
    _write_supplier_format(src, [r for r in _fixture_lms_rows() if r[2] <= 12.0])
    result = ingest.ingest(src)
    assert result["coverage"]["complete"] is False
    entry = result["coverage"]["series"]["boy/height"]
    assert entry["missing_ages"], "missing ages were not enumerated"
    assert 18.0 in entry["missing_ages"]
    assert result["installed"] is False


def test_a_good_file_passes_the_gate_and_a_perturbed_one_does_not(tmp_path):
    good = tmp_path / "good.csv"
    _write_supplier_format(good, _fixture_lms_rows())
    assert ingest.ingest(good)["gate"]["ok"] is True

    # One triplet, one age, one measure — the shape of a real typing slip.
    rows = _fixture_lms_rows()
    perturbed = [
        (sex, measure, age, l, m * 1.02 if (measure == "height" and age == 11.0) else m, s)
        for sex, measure, age, l, m, s in rows
    ]
    bad = tmp_path / "bad.csv"
    _write_supplier_format(bad, perturbed)
    result = ingest.ingest(bad, install=True)
    assert result["gate"]["ok"] is False, (
        "a 2% error in one median passed the gate — a wrong L,M,S is invisible "
        "by eye, so this check is the only thing standing in front of it"
    )
    assert result["installed"] is False, "a failing file was installed"


def test_install_makes_the_lms_path_actually_take_effect(tmp_path, monkeypatch):
    """The gap this milestone existed to close.

    Before this, a valid file could land, pass the gate, report itself active on
    /api/growth/validate -- and change nothing, because no consumer called it.
    The LMS module was wired to the API's status endpoint and to nothing else.
    """
    src = tmp_path / "good.csv"
    _write_supplier_format(src, _fixture_lms_rows())
    installed = tmp_path / "iap_2015_lms.csv"

    monkeypatch.setattr(lms, "LMS_PATH", installed)
    monkeypatch.setattr(ingest, "PROVENANCE_PATH", tmp_path / "provenance.json")
    lms.reset_cache()
    try:
        before = legacy.iap_value_at_z("height", "boys", 11.0, -1.88079)

        result = ingest.ingest(src, install=True, supplied_by="test fixture",
                               received="2026-08-09")
        assert result["installed"] is True
        assert lms.lms_available() is True

        after = legacy.iap_value_at_z("height", "boys", 11.0, -1.88079)
        direct = lms.iap_lms_value_at_z("height", "boys", 11.0, -1.88079)
        assert after == pytest.approx(direct), (
            "iap_value_at_z did not delegate to the LMS path — installing the "
            "data changed nothing, which is exactly the M1.1 failure mode"
        )
        assert before is not None and after is not None

        # ...and the inverse must flip with it, or a value is scored on one
        # model while the curve it sits on is drawn from another (GC-3/GC-4).
        z = legacy.iap_z_for_value("height", "boys", 11.0, after)
        assert z == pytest.approx(-1.88079, abs=1e-6)

        provenance = json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8"))
        assert provenance["supplied_by"] == "test fixture"
        assert provenance["rows"] == 162
    finally:
        lms.reset_cache()


def test_value_and_z_are_exact_inverses_once_live(tmp_path, monkeypatch):
    """The property the legacy path could only approximate, checked through the
    PUBLIC facade rather than the LMS module directly -- that is what a patient's
    z-score actually goes through."""
    src = tmp_path / "good.csv"
    _write_supplier_format(src, _fixture_lms_rows())
    monkeypatch.setattr(lms, "LMS_PATH", tmp_path / "iap_2015_lms.csv")
    monkeypatch.setattr(ingest, "PROVENANCE_PATH", tmp_path / "provenance.json")
    lms.reset_cache()
    try:
        assert ingest.ingest(src, install=True)["installed"] is True
        for measure in ("height", "weight", "bmi"):
            for age in (5.0, 9.5, 14.0, 18.0):
                for target in (-3.0, -1.88079, 0.0, 2.0, 3.5):
                    value = legacy.iap_value_at_z(measure, "girls", age, target)
                    got = legacy.iap_z_for_value(measure, "girls", age, value)
                    assert got == pytest.approx(target, abs=1e-6), (
                        f"{measure} @ {age}y, z={target}: round-tripped to {got}"
                    )
    finally:
        lms.reset_cache()


def test_the_who_iap_seam_still_validates_with_the_lms_path_live(tmp_path, monkeypatch):
    """The bridge takes a value, a slope and a curvature at 5.0y. All three must
    come from the same function, which is why the LMS series extrapolates down
    to the shoulder instead of clamping at 5.0."""
    from backend.growth import validation

    src = tmp_path / "good.csv"
    _write_supplier_format(src, _fixture_lms_rows())
    monkeypatch.setattr(lms, "LMS_PATH", tmp_path / "iap_2015_lms.csv")
    monkeypatch.setattr(ingest, "PROVENANCE_PATH", tmp_path / "provenance.json")
    lms.reset_cache()
    try:
        assert ingest.ingest(src, install=True)["installed"] is True
        report = validation.run_full_validation()
        assert report.all_pass, f"seam/ordering regressions: {report.failures[:5]}"
    finally:
        lms.reset_cache()


def test_lms_coverage_matches_the_legacy_range_exactly():
    """A narrower LMS range would leave the legacy fit serving the shoulder while
    the LMS served everything above it -- two models either side of the exact
    point the bridge probes."""
    assert lms.SHOULDER_AGE == legacy.BLEND_SHOULDER_AGE
    for age in (4.4, 4.5, 4.9, 5.0, 18.0, 18.1):
        assert lms.covers(age) == legacy.iap_covers(age), f"disagree at {age}"


def test_shoulder_extrapolates_rather_than_flattening(tmp_path, monkeypatch):
    """Clamping L, M and S at 5.0 would make them constant below it, so the
    bridge's derivative probe at 5.0 - 1/24y would read zero on one side."""
    src = tmp_path / "good.csv"
    _write_supplier_format(src, _fixture_lms_rows())
    monkeypatch.setattr(lms, "LMS_PATH", tmp_path / "iap_2015_lms.csv")
    monkeypatch.setattr(ingest, "PROVENANCE_PATH", tmp_path / "provenance.json")
    lms.reset_cache()
    try:
        assert ingest.ingest(src, install=True)["installed"] is True
        eps = 1 / 24
        below = lms.iap_lms_value_at_z("height", "boys", 5.0 - eps, 0.0)
        at = lms.iap_lms_value_at_z("height", "boys", 5.0, 0.0)
        above = lms.iap_lms_value_at_z("height", "boys", 5.0 + eps, 0.0)
        assert below is not None and below < at < above, (
            "the median is flat or decreasing across the shoulder — the series "
            "is clamping at 5.0 instead of extrapolating"
        )
    finally:
        lms.reset_cache()


def test_the_gate_cannot_distinguish_a_refit_from_the_real_values(tmp_path):
    """A limitation, pinned deliberately rather than left to be rediscovered.

    Holding out the reconstructed columns leaves three judged columns against
    three free parameters, so an LMS fitted to p3/p50/p97 reproduces them
    exactly. The gate therefore still catches a WRONG file -- a typing slip
    breaks the judged columns, as the perturbation test shows -- but it cannot
    tell the authors' parameters from a competent refit of the same three
    columns.

    An attempt to recover that discrimination from smoothness-in-age was
    measured and abandoned: WHO's real published L for height is nearly
    constant, so any spread-normalised roughness reads it as ROUGHER than a
    per-age refit (0.59 vs 0.047). No criterion was added on that basis.

    What carries the weight instead is provenance -- who supplied the file and
    when, recorded by --supplied-by into iap_2015_lms_provenance.json. When a
    technical check cannot establish a property, the process control that does
    should be named, not implied.
    """
    src = tmp_path / "refit.csv"
    _write_supplier_format(src, _fixture_lms_rows())
    result = ingest.ingest(src)
    assert result["gate"]["ok"] is True

    # And the advisory columns are where the refit shows itself: it reproduces
    # what it was fitted to and misses the reconstructed columns by a lot.
    advisory = result["gate"]["advisory_worst"]
    assert advisory["height"] > 0.2 and advisory["weight"] > 0.2, (
        "the excluded columns should still be MEASURED and reported — they are "
        "the evidence a reviewer reads even though the gate does not judge them"
    )

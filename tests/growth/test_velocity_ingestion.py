"""M1.3 ingestion: installing the Indian height-velocity reference.

Unlike M1.1, the consumption path already existed and was real --
``growth_service.velocities_for`` scores height intervals, and M5's
LOW_HEIGHT_VELOCITY rule reads the result. What was missing was a way to get
the data in, and one latent defect that only becomes reachable once it is:
:func:`test_an_unscorable_recent_interval_is_not_labelled_with_an_older_sds`.

The fixture below is a synthetic curve with the published peak, built to
exercise the machinery. It is not the reference and never leaves tmp_path --
the real values are five numbers per age from a paper this project does not
hold, and inventing them is what the gate exists to prevent.
"""
from __future__ import annotations

import csv
import json

import pytest

from backend.clinical import rules
from backend.clinical.snapshot import PatientSnapshot
from backend.growth import ingest_velocity_reference as ingest
from backend.growth import velocity as vel
from backend.growth import velocity_reference as vr
from backend.growth.ingest_iap_lms import IngestError


# ── fixture: a curve with the right shape and the published peak ────────────

def _synthetic_rows(*, peak_shift_years: float = 0.0, flat: bool = False,
                    distances: bool = False, stop_before_peak: bool = False):
    """A plausible velocity curve, NOT the reference.

    Shape only: a mid-childhood decline into a pubertal peak at the age and
    value the paper's abstract reports, then a fall toward zero. Parameters let
    each test break one property at a time.
    """
    rows = []
    for sex_csv, sex in (("boy", "boys"), ("girl", "girls")):
        expected = vr.EXPECTED_PEAK[sex]
        peak_age = expected["age_years"] + peak_shift_years
        peak_v = expected["velocity_cm_per_year"]
        age = vr.AGE_MIN
        while age <= (peak_age if stop_before_peak else vr.AGE_MAX) + 1e-9:
            if stop_before_peak and age >= peak_age - 1.0:
                break
            if flat:
                m = peak_v
            elif age <= peak_age:
                # 5.5 cm/yr baseline dipping to 4.6, then rising into the peak.
                m = 4.6 + (peak_v - 4.6) * ((age - vr.AGE_MIN) / (peak_age - vr.AGE_MIN)) ** 3
            else:
                frac = (age - peak_age) / max(vr.AGE_MAX - peak_age, 1e-9)
                m = peak_v * (1 - frac) ** 2 + 0.4
            if distances:
                m = 100.0 + age * 6.0        # a height table, not a velocity one
            rows.append((sex_csv, round(age, 2), 1.0, round(m, 3), 0.18))
            age += 0.5
    return rows


def _write_supplier(path, rows, *, comment_header: bool = True):
    with open(path, "w", newline="", encoding="utf-8") as f:
        if comment_header:
            f.write("# supplied by the authors, LMS ChartMaker export\n")
        w = csv.writer(f)
        w.writerow(["Gender", "Age (years)", "lambda", "mu", "sigma"])
        for sex, age, l, m, s in rows:
            w.writerow(["Male" if sex == "boy" else "Female", age,
                        f"{l:.6f}", f"{m:.6f}", f"{s:.6f}"])


def _install(tmp_path, monkeypatch, rows=None):
    src = tmp_path / "velocity.csv"
    _write_supplier(src, rows if rows is not None else _synthetic_rows())
    monkeypatch.setattr(vr, "REFERENCE_PATH", tmp_path / "indian_height_velocity.csv")
    monkeypatch.setattr(ingest, "PROVENANCE_PATH", tmp_path / "provenance.json")
    vr.reset_cache()
    return ingest.ingest(src, install=True, supplied_by="test fixture",
                         received="2026-08-09")


# ── parsing and reporting ───────────────────────────────────────────────────

def test_normalise_absorbs_a_supplier_format_including_comment_lines(tmp_path):
    src = tmp_path / "v.csv"
    _write_supplier(src, _synthetic_rows())
    rows = ingest.normalise(src)
    assert rows, "comment header swallowed the whole file"
    assert {r[0] for r in rows} == {"boy", "girl"}
    assert all(vr.AGE_MIN <= r[1] <= vr.AGE_MAX for r in rows)


def test_unrecognised_columns_fail_with_the_accepted_names(tmp_path):
    src = tmp_path / "bad.csv"
    src.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(IngestError, match="lambda"):
        ingest.normalise(src)


def test_a_table_that_stops_before_the_peak_is_reported_as_incomplete(tmp_path):
    """A count of ages alone looks healthy; the pubertal peak is the part the
    rule actually depends on, so coverage is judged on spanning it."""
    src = tmp_path / "short.csv"
    _write_supplier(src, _synthetic_rows(stop_before_peak=True))
    result = ingest.ingest(src)
    assert result["coverage"]["complete"] is False
    assert result["coverage"]["series"]["boy"]["spans_pubertal_peak"] is False
    assert result["installed"] is False


def test_a_distance_table_is_caught_structurally(tmp_path):
    """The likeliest real mistake: sending the height chart, not the velocity
    one. It parses, it is complete, and every number is wrong."""
    src = tmp_path / "distance.csv"
    _write_supplier(src, _synthetic_rows(distances=True))
    result = ingest.ingest(src)
    assert result["sanity_problems"]
    assert any("distance" in p for p in result["sanity_problems"])
    assert result["installed"] is False


def test_a_near_zero_median_at_the_top_ages_is_accepted(tmp_path):
    """Regression on the structural check itself.

    The first draft demanded M >= 0.5 cm/year and rejected a good table, because
    by 17.5y the median velocity genuinely approaches zero — growth stops. A
    floor there refuses the real reference at exactly the ages where it is
    correct, so only an upper bound is enforced.
    """
    rows = _synthetic_rows()
    assert any(m < 0.5 for _s, _a, _l, m, _sd in rows), (
        "the fixture no longer exercises the near-zero tail this test guards"
    )
    src = tmp_path / "tail.csv"
    _write_supplier(src, rows)
    assert ingest.ingest(src)["sanity_problems"] == []


def test_a_flat_table_fails_the_shape_check(tmp_path):
    """Peaking at the right value is necessary, not sufficient. A flat table
    peaks at 6.8 everywhere; only the post-pubertal fall distinguishes a real
    velocity curve."""
    src = tmp_path / "flat.csv"
    _write_supplier(src, _synthetic_rows(flat=True))
    result = ingest.ingest(src)
    assert result["shape"]["ok"] is False
    assert "does not fall away" in result["shape"]["series"]["boys"]["reason"]
    assert result["installed"] is False


def test_a_peak_in_the_wrong_place_fails_the_gate(tmp_path, monkeypatch):
    """Shifting the peak by 3 years is what a swapped sex column looks like."""
    monkeypatch.setattr(vr, "REFERENCE_PATH", tmp_path / "installed.csv")
    monkeypatch.setattr(ingest, "PROVENANCE_PATH", tmp_path / "p.json")
    vr.reset_cache()
    try:
        src = tmp_path / "shifted.csv"
        _write_supplier(src, _synthetic_rows(peak_shift_years=3.0))
        result = ingest.ingest(src, install=True)
        assert result["gate"]["ok"] is False
        assert "does not peak" in result["gate"]["reason"]
        assert result["installed"] is False
        assert not (tmp_path / "installed.csv").exists()
    finally:
        vr.reset_cache()


# ── installing takes effect ─────────────────────────────────────────────────

def test_install_activates_scoring(tmp_path, monkeypatch):
    try:
        assert vr.reference_available() is False
        result = _install(tmp_path, monkeypatch)
        assert result["installed"] is True
        assert vr.reference_available() is True

        sds, status = vr.velocity_sds("boys", 13.5, 6.8, 1.0)
        assert status == "ok" and sds == pytest.approx(0.0, abs=0.2), (
            "a velocity at the published median peak should score near 0 SD"
        )
        provenance = json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8"))
        assert provenance["supplied_by"] == "test fixture"
    finally:
        vr.reset_cache()


def test_the_interval_band_still_withholds_after_install(tmp_path, monkeypatch):
    """Installing the reference does not make a 4-month interval scorable. The
    reference is built on ~annual measurements; annualising a shorter interval
    widens the spread, so an ordinary child would read as extreme."""
    try:
        assert _install(tmp_path, monkeypatch)["installed"] is True
        sds, status = vr.velocity_sds("boys", 13.5, 6.8, 0.33)
        assert sds is None
        assert status.startswith("interval_outside_reference_band")
    finally:
        vr.reset_cache()


def test_the_rule_switches_from_the_floor_to_a_centile(tmp_path, monkeypatch):
    """End to end: the same child, before and after the data lands."""
    slow = ((12.5, 13.5, 3.0),)
    before = next(f for f in rules.evaluate(
        PatientSnapshot(sex="boys", height_velocities=slow))
        if f.rule_id == "LOW_HEIGHT_VELOCITY")
    assert "coarse floor" in before.rationale
    assert "velocity_sds" not in before.inputs_used

    try:
        assert _install(tmp_path, monkeypatch)["installed"] is True
        sds, status = vr.velocity_sds("boys", 13.0, 3.0, 1.0)
        assert status == "ok" and sds is not None
        after = next(f for f in rules.evaluate(
            PatientSnapshot(sex="boys", height_velocities=((12.5, 13.5, 3.0, sds),)))
            if f.rule_id == "LOW_HEIGHT_VELOCITY")
        assert "velocity reference" in after.rationale
        assert "coarse floor" not in after.rationale
        assert after.inputs_used["velocity_sds"] == pytest.approx(round(sds, 2))
    finally:
        vr.reset_cache()


# ── the latent defect this milestone makes reachable ────────────────────────

def test_an_unscorable_recent_interval_is_not_labelled_with_an_older_sds():
    """A rate from one interval must never carry a centile from another.

    The snapshot exposes ``latest_velocity_sds`` -- the SDS of the most recent
    SCORABLE interval. That is routinely NOT the most recent interval: an annual
    visit scores, and a 4-month follow-up after it produces a rate with no
    centile. The rule used to read that field while reporting the latest
    interval's rate and ages, so it would state a 4-month rate "-2.4 SD against
    the Indian velocity reference" using the previous year's number -- and pick
    URGENT vs ATTENTION from it.

    Dormant until M1.3 installs the data, because the field is None until then.
    Fixed by carrying each interval's SDS with the interval.
    """
    recent_unscorable = (
        (12.0, 13.0, 3.0, -2.6),      # annual, scored, alarming
        (13.0, 13.33, 7.5, None),     # 4-month follow-up, healthy rate, no centile
    )
    findings = [f for f in rules.evaluate(PatientSnapshot(
        sex="boys", height_velocities=recent_unscorable,
        latest_velocity_sds=-2.6))                      # the misleading field
        if f.rule_id == "LOW_HEIGHT_VELOCITY"]

    for f in findings:
        assert f.inputs_used.get("velocity_sds") is None, (
            "the finding attached an SDS to an interval that has none — that SDS "
            "belongs to a different interval of this child's life"
        )
        assert "velocity reference" not in f.rationale, (
            "the rationale cites a centile for an interval that could not be scored"
        )
        assert f.severity != "urgent", (
            "severity was escalated by a stale SDS while reporting a healthy "
            "7.5 cm/year rate"
        )


def test_an_interval_with_its_own_sds_is_still_scored_by_centile():
    """The counterpart: the fix must not disable scoring where it is valid."""
    findings = [f for f in rules.evaluate(PatientSnapshot(
        sex="boys", height_velocities=((12.0, 13.0, 3.0, -2.6),)))
        if f.rule_id == "LOW_HEIGHT_VELOCITY"]
    assert len(findings) == 1
    assert findings[0].inputs_used["velocity_sds"] == pytest.approx(-2.6)
    assert findings[0].severity == "urgent"


def test_the_service_pairs_each_interval_with_its_own_sds():
    """Guard on the producer side: whatever the service emits must carry the
    SDS positionally, or the rule silently falls back to the floor forever."""
    import inspect

    from backend import clinical_service

    src = inspect.getsource(clinical_service.build_snapshot)
    assert 'v.get("velocity_sds")' in src, (
        "build_snapshot no longer puts each interval's SDS into the tuple; the "
        "rule reads element [3] and would never see a centile again"
    )


def test_velocity_result_reports_sds_status_rather_than_a_bare_none():
    """A missing centile must say why -- 'no reference' and 'interval too short'
    lead to different actions, and neither is 'normal'."""
    r = vel.velocity(12.0, 140.0, 13.0, 143.0, sex="boys", score=True)
    assert r.available is True and r.velocity_sds is None
    assert r.sds_status == "no_velocity_reference_available"

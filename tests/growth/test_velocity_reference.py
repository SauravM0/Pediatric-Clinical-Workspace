"""The M1.3 velocity-reference gate.

Like M1.1, most of this skips today: the Khadilkar 2019 velocity percentiles are
not bundled and are not reconstructed here. The tests exist now so installing the
file has an automatic verdict.

The parts that always run cover what does not need the data — the interval band
(the real subtlety in velocity scoring), the fallback behaviour of the M5 rule,
and a dry run proving the activation gate rejects a table that is not this
reference.
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.clinical import rules
from backend.clinical.snapshot import ATTENTION, URGENT, PatientSnapshot
from backend.growth import velocity as vel
from backend.growth import velocity_reference as vr

requires_reference = pytest.mark.skipif(
    not vr.reference_available(),
    reason="Indian velocity reference not installed — see "
           "backend/growth/data/VELOCITY-REFERENCE-REQUEST.md",
)


def _synthetic(path, *, boys_peak=6.8, boys_age=13.5,
               girls_peak=6.6, girls_age=10.5) -> None:
    """A velocity table with a realistic shape, for exercising the machinery.

    A test fixture, not a reference: the L,M,S are constructed, not published.
    Defaults match the paper's reported peaks so the gate accepts it; the
    parameters let a test deliberately build one that should be rejected.
    """
    rows = ["sex,age_years,L,M,S"]
    for sex, peak, peak_age in (("boy", boys_peak, boys_age), ("girl", girls_peak, girls_age)):
        for i in range(26):
            age = 5.0 + 0.5 * i
            # Mid-childhood decline plus a pubertal bump — the characteristic shape.
            m = 3.0 + 2.2 * np.exp(-((age - peak_age) ** 2) / 2.0)
            m += max(0.0, (8.0 - age)) * 0.18
            m = m * (peak / (3.0 + 2.2 + max(0.0, 8.0 - peak_age) * 0.18))
            rows.append(f"{sex},{age},1.0,{m:.4f},0.2000")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


# ── always run ──────────────────────────────────────────────────────────────

def test_path_is_inactive_without_data():
    if vr.REFERENCE_PATH.exists():
        pytest.skip("reference installed")
    assert vr.reference_available() is False
    sds, status = vr.velocity_sds("boys", 10.0, 5.0, 1.0)
    assert sds is None and status == "no_velocity_reference_available"


def test_status_names_the_paper_and_the_consequence():
    status = vr.reference_status()
    if not status["active"]:
        assert "Khadilkar" in status.get("source", "") or "Khadilkar" in status["reason"]
        assert "rule of thumb" in status["reason"] or "4 cm/year" in status["reason"]


def test_kill_switch_only_disables(monkeypatch):
    monkeypatch.setenv("PCW_DISABLE_VELOCITY_REF", "1")
    assert vr.disabled_by_env() is True
    assert vr.reference_available() is False


def test_template_carries_no_values():
    template = vr.REFERENCE_PATH.parent / "indian_height_velocity.template.csv"
    assert template.exists()
    body = [ln for ln in template.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#") and not ln.startswith("sex,")]
    assert body == [], f"the template contains data rows: {body[:3]}"


# ── the interval band: the real subtlety ────────────────────────────────────

@pytest.mark.parametrize("interval,scorable", [
    (0.5, False), (0.74, False), (0.75, True), (1.0, True),
    (1.25, True), (1.26, False), (2.0, False),
])
def test_only_near_annual_intervals_are_scorable(interval, scorable):
    """Velocity centiles are interval-specific. Annualising a shorter gap divides
    measurement error by a smaller delta-t, so the spread widens and an ordinary
    child scores as extreme."""
    assert vr.interval_is_scorable(interval) is scorable


def test_out_of_band_interval_withholds_sds_but_keeps_the_rate(tmp_path, monkeypatch):
    """The rate is still clinically useful; only the centile is withheld."""
    ref = tmp_path / "indian_height_velocity.csv"
    _synthetic(ref)
    monkeypatch.setattr(vr, "REFERENCE_PATH", ref)
    vr.reset_cache()
    try:
        assert vr.reference_available() is True
        result = vel.velocity(5.0, 108.0, 8.0, 130.0, sex="boys", score=True)
        assert result.available is True and result.velocity_per_year is not None
        assert result.velocity_sds is None
        assert "interval_outside_reference_band" in result.sds_status
    finally:
        vr.reset_cache()


def test_sds_is_scored_at_the_interval_midpoint(tmp_path, monkeypatch):
    """A year's growth describes the middle of that year. Attributing it to
    either endpoint shifts the comparison by six months, and around the pubertal
    peak that is the difference between normal and abnormal."""
    ref = tmp_path / "indian_height_velocity.csv"
    _synthetic(ref)
    monkeypatch.setattr(vr, "REFERENCE_PATH", ref)
    vr.reset_cache()
    try:
        rate = 5.0
        result = vel.velocity(13.0, 150.0, 14.0, 155.0, sex="boys", score=True)
        at_mid, _ = vr.velocity_sds("boys", 13.5, rate, 1.0)
        at_end, _ = vr.velocity_sds("boys", 14.0, rate, 1.0)
        assert result.velocity_sds == pytest.approx(at_mid, abs=1e-3)
        assert at_mid != pytest.approx(at_end, abs=1e-3), (
            "midpoint and endpoint give the same answer, so this test proves nothing"
        )
    finally:
        vr.reset_cache()


# ── the activation gate has teeth ───────────────────────────────────────────

def test_gate_accepts_a_table_that_peaks_where_the_paper_says(tmp_path, monkeypatch):
    ref = tmp_path / "indian_height_velocity.csv"
    _synthetic(ref)
    monkeypatch.setattr(vr, "REFERENCE_PATH", ref)
    vr.reset_cache()
    try:
        status = vr.reference_status()
        assert status["active"] is True, status["reason"]
        assert status["peak_check"]["boys"]["matches"] is True
    finally:
        vr.reset_cache()


def test_gate_rejects_swapped_sex_columns(tmp_path, monkeypatch):
    """The most likely transcription error, and invisible by inspection: boys and
    girls peak at different ages, so a swap shows up as a peak in the wrong place."""
    ref = tmp_path / "indian_height_velocity.csv"
    _synthetic(ref, boys_peak=6.6, boys_age=10.5, girls_peak=6.8, girls_age=13.5)
    monkeypatch.setattr(vr, "REFERENCE_PATH", ref)
    vr.reset_cache()
    try:
        assert vr.reference_available() is False
        assert "does not peak" in vr.reference_status()["reason"]
    finally:
        vr.reset_cache()


def test_gate_rejects_distance_values_entered_as_velocity(tmp_path, monkeypatch):
    """The other likely error: pasting the height table into the velocity file.
    Distances are an order of magnitude larger and have no pubertal peak."""
    ref = tmp_path / "indian_height_velocity.csv"
    rows = ["sex,age_years,L,M,S"]
    for sex in ("boy", "girl"):
        for i in range(26):
            age = 5.0 + 0.5 * i
            rows.append(f"{sex},{age},1.0,{100 + age * 5:.2f},0.05")  # heights, not rates
    ref.write_text("\n".join(rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(vr, "REFERENCE_PATH", ref)
    vr.reset_cache()
    try:
        assert vr.reference_available() is False
    finally:
        vr.reset_cache()


def test_sparse_table_is_rejected(tmp_path, monkeypatch):
    ref = tmp_path / "indian_height_velocity.csv"
    ref.write_text("sex,age_years,L,M,S\nboy,5.0,1.0,6.0,0.2\ngirl,5.0,1.0,6.0,0.2\n",
                   encoding="utf-8")
    monkeypatch.setattr(vr, "REFERENCE_PATH", ref)
    vr.reset_cache()
    try:
        with pytest.raises(vr.VelocityReferenceError, match="too few age rows"):
            vr._load()
    finally:
        vr.reset_cache()


# ── the M5 rule upgrades itself ─────────────────────────────────────────────

def test_rule_uses_the_coarse_floor_without_a_reference():
    s = PatientSnapshot(sex="boys", height_velocities=((6.0, 7.0, 3.0),))
    f = next(x for x in rules.evaluate(s) if x.rule_id == "LOW_HEIGHT_VELOCITY")
    assert f.confidence == "low"
    assert "coarse floor" in f.rationale
    assert "threshold_cm_per_year" in f.inputs_used


# These three used to pass the SDS as the snapshot-level `latest_velocity_sds`.
# That field is the SDS of the most recent SCORABLE interval, which is often a
# DIFFERENT interval from the one being reported, so reading it to characterise
# a specific interval mislabels the finding -- see
# tests/growth/test_velocity_ingestion.py. The SDS now travels as the interval's
# own fourth element, and that is what these assert against.

def test_rule_uses_a_real_centile_when_sds_is_available():
    """The upgrade M1.3 delivers: the same 4.5 cm/year is unremarkable at 7 and
    alarming mid-puberty, and only a centile can tell those apart."""
    s = PatientSnapshot(sex="boys", height_velocities=((13.0, 14.0, 4.5, -1.2),))
    f = next(x for x in rules.evaluate(s) if x.rule_id == "LOW_HEIGHT_VELOCITY")
    assert f.confidence == "high"
    assert f.severity == ATTENTION
    assert f.inputs_used["velocity_sds"] == -1.2
    assert "25th centile" in f.rationale


def test_rule_escalates_below_the_third_centile():
    s = PatientSnapshot(sex="boys", height_velocities=((13.0, 14.0, 2.0, -2.4),))
    f = next(x for x in rules.evaluate(s) if x.rule_id == "LOW_HEIGHT_VELOCITY")
    assert f.severity == URGENT and "3rd centile" in f.rationale


def test_rule_stays_silent_for_a_normal_velocity_sds():
    """A slow rate with a NORMAL centile must stay silent.

    Deliberately 3.5 cm/year, which is below the 4 cm/year coarse floor. The
    earlier version used 8.0, which clears the floor too — so it passed whether
    or not the centile was read at all, and proved nothing about the centile
    path. This one is silent only if the SDS is genuinely consulted.
    """
    s = PatientSnapshot(sex="boys", height_velocities=((13.0, 14.0, 3.5, 0.4),))
    assert not any(x.rule_id == "LOW_HEIGHT_VELOCITY" and x.severity in (ATTENTION, URGENT)
                   for x in rules.evaluate(s))


def test_a_fast_velocity_does_not_trip_the_coarse_floor_either():
    s = PatientSnapshot(sex="boys", height_velocities=((13.0, 14.0, 9.0),))
    assert not any(x.rule_id == "LOW_HEIGHT_VELOCITY" and x.severity in (ATTENTION, URGENT)
                   for x in rules.evaluate(s))


# ── runs once the real reference is installed ───────────────────────────────

@requires_reference
def test_installed_reference_peaks_as_published():
    check = vr._peak_check()
    assert check["ok"], check["reason"]


@requires_reference
@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_median_velocity_is_physiologically_plausible(sex):
    for age in np.arange(vr.AGE_MIN, vr.AGE_MAX + 1e-9, 0.5):
        median = vr.velocity_at_centile(sex, float(age), 0.0)
        assert 0.0 < median < 15.0, f"{sex} at {age}: median {median} cm/yr"


@requires_reference
@pytest.mark.parametrize("sex", ["boys", "girls"])
def test_velocity_centiles_never_cross(sex):
    for age in np.arange(vr.AGE_MIN, vr.AGE_MAX + 1e-9, 0.5):
        values = [vr.velocity_at_centile(sex, float(age), z)
                  for z in (-1.88079, -0.67449, 0.0, 0.67449, 1.88079)]
        assert all(np.diff(values) > 0), f"{sex} centiles cross at {age}"


@requires_reference
def test_sds_round_trips_against_the_reference():
    for sex in ("boys", "girls"):
        for age in (7.0, 10.5, 13.5, 16.0):
            for z in (-2.0, 0.0, 1.5):
                value = vr.velocity_at_centile(sex, age, z)
                got, status = vr.velocity_sds(sex, age, value, 1.0)
                assert status == "ok"
                assert got == pytest.approx(z, abs=1e-6)

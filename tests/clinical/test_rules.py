"""The reasoning engine: firing, suppression, and never reading silence as safety (M5)."""
from __future__ import annotations

import pytest

from backend.clinical import rules
from backend.clinical.snapshot import (
    ATTENTION,
    INSUFFICIENT_DATA,
    URGENT,
    Measurement,
    PatientSnapshot,
)


def snap(**kw) -> PatientSnapshot:
    kw.setdefault("sex", "girls")
    return PatientSnapshot(**kw)


def ids(findings) -> set[str]:
    return {f.rule_id for f in findings}


def by_id(findings, rule_id):
    return next(f for f in findings if f.rule_id == rule_id)


# ── thresholds are data, with provenance ────────────────────────────────────

def test_every_threshold_declares_a_source():
    """A number a clinician cannot trace is a number they cannot accept."""
    for name, entry in rules.thresholds().items():
        if name.startswith("_") or name == "version":
            continue
        assert entry.get("source"), f"{name} has no source"
        assert len(entry["source"]) > 30, f"{name}: source is too thin to be useful"
        assert entry.get("confidence") in ("low", "moderate", "high"), name


def test_rule_of_thumb_thresholds_say_so():
    """Two thresholds are clinical folklore rather than guideline figures. They
    must be labelled as such, not dressed up as evidence."""
    for name in ("low_height_velocity_cm_per_year", "arm_span_height_difference_cm"):
        entry = rules.thresholds()[name]
        assert "RULE OF THUMB" in entry["source"]
        assert entry["confidence"] == "low"


def test_every_registered_rule_has_a_description_and_requirements():
    for r in rules.registry():
        assert r.rule_id.isupper() and r.describe and r.requires


# ── firing ──────────────────────────────────────────────────────────────────

def test_short_stature_fires_below_minus_two_sd():
    f = by_id(rules.evaluate(snap(height=Measurement(7.0, 108.0, -2.4))), "SHORT_STATURE")
    assert f.severity == ATTENTION
    assert f.inputs_used["height_sds"] == -2.4
    assert "paediatric endocrinology" in f.suggests_specialty


def test_short_stature_does_not_fire_just_above_the_threshold():
    assert "SHORT_STATURE" not in ids(
        rules.evaluate(snap(height=Measurement(7.0, 112.0, -1.95))))


def test_severe_short_stature_suppresses_the_milder_rule():
    """One problem, one alarm. Three findings for a single -3.2 SD height is how
    clinicians learn to ignore the panel."""
    findings = rules.evaluate(snap(
        height=Measurement(7.0, 100.0, -3.2), mother_height_cm=150.0,
        father_height_cm=160.0, parental_height_source="measured"))
    assert "SEVERE_SHORT_STATURE" in ids(findings)
    assert "SHORT_STATURE" not in ids(findings), "both severity rules fired"
    assert "BELOW_TARGET_HEIGHT" not in ids(findings)


def test_downward_centile_crossing_fires_on_a_sustained_fall():
    findings = rules.evaluate(snap(height_history=(
        Measurement(5.0, 108.0, 0.1), Measurement(6.0, 112.0, -0.3),
        Measurement(7.0, 115.0, -0.9))))
    f = by_id(findings, "DOWNWARD_CENTILE_CROSSING")
    assert f.severity == URGENT
    assert f.inputs_used["change_sds"] == pytest.approx(-1.0, abs=0.01)


def test_crossing_needs_a_year_not_just_a_drop():
    """Over a short interval a fall is measurement noise, not a trajectory."""
    assert "DOWNWARD_CENTILE_CROSSING" not in ids(rules.evaluate(snap(height_history=(
        Measurement(6.0, 112.0, 0.2), Measurement(6.4, 112.5, -0.8)))))


def test_crossing_ignores_infancy():
    """Settling onto a genetic centile before age 3 is physiological."""
    assert "DOWNWARD_CENTILE_CROSSING" not in ids(rules.evaluate(snap(height_history=(
        Measurement(0.5, 65.0, 1.0), Measurement(2.5, 88.0, -0.6)))))


def test_low_velocity_uses_the_most_recent_interval():
    findings = rules.evaluate(snap(height_velocities=((5.0, 6.0, 6.0), (6.0, 7.0, 3.0))))
    f = by_id(findings, "LOW_HEIGHT_VELOCITY")
    assert f.inputs_used["velocity_cm_per_year"] == 3.0
    assert f.confidence == "low", "a rule-of-thumb threshold must not claim confidence"


def test_bone_age_discrepancy_reports_reduced_confidence():
    """The active curve is provisional and digitized; a discrepancy near the
    threshold may be method error rather than biology."""
    f = by_id(rules.evaluate(snap(age_years=10.0, bone_age_years=13.0,
                                  bone_age_method="TW3-C-RUS")), "BONE_AGE_DISCREPANCY")
    assert f.confidence == "low"
    assert "provisional" in f.rationale


def test_sga_without_catch_up_suppresses_plain_short_stature():
    findings = rules.evaluate(snap(
        age_years=4.0, birth_weight_g=2100.0, height=Measurement(4.0, 92.0, -2.3)))
    assert "SGA_WITHOUT_CATCH_UP" in ids(findings)
    assert "SHORT_STATURE" not in ids(findings)


def test_delayed_puberty_boys_uses_testicular_volume():
    findings = rules.evaluate(PatientSnapshot(
        sex="boys", age_years=14.5, testicular_volume_ml=2.0))
    f = by_id(findings, "DELAYED_PUBERTY")
    assert f.severity == URGENT and f.confidence == "high"


def test_early_menarche_suppresses_generic_precocious_puberty():
    findings = rules.evaluate(snap(age_years=7.2, menarche_reached=True, breast_stage=3))
    assert "EARLY_MENARCHE" in ids(findings)
    assert "PRECOCIOUS_PUBERTY" not in ids(findings)


def test_disproportion_points_at_a_different_workup():
    f = by_id(rules.evaluate(snap(arm_span_cm=140.0,
                                  height=Measurement(10.0, 130.0, -1.0))), "DISPROPORTION")
    assert "clinical genetics" in f.suggests_specialty
    assert "skeletal dysplasia" in f.rationale


# ── the safety property ─────────────────────────────────────────────────────

def test_missing_inputs_produce_an_explicit_not_assessed_finding():
    """The most dangerous output is silence: an absent flag must never be
    indistinguishable from 'checked and fine'."""
    findings = rules.evaluate(snap())
    gaps = [f for f in findings if f.severity == INSUFFICIENT_DATA]
    assert gaps, "an empty snapshot produced no not-assessed findings"
    for g in gaps:
        assert "does not mean the finding was excluded" in g.rationale
        assert g.inputs_used["missing"]


def test_a_check_that_ran_is_not_also_reported_as_not_assessed():
    findings = rules.evaluate(snap(height=Measurement(7.0, 108.0, -2.4)))
    assert "SHORT_STATURE" in ids(findings)
    assert not any(f.rule_id == "SHORT_STATURE" and f.severity == INSUFFICIENT_DATA
                   for f in findings)


def test_a_broken_rule_does_not_take_down_the_panel(monkeypatch):
    """A single bad rule must degrade to 'not assessed', not hide every other
    finding behind a 500."""
    def explode(_s):
        raise ZeroDivisionError("boom")

    original = rules._REGISTRY[:]
    try:
        rules._REGISTRY[0] = rules.Rule(original[0].rule_id, (), "broken", explode)
        findings = rules.evaluate(snap(height=Measurement(7.0, 108.0, -2.4)))
        broken = by_id(findings, original[0].rule_id)
        assert broken.severity == INSUFFICIENT_DATA and "ZeroDivisionError" in broken.rationale
        assert "SHORT_STATURE" in ids(findings) or original[0].rule_id == "SHORT_STATURE"
    finally:
        rules._REGISTRY[:] = original


def test_every_finding_carries_the_numbers_it_fired_on():
    """inputs_used is what makes a finding auditable and boundary-testable."""
    findings = rules.evaluate(snap(
        height=Measurement(7.0, 100.0, -3.2), age_years=7.0,
        bone_age_years=4.0, bone_age_method="TW3-C-RUS"))
    for f in findings:
        if f.severity in (URGENT, ATTENTION):
            assert f.inputs_used, f"{f.rule_id} fired without recording its inputs"
            assert f.source, f"{f.rule_id} fired without citing a source"


def test_findings_are_sorted_most_severe_first():
    findings = rules.evaluate(snap(
        height=Measurement(7.0, 100.0, -3.2), age_years=7.0,
        bone_age_years=10.5, bone_age_method="TW3-C-RUS"))
    severities = [f.severity for f in findings]
    assert severities == sorted(severities,
                                key=lambda s: {"urgent": 0, "attention": 1,
                                               "insufficient_data": 2, "info": 3}[s])


def test_engine_is_pure_and_repeatable():
    s = snap(height=Measurement(7.0, 108.0, -2.4))
    assert [f.to_dict() for f in rules.evaluate(s)] == [f.to_dict() for f in rules.evaluate(s)]


# ── regression: the false-positive generator ────────────────────────────────

def test_below_target_compares_sds_with_sds_not_cm_with_an_adult_target():
    """Regression guard for a real bug caught by the API tests.

    The first implementation compared the child's height in CENTIMETRES with the
    mid-parental target in centimetres. A 7-year-old is legitimately ~30 cm
    shorter than their adult target, so it fired for essentially every child --
    precisely the alarm-fatigue generator the engine is designed to avoid.
    Both sides must be on the same scale.
    """
    # On track: child at -0.2 SD, family target -0.3 SD. Must NOT fire.
    on_track = snap(height=Measurement(7.0, 119.0, -0.2), target_height_sds=-0.3,
                    parental_height_source="measured")
    assert "BELOW_TARGET_HEIGHT" not in ids(rules.evaluate(on_track))

    # Genuinely short for THIS family: -2.4 SD against a +0.1 SD target.
    shortfall = snap(height=Measurement(7.0, 105.0, -2.4), target_height_sds=0.1,
                     parental_height_source="measured")
    findings = rules.evaluate(shortfall)
    f = by_id(findings, "BELOW_TARGET_HEIGHT")
    assert f.inputs_used["gap_sds"] == pytest.approx(-2.5, abs=0.01)
    assert "SD" in f.rationale


def test_below_target_confidence_drops_when_parents_were_not_measured():
    reported = snap(height=Measurement(7.0, 105.0, -2.4), target_height_sds=0.1,
                    parental_height_source="reported")
    assert by_id(rules.evaluate(reported), "BELOW_TARGET_HEIGHT").confidence == "low"

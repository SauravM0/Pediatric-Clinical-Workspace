"""Triage safety and the target-vs-prediction split (M5).

The triage tests are the most important in this suite. Under-triage is the
failure mode that harms a patient, and a reassuring output is the specific thing
this product must never produce from anthropometry alone.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.clinical import prediction, referral, rules
from backend.clinical.snapshot import (
    ATTENTION,
    INSUFFICIENT_DATA,
    URGENT,
    Finding,
    Measurement,
    PatientSnapshot,
)


def f(rule_id: str, severity: str, specialties=()) -> Finding:
    return Finding(rule_id, severity, rule_id, "because", {"x": 1}, "src",
                   suggests_specialty=tuple(specialties))


# ── the constraint that matters ─────────────────────────────────────────────

def test_no_triage_level_reassures():
    """Structural, not stylistic. Anthropometry can indicate that something needs
    review; it can almost never establish that a child is fine. A level that says
    so would be read as an all-clear."""
    banned = ("minor", "benign", "normal", "fine", "no_action", "no_concern",
              "clear", "healthy", "reassur", "nothing")
    for level in referral.TRIAGE_LEVELS:
        for word in banned:
            assert word not in level.lower(), (
                f"triage level {level!r} contains reassuring language. "
                "Under-triage is the failure mode that harms patients."
            )


def test_triage_levels_are_exactly_the_three_intended():
    assert set(referral.TRIAGE_LEVELS) == {
        "routine_monitoring", "discuss_with_paediatrician", "specialist_soon"}


def test_referral_source_declares_no_extra_level_constants():
    """A fourth level added without updating TRIAGE_LEVELS would escape the
    guard above, so check the module's own constants."""
    src = Path(referral.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    string_consts = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    }
    for name, value in string_consts.items():
        if name.isupper() and "_" in value:
            assert value in referral.TRIAGE_LEVELS, (
                f"{name} = {value!r} looks like a triage level but is not in "
                "TRIAGE_LEVELS, so the reassurance guard would not see it"
            )


# ── escalation ──────────────────────────────────────────────────────────────

def test_no_findings_yields_monitoring_not_an_all_clear():
    t = referral.triage([])
    assert t.level == referral.ROUTINE_MONITORING
    assert "keep measuring" in t.guidance.lower()
    assert "fine" not in t.guidance.lower() and "normal" not in t.guidance.lower()


def test_urgent_finding_escalates_to_specialist():
    t = referral.triage([f("SEVERE_SHORT_STATURE", URGENT, ("paediatric endocrinology",))])
    assert t.level == referral.SPECIALIST_SOON
    assert t.specialties == ("paediatric endocrinology",)
    assert "SEVERE_SHORT_STATURE" in t.driving_findings


def test_the_highest_severity_wins():
    t = referral.triage([f("A", ATTENTION), f("B", URGENT), f("C", ATTENTION)])
    assert t.level == referral.SPECIALIST_SOON
    assert t.driving_findings == ("B",), "a lesser finding diluted the level"


def test_not_assessed_never_escalates_but_is_always_reported():
    """A check that could not run must not raise the level -- and must not be
    hidden either, or a thin record reads as a clean one."""
    t = referral.triage([f("X", INSUFFICIENT_DATA)])
    assert t.level == referral.ROUTINE_MONITORING
    assert "X" in t.not_assessed
    assert "not the same as those checks passing" in t.reason


def test_specialties_are_deduplicated_in_order():
    t = referral.triage([
        f("A", URGENT, ("paediatric endocrinology",)),
        f("B", URGENT, ("paediatric endocrinology", "clinical genetics")),
    ])
    assert t.specialties == ("paediatric endocrinology", "clinical genetics")


# ── parent wording ──────────────────────────────────────────────────────────

def test_parent_summary_states_observations_not_a_diagnosis():
    findings = [f("SHORT_STATURE", ATTENTION)]
    body = referral.parent_summary(findings, referral.triage(findings))
    assert "not a diagnosis" in body["important"]
    assert "cannot rule anything out" in body["important"]
    blob = " ".join(str(v) for v in body.values()).lower()
    for word in ("diagnos", "probably fine", "nothing to worry"):
        assert word not in blob.replace("not a diagnosis", "").replace("diagnosis.", "")


def test_parent_questions_follow_what_actually_fired():
    body = referral.parent_summary([f("DOWNWARD_CENTILE_CROSSING", URGENT)],
                                   referral.triage([f("DOWNWARD_CENTILE_CROSSING", URGENT)]))
    assert any("growth rate" in q for q in body["questions_to_ask"])


def test_parent_summary_always_offers_at_least_one_question():
    body = referral.parent_summary([], referral.triage([]))
    assert body["questions_to_ask"]


# ── target vs prediction (audit F-1) ────────────────────────────────────────

def test_mid_parental_target_matches_the_tanner_formula():
    boys = prediction.mid_parental_target("boys", 155.0, 175.0, source="measured")
    girls = prediction.mid_parental_target("girls", 155.0, 175.0, source="measured")
    assert boys.target_cm == pytest.approx((175 + 155 + 13) / 2)
    assert girls.target_cm == pytest.approx((175 + 155 - 13) / 2)
    assert boys.target_cm - girls.target_cm == pytest.approx(13.0)


def test_target_needs_both_parents():
    assert prediction.mid_parental_target("boys", 155.0, None) is None
    assert prediction.mid_parental_target("boys", None, 175.0) is None


def test_reported_parental_heights_are_flagged_as_probably_high():
    t = prediction.mid_parental_target("boys", 155.0, 175.0, source="reported")
    assert t.source_quality == "reported"
    assert "over-stated" in t.caveat


def test_target_carries_a_range_not_just_a_number():
    t = prediction.mid_parental_target("boys", 155.0, 175.0, source="measured")
    assert t.range_low_cm < t.target_cm < t.range_high_cm
    assert t.range_high_cm - t.range_low_cm == pytest.approx(
        2 * rules.T("target_range_half_width_cm"))


def test_khamis_roche_is_gated_not_invented():
    """Regression coefficients are not bundled. Inventing them would repeat
    exactly the failure already carried by the digitized TW3 curve."""
    assert prediction.khamis_roche_available() is False
    p = prediction.predict_adult_height("boys", 10.0, 140.0, 32.0, 155.0, 175.0)
    assert p.available is False
    assert "not bundled" in p.status and "Khamis & Roche" in p.status


def test_target_and_prediction_are_separately_labelled():
    """The F-1 audit finding: they are different quantities and one must never be
    presented under the other's name."""
    body = prediction.adult_height_summary("boys", 10.0, 140.0, 32.0, 155.0, 175.0, "measured")
    assert body["genetic_target"]["label"].startswith("Mid-parental target")
    assert body["predicted_adult_height"]["label"].startswith("Predicted adult height")
    assert "different quantities" in body["note"]
    assert body["genetic_target"]["target_cm"] is not None
    assert body["predicted_adult_height"]["predicted_cm"] is None


def test_prediction_would_refuse_to_extrapolate_outside_its_validated_range(monkeypatch):
    monkeypatch.setattr(prediction, "khamis_roche_available", lambda: True)
    monkeypatch.setattr(prediction, "_coefficients", lambda: {"coefficients": {}})
    p = prediction.predict_adult_height("boys", 2.0, 88.0, 12.0, 155.0, 175.0)
    assert p.available is False and "outside that range" in p.status


def test_purity_clinical_package_has_no_persistence():
    """Same contract as backend/growth and backend/tw3."""
    pkg = Path(prediction.__file__).parent
    forbidden = ("sqlalchemy", "fastapi", "backend.models", "backend.db")
    for path in pkg.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.add(node.module)
        bad = [n for n in names if any(n == p or n.startswith(p + ".") for p in forbidden)]
        assert not bad, f"backend/clinical/{path.name} imports {bad}"
